"""
Voice Output Module — translate text then generate speech via gTTS.
Returns base64-encoded MP3 audio and the translated text.
"""

import io
import base64
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "english": "en",
    "hindi": "hi",
    "telugu": "te",
    "tamil": "ta",
    "kannada": "kn",
    "malayalam": "ml",
    "marathi": "mr",
    "bengali": "bn",
    "gujarati": "gu",
    "punjabi": "pa",
    "urdu": "ur",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "arabic": "ar",
    "chinese": "zh-CN",
    "japanese": "ja",
    "korean": "ko",
}


def _translate(text: str, target_lang_code: str) -> str:
    """Translate text to target language. Falls back to original on error."""
    if target_lang_code == "en":
        return text
    try:
        from deep_translator import GoogleTranslator
        # Google Translate accepts up to ~5000 chars per call; chunk if needed
        max_chunk = 4000
        if len(text) <= max_chunk:
            return GoogleTranslator(source="auto", target=target_lang_code).translate(text)

        chunks = [text[i:i + max_chunk] for i in range(0, len(text), max_chunk)]
        translated_chunks = [
            GoogleTranslator(source="auto", target=target_lang_code).translate(chunk)
            for chunk in chunks
        ]
        return " ".join(translated_chunks)
    except Exception as exc:
        logger.warning("Translation failed (%s), returning original text", exc)
        return text


def text_to_speech(text: str, language: str = "english") -> Tuple[str, str]:
    """
    Convert text to speech in the requested language.

    Returns:
        (base64_audio_string, translated_text)
    """
    lang_code = SUPPORTED_LANGUAGES.get(language.lower(), "en")

    # Translate first
    translated = _translate(text, lang_code)

    # Generate speech
    try:
        from gtts import gTTS
        tts = gTTS(text=translated, lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode("utf-8")
    except Exception as exc:
        logger.error("gTTS failed: %s", exc)
        raise RuntimeError(f"Speech generation failed: {exc}") from exc

    return audio_b64, translated
