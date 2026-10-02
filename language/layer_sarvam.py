"""Drop-in replacement for language/bhashini_layer.py using Sarvam AI.
Same three functions, so nothing else in the project changes except one import line in backend/main.py.
Needs:  pip install requests   and   SARVAM_API_KEY=... in .env"""
import os, base64, requests
from dotenv import load_dotenv
load_dotenv()

HEADERS = {"api-subscription-key": os.getenv("SARVAM_API_KEY", "")}
CODES = {"hi": "hi-IN", "bn": "bn-IN", "or": "od-IN", "as": "as-IN", "ta": "ta-IN", "te": "te-IN", "en": "en-IN"}
TTS_LANGS = {"hi", "bn", "or", "ta", "te", "en"}      # no Assamese voice listed; Assamese falls back to text only
SUPPORTED = list(CODES)

def translate(text: str, src: str, tgt: str) -> str:
    if src == tgt or not text.strip():
        return text
    r = requests.post("https://api.sarvam.ai/translate", headers=HEADERS, timeout=30, json={
        "input": text, "source_language_code": CODES[src], "target_language_code": CODES[tgt],
        "model": "sarvam-translate:v1"})
    r.raise_for_status()
    return r.json()["translated_text"]

def asr_to_english(audio_b64: str, lang: str) -> str:
    """16 kHz wav (base64), up to ~30 s -> English text, in one call."""
    r = requests.post("https://api.sarvam.ai/speech-to-text", headers=HEADERS, timeout=60,
        files={"file": ("question.wav", base64.b64decode(audio_b64), "audio/wav")},
        data={"model": "saaras:v3", "mode": "translate"})
    r.raise_for_status()
    return r.json()["transcript"]

def tts(text: str, lang: str) -> str:
    if lang not in TTS_LANGS:
        raise ValueError(f"No voice for {lang}")      # backend already catches this and shows text only
    r = requests.post("https://api.sarvam.ai/text-to-speech", headers=HEADERS, timeout=60, json={
        "text": text[:1400], "target_language_code": CODES[lang], "model": "bulbul:v3"})
    r.raise_for_status()
    return r.json()["audios"][0]

if __name__ == "__main__":      # quick test:  python language/layer_sarvam.py
    hi = translate("How do I claim crop insurance?", "en", "hi")
    print(hi, "->", translate(hi, "hi", "en"))