"""MEMBER 3 owns this file. Run from the project root:  uvicorn backend.main:app --reload"""
from datetime import date
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from language.layer_sarvam import translate, tts, asr_to_english
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
    issue = b.issue.strip().rstrip(".")
    when = f" Date of incident: {b.date}." if b.date else ""
    draft = (f"Date: {date.today().strftime('%d %B %Y')}\n\n"
             f"To,\nThe Secretary,\n{b.society}\n\n"
             f"Subject: Grievance from {b.name}, {b.village}\n\n"
             f"Respected Sir/Madam,\n\n"
             f"I, {b.name}, a member from {b.village}, wish to bring the following issue to your notice:\n\n"
             f"{issue}.{when}\n\n"
             f"I request your kind action and a written acknowledgment of this grievance.\n\n"
             f"Yours sincerely,\n{b.name}\nVillage: {b.village}")
    return {"draft_text": draft}

app.mount("/", StaticFiles(directory="frontend", html=True), name="ui")   # keep this LAST