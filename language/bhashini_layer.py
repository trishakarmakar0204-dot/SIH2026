"""MEMBER 2 owns this file. Language layer: translate, speech-to-text, text-to-speech.
Language codes: hi, bn, or, as, ta, te, en  (test each one; if Bhashini rejects a code, fix it HERE only)."""
from dotenv import load_dotenv
load_dotenv()
from bhashini_translator import Bhashini

SUPPORTED = ["hi", "bn", "or", "as", "ta", "te", "en"]

def translate(text: str, src: str, tgt: str) -> str:
    if src == tgt or not text.strip():
        return text
    return Bhashini(src, tgt).translate(text)

def asr_to_english(audio_b64: str, lang: str) -> str:
    """Speech (16 kHz wav, base64) in `lang` -> English text."""
    return Bhashini(lang, "en").asr_nmt(audio_b64)

def tts(text: str, lang: str) -> str:
    """Text in `lang` -> base64 audio."""
    return Bhashini(lang).tts(text)
