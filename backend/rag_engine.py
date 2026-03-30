"""
RAG Engine — Embeddings + FAISS retrieval + chat answer generation.

Strategy:
  - Uses sentence-transformers (all-MiniLM-L6-v2) for local, free embeddings.
  - Falls back to TF-IDF if sentence-transformers is not installed.
  - Uses OpenAI GPT for answer generation when API key is provided.
  - Falls back to extractive answer (most relevant chunk) otherwise.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Embedding back-ends
# ─────────────────────────────────────────────────────────────────────────────

_st_model = None


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


def _embed_st(texts: List[str]) -> np.ndarray:
    model = _get_st_model()
    return model.encode(texts, normalize_embeddings=True).astype("float32")


def _embed_tfidf(texts: List[str], fitted_vectorizer=None):
    from sklearn.feature_extraction.text import TfidfVectorizer
    if fitted_vectorizer is None:
        vec = TfidfVectorizer(max_features=512, sublinear_tf=True)
        mat = vec.fit_transform(texts).toarray().astype("float32")
        # L2 normalize
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        return mat / norms, vec
    else:
        mat = fitted_vectorizer.transform(texts).toarray().astype("float32")
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        return mat / norms, fitted_vectorizer


def embed_texts(texts: List[str]):
    """Return (embeddings: np.ndarray, meta: any) — meta is vectorizer for TF-IDF, None for ST."""
    try:
        return _embed_st(texts), None
    except Exception as exc:
        logger.warning("sentence-transformers unavailable (%s), falling back to TF-IDF", exc)
        mat, vec = _embed_tfidf(texts)
        return mat, vec


def embed_query(query: str, meta):
    """Embed a single query string using the same backend as the corpus."""
    if meta is None:
        try:
            return _embed_st([query])
        except Exception:
            pass
    if meta is not None:
        mat, _ = _embed_tfidf([query], fitted_vectorizer=meta)
        return mat
    # last resort: zero vector
    return np.zeros((1, 512), dtype="float32")


# ─────────────────────────────────────────────────────────────────────────────
# FAISS index per document
# ─────────────────────────────────────────────────────────────────────────────

_doc_store: Dict[str, Dict] = {}  # doc_id -> {chunks, index, meta}


def build_index(doc_id: str, chunks: List[Dict]) -> None:
    """Build a FAISS index for the given document chunks."""
    import faiss

    texts = [c["text"] for c in chunks]
    embeddings, meta = embed_texts(texts)
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    _doc_store[doc_id] = {
        "chunks": chunks,
        "index": index,
        "meta": meta,
        "texts": texts,
    }


def retrieve(doc_id: str, query: str, k: int = 4) -> List[Dict]:
    """Return top-k most relevant chunks for the query."""
    if doc_id not in _doc_store:
        return []

    entry = _doc_store[doc_id]
    q_emb = embed_query(query, entry["meta"])

    distances, indices = entry["index"].search(q_emb, k)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx >= 0:
            results.append({
                "chunk": entry["chunks"][idx],
                "score": float(dist),
            })
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Answer generation
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are LexIntel, an expert AI legal document analyst. "
    "Answer the user's question based ONLY on the provided document context. "
    "If the answer is not in the context, say so clearly. "
    "Always cite the relevant clause or section. Be concise and precise."
)


async def generate_answer(
    question: str,
    retrieved: List[Dict],
    openai_api_key: Optional[str] = None,
) -> Dict[str, str]:
    """Generate a chat answer from retrieved chunks."""
    if not retrieved:
        return {
            "answer": "I could not find relevant information in this document to answer your question.",
            "source": None,
        }

    # Build context
    context_parts = []
    for r in retrieved[:3]:
        chunk = r["chunk"]
        title = chunk.get("title", "")
        context_parts.append(f"[{title}]\n{chunk['text'][:600]}")
    context = "\n\n---\n\n".join(context_parts)

    source_title = retrieved[0]["chunk"].get("title", "")

    if openai_api_key:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Document context:\n{context}\n\nQuestion: {question}"},
                ],
                max_tokens=400,
                temperature=0.2,
            )
            answer = response.choices[0].message.content.strip()
            return {"answer": answer, "source": source_title}
        except Exception as exc:
            logger.warning("OpenAI call failed (%s), using extractive fallback", exc)

    # Extractive fallback: find the best matching chunk by keyword overlap
    q_words = set(re.findall(r"\w+", question.lower())) - {
        "what", "is", "are", "the", "a", "an", "there", "any", "how",
        "does", "do", "tell", "me", "about", "in", "this", "document",
        "please", "can", "you", "explain",
    }

    best_chunk = None
    best_chunk_score = -1

    for r in retrieved:
        chunk_text = r["chunk"]["text"].lower()
        kw_overlap = sum(1 for w in q_words if w in chunk_text)
        combined = kw_overlap * 2 + r["score"]
        if combined > best_chunk_score:
            best_chunk_score = combined
            best_chunk = r["chunk"]

    if not best_chunk:
        best_chunk = retrieved[0]["chunk"]

    best_text = best_chunk["text"]
    sentences = re.split(r"(?<=[.!\n])\s+", best_text)
    scored_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) > 25:
            overlap = len(q_words & set(re.findall(r"\w+", s.lower())))
            scored_sentences.append((overlap, s))
    scored_sentences.sort(key=lambda x: -x[0])
    top_sentences = [s for _, s in scored_sentences[:3]] if scored_sentences else sentences[:3]
    answer = " ".join(top_sentences)

    source_title = best_chunk.get("title", "")

    return {
        "answer": answer or best_text[:400],
        "source": source_title,
    }
