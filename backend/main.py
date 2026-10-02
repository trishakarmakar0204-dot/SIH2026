"""MEMBER 3 owns this file. Run from the project root:  uvicorn backend.main:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from language.bhashini_layer import translate, tts, asr_to_english
from rag import engine

app = FastAPI(title="Cooperative Sahayak")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    text: str
    lang: str = "en"
    speak: bool = False

class VoiceIn(BaseModel):
    audio_b64: str
    lang: str = "en"

class GrievanceIn(BaseModel):
    name: str
    village: str
    society: str
    issue: str
    date: str = ""

def safe_translate(text, src, tgt):
    try:
        return translate(text, src, tgt)
    except Exception as e:           # fall back to English rather than crash the demo
        print("translate failed:", e)
        return text

def run(english_q: str, lang: str, speak: bool) -> dict:
    r = engine.answer(english_q)
    r["answer"] = safe_translate(r["answer"], "en", lang)
    r["steps"] = [safe_translate(s, "en", lang) for s in r["steps"]]
    r["audio_b64"] = None
    if speak:
        try:
            r["audio_b64"] = tts(r["answer"], lang)
        except Exception as e:
            print("tts failed:", e)
    return r

@app.post("/chat")
def chat(b: ChatIn):
    q = safe_translate(b.text, b.lang, "en")
    return {"transcript": b.text, **run(q, b.lang, b.speak)}

@app.post("/voice")
def voice(b: VoiceIn):
    q = asr_to_english(b.audio_b64, b.lang)
    return {"transcript": q, **run(q, b.lang, True)}

@app.post("/grievance")
def grievance(b: GrievanceIn):
    draft = (f"To,\nThe Secretary, {b.society}\n\nSubject: Grievance regarding {b.issue}\n\n"
             f"I, {b.name}, a member from {b.village}, wish to report the following issue: {b.issue}. "
             f"Date of incident: {b.date or 'not specified'}. I request your kind action and a written acknowledgment.\n\nSincerely,\n{b.name}")
    return {"draft_text": draft}

app.mount("/", StaticFiles(directory="frontend", html=True), name="ui")   # keep this LAST
