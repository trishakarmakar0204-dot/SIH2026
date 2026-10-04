"""MEMBER 3 owns this file. Run from the project root:  uvicorn backend.main:app
(public demo: run WITHOUT --reload)"""
import threading
import time
from collections import defaultdict, deque
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from language.layer_sarvam import translate, tts, asr_to_english
from rag import engine

# --- limits that protect the Sarvam credits when the site is public ---------------------------
PER_MINUTE_CHAT = 12        # typed questions per visitor per minute
PER_MINUTE_VOICE = 6        # voice questions per visitor per minute (they cost more)
PER_MINUTE_GRIEVANCE = 10   # grievance letters per visitor per minute (no Sarvam cost)
PER_DAY_TOTAL = 3000        # chat + voice requests from ALL visitors together, per day

Lang = Literal["en", "hi", "bn", "or", "as", "ta", "te"]

# docs are switched off so the public site does not advertise its API
app = FastAPI(title="Cooperative Sahayak", docs_url=None, redoc_url=None, openapi_url=None)

_lock = threading.Lock()
_hits = defaultdict(deque)               # (visitor, bucket) -> recent request times
_day = {"date": date.today(), "count": 0}


def _visitor(request: Request) -> str:
    # behind a Cloudflare tunnel the real visitor address arrives in this header
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")


def check_limit(request: Request, bucket: str, per_minute: int, count_daily: bool = True):
    now = time.time()
    with _lock:
        today = date.today()
        if _day["date"] != today:
            _day["date"], _day["count"] = today, 0
        if count_daily and _day["count"] >= PER_DAY_TOTAL:
            raise HTTPException(429, "The daily limit has been reached. Please try again tomorrow.")
        q = _hits[(_visitor(request), bucket)]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= per_minute:
            raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
        q.append(now)
        if count_daily:
            _day["count"] += 1
        if len(_hits) > 5000:            # forget visitors who have been quiet for a minute
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > 60]:
                del _hits[k]


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    lang: Lang = "en"
    speak: bool = False


class VoiceIn(BaseModel):
    audio_b64: str = Field(min_length=1, max_length=5_000_000)   # about 90 seconds of audio
    lang: Lang = "en"


class GrievanceIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    village: str = Field(min_length=1, max_length=80)
    society: str = Field(min_length=1, max_length=120)
    issue: str = Field(min_length=1, max_length=1000)
    date: str = Field(default="", max_length=30)


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(b: ChatIn, request: Request):
    check_limit(request, "chat", PER_MINUTE_CHAT)
    q = safe_translate(b.text, b.lang, "en")
    return {"transcript": b.text, **run(q, b.lang, b.speak)}


@app.post("/voice")
def voice(b: VoiceIn, request: Request):
    check_limit(request, "voice", PER_MINUTE_VOICE)
    try:
        q = asr_to_english(b.audio_b64, b.lang)
    except Exception as e:
        print("speech-to-text failed:", e)
        raise HTTPException(502, "Sorry, the speech service could not understand this recording. Please try again or type your question.")
    return {"transcript": q, **run(q, b.lang, True)}


@app.post("/grievance")
def grievance(b: GrievanceIn, request: Request):
    check_limit(request, "grievance", PER_MINUTE_GRIEVANCE, count_daily=False)
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
