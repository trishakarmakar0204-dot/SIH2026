"""MEMBER 1 owns this file. English-only knowledge base -> answer + sources.
Put official documents (.txt or .pdf) in rag/data/ ."""
import os, glob, json
import numpy as np
from dotenv import load_dotenv
load_dotenv()
from sentence_transformers import SentenceTransformer
import anthropic

DATA = os.path.join(os.path.dirname(__file__), "data")
MIN_SCORE = 0.30          # tune this using the test questions
embedder = SentenceTransformer("all-MiniLM-L6-v2")
chunks, sources = [], []
llm = anthropic.Anthropic()

def _read(path):
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return " ".join((p.extract_text() or "") for p in PdfReader(path).pages)
    return open(path, encoding="utf-8").read()

def load():
    global vectors
    for path in glob.glob(os.path.join(DATA, "*.*")):
        if not path.lower().endswith((".txt", ".pdf")):
            continue
        words = _read(path).split()
        for i in range(0, len(words), 150):
            chunks.append(" ".join(words[i:i + 200]))
            sources.append(os.path.basename(path))
    vectors = embedder.encode(chunks, normalize_embeddings=True) if chunks else np.zeros((0, 384))

load()

SYSTEM = ("You help Indian cooperative members and farmers. Answer ONLY from the provided context. "
          "Use simple words. Reply as JSON: {\"answer\": str, \"steps\": [str, ...]}. "
          "If the context does not contain the answer, set answer to \"NOT_FOUND\".")
NOT_VERIFIED = {"answer": "I could not verify this from official documents. Please contact your cooperative office.",
                "steps": [], "sources": [], "verified": False}

def answer(question: str) -> dict:
    if len(chunks) == 0:
        return {**NOT_VERIFIED, "answer": "No documents loaded."}
    q = embedder.encode([question], normalize_embeddings=True)[0]
    scores = vectors @ q
    top = np.argsort(-scores)[:4]
    if scores[top[0]] < MIN_SCORE:
        return dict(NOT_VERIFIED)
    context = "\n\n".join(f"[{sources[i]}] {chunks[i]}" for i in top)
    msg = llm.messages.create(
        model=os.getenv("LLM_MODEL", "claude-sonnet-5-5"), max_tokens=700, system=SYSTEM,
        messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}])
    text = msg.content[0].text.strip().strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except Exception:
        data = {"answer": text, "steps": []}
    if data.get("answer") == "NOT_FOUND":
        return dict(NOT_VERIFIED)
    return {"answer": data["answer"], "steps": data.get("steps", []),
            "sources": sorted({sources[i] for i in top}), "verified": True}
