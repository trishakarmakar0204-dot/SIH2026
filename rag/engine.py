"""MEMBER 1 owns this file. English-only knowledge base -> answer + sources.
No-LLM mode: returns the most relevant sentences from official documents, word for word.
Put official documents (.txt or .pdf) in rag/data/ ."""
import os, glob, re, math
from collections import Counter
import numpy as np
from sentence_transformers import SentenceTransformer

DATA = os.path.join(os.path.dirname(__file__), "data")
MIN_SCORE = 0.30          # tune this using the test questions
KW_WEIGHT = 0.03          # how much rare-keyword matches count vs meaning-similarity
GAP = 0.12                # extra sentences must score within this of the best one
embedder = SentenceTransformer("all-MiniLM-L6-v2")
chunks, sources = [], []
vectors = np.zeros((0, 384))
chunk_prefixes, idf = [], {}

STOP = {"how", "do", "i", "the", "a", "an", "to", "of", "is", "are", "under", "what",
        "can", "for", "in", "on", "my", "me", "and", "or", "with", "when", "which",
        "does", "will", "should", "have", "has", "get", "give", "tell", "about"}
# words people use -> words official documents use
SYNONYMS = {"report": ["intimation", "intimate", "notify", "inform"],
            "inform": ["intimation", "intimate", "notify"],
            "tell": ["intimation", "notify"],
            "complain": ["grievance"], "complaint": ["grievance"],
            "damaged": ["loss", "damage"], "destroyed": ["loss", "damage"],
            "money": ["claim", "compensation", "indemnity"],
            "compensation": ["claim", "indemnity"]}

# insurer-side deadlines, e.g. "Within 48 hours from the receipt of the information"
INSURER_DEADLINE = re.compile(r"within \d+ (hours?|days?) (from|of) (the )?(receipt|intimation)", re.I)
# leftovers from PDF tables
TABLE_JUNK = re.compile(r"\bSl No\b|Action required|Schedule for taking action|Action to be taken|\bWithin \d+ days of\b", re.I)


def _clean(t):
    # remove repeating page header of the PMFBY guidelines PDF
    t = re.sub(r"www\.pmfby\.gov\.in\s+Operational Guidelines 2023 of PMFBY\s+\d+", " ", t)
    # stop abbreviations like "Sl." from being treated as sentence ends
    t = re.sub(r"\b(Sl|No|Nos|Rs|Dept|Govt)\.", r"\1", t)
    return t


def _read(path):
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader
        text = " ".join((p.extract_text() or "") for p in PdfReader(path).pages)
    else:
        text = open(path, encoding="utf-8").read()
    return _clean(text)


def _prefixes(text):
    return {w[:6] for w in re.findall(r"[a-z]+", text.lower())}


def load():
    global vectors, chunk_prefixes, idf
    for path in glob.glob(os.path.join(DATA, "*.*")):
        if not path.lower().endswith((".txt", ".pdf")):
            continue
        words = _read(path).split()
        for i in range(0, len(words), 150):
            chunks.append(" ".join(words[i:i + 200]))
            sources.append(os.path.basename(path))
    vectors = embedder.encode(chunks, normalize_embeddings=True) if chunks else np.zeros((0, 384))
    chunk_prefixes = [_prefixes(c) for c in chunks]
    df = Counter(p for s in chunk_prefixes for p in s)
    n = max(len(chunks), 1)
    idf = {p: math.log((n + 1) / (c + 1)) for p, c in df.items()}   # rare word = high weight


load()

NOT_VERIFIED = {"answer": "I could not verify this from official documents. Please contact your cooperative office.",
                "steps": [], "sources": [], "verified": False}


def _keywords(question):
    """Question words + document-style synonyms, as 6-letter prefixes."""
    words = [w for w in re.findall(r"[a-z]+", question.lower()) if w not in STOP and len(w) > 2]
    extra = [x for w in words for x in SYNONYMS.get(w, [])]
    return {w[:6] for w in words + extra}, extra


def _kw_bonus(prefix_set, kws):
    return sum(idf.get(p, 0.0) for p in kws if p in prefix_set)


def _wordset(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _best_sentences(q_vec, top_chunks, kws, n=3):
    cands = []                                   # (position, sentence)
    for rank, ci in enumerate(top_chunks):
        parts = re.split(r"(?<=[.!?])\s+|\s(?=\d{1,2}(?:\.\d{1,2}){1,3}\s)", chunks[ci])
        for s in parts:
            if 8 <= len(s.split()) <= 60:
                s = re.sub(r"^\d+(\.\d+)+\s*", "", s.strip())      # drop clause number like 22.1.7
                s = re.sub(r"^\d+\s+", "", s)                       # drop stray table number like "2 "
                s = re.sub(r"\s*(as detailed in|as per|as mentioned in|as given in)\s+Para\b.*$", ".", s, flags=re.I)
                if not s or s[0].islower():
                    continue
                if INSURER_DEADLINE.search(s) or TABLE_JUNK.search(s):
                    continue
                cands.append((rank * 1000 + len(cands), s))
    if not cands:
        return []
    sv = embedder.encode([s for _, s in cands], normalize_embeddings=True)
    sims = sv @ q_vec
    for i, (_, s) in enumerate(cands):
        sims[i] += KW_WEIGHT * _kw_bonus(_prefixes(s), kws)
    order = np.argsort(-sims)
    best_score = sims[order[0]]
    kept = []                                    # (index, wordset)
    for i in order:
        if kept and sims[i] < best_score - GAP:  # not relevant enough compared with the best
            break
        w = _wordset(cands[i][1])
        # skip a sentence that mostly repeats one we already picked
        if any(len(w & kw) / max(1, min(len(w), len(kw))) > 0.8 for _, kw in kept):
            continue
        kept.append((i, w))
        if len(kept) == n:
            break
    return [cands[i][1] for i, _ in sorted(kept, key=lambda t: cands[t[0]][0])]


def answer(question: str) -> dict:
    if len(chunks) == 0:
        return {**NOT_VERIFIED, "answer": "No documents loaded."}
    kws, extra = _keywords(question)
    q = embedder.encode([question + " " + " ".join(extra)], normalize_embeddings=True)[0]
    scores = vectors @ q
    if scores.max() < MIN_SCORE:
        return dict(NOT_VERIFIED)
    combined = scores + KW_WEIGHT * np.array([_kw_bonus(p, kws) for p in chunk_prefixes])
    top = list(np.argsort(-combined)[:5])
    sents = _best_sentences(q, top, kws, 3)
    if not sents:
        return dict(NOT_VERIFIED)
    text = ""
    for s in sents:                              # whole sentences only, max ~900 chars
        if text and len(text) + len(s) > 900:
            break
        text += (" " if text else "") + s
    return {"answer": text, "steps": [],
            "sources": sorted({sources[i] for i in top}), "verified": True}