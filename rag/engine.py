"""MEMBER 1 owns this file. English-only knowledge base -> answer + sources.
No-LLM mode v2: every sentence of every official document is indexed, and the answer is the
best-matching sentences quoted word for word, with the exact source files.
Put official documents (.txt or .pdf) in rag/data/ ."""
import os, glob, re, math
from collections import Counter
import numpy as np
from sentence_transformers import SentenceTransformer

DATA = os.path.join(os.path.dirname(__file__), "data")
MIN_SCORE = 0.35          # best sentence must be at least this similar to the question
LEX_WEIGHT = 0.25         # max bonus for matching the question's keywords (a fraction, so keyword-stuffed sentences cannot dominate)
GAP = 0.06                # extra sentences must score within this of the best one
LEN_PENALTY = 0.0015      # per word above 15, so short factual sentences beat long mixed ones
MAX_WORDS = 70            # longest sentence kept
embedder = SentenceTransformer("all-MiniLM-L6-v2")
sentences, sources, positions, sent_prefixes, has_num, lengths = [], [], [], [], [], []
vectors = np.zeros((0, 384))
idf = {}

STOP = {"how", "do", "i", "the", "a", "an", "to", "of", "is", "are", "under", "what",
        "can", "for", "in", "on", "my", "me", "and", "or", "with", "when", "which",
        "does", "will", "should", "have", "has", "get", "give", "tell", "about",
        "many", "much", "number", "total"}
# words people use -> words official documents use
SYNONYMS = {"report": ["intimation", "intimate", "notify", "inform"],
            "inform": ["intimation", "intimate", "notify"],
            "tell": ["intimation", "notify"],
            "complain": ["grievance"], "complaint": ["grievance"],
            "damaged": ["loss", "damage"], "destroyed": ["loss", "damage"],
            "money": ["claim", "compensation", "indemnity"],
            "compensation": ["claim", "indemnity"],
            "working": ["functioning", "operating", "providing"],
            "adopted": ["adopted", "adopt"]}
# phrase in a question -> acronym used in the documents
ACRONYMS = {"common service cent": "csc", "kisan samriddhi": "pmksk", "jan aushadhi": "pmbjk",
            "farmer producer": "fpo", "primary agricultur": "pacs",
            "national cooperative development": "ncdc", "fasal bima": "pmfby",
            "district central cooperative": "dccb", "urban cooperative bank": "ucb",
            "multi state": "mscs", "multi-state": "mscs", "election authority": "cea",
            "toll free": "krph", "enterprise resource": "erp"}

# insurer-side deadlines, e.g. "Within 48 hours from the receipt of the information"
INSURER_DEADLINE = re.compile(r"within \d+ (hours?|days?) (from|of) (the )?(receipt|intimation)", re.I)
# leftovers from PDF tables and formulas
TABLE_JUNK = re.compile(r"\bSl No\b|Action required|Schedule for taking action|Action to be taken|\bWithin \d+ days of\b|%age|Sum Insured X", re.I)
NUMERIC_Q = re.compile(r"\bhow (many|much|long)\b|\bnumber of\b|\bpercent|\bamount\b|\blimit\b", re.I)
FIGURE = re.compile(r"\d{2,}|\d,\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|hundred|thousand|lakh|crore)\b", re.I)


def _clean(t):
    # remove repeating page header of the PMFBY guidelines PDF
    t = re.sub(r"www\.pmfby\.gov\.in\s+Operational Guidelines 2023 of PMFBY\s+\d+", " ", t)
    # stop abbreviations like "Sl." from being treated as sentence ends
    t = re.sub(r"\b(Sl|No|Nos|Rs|Dept|Govt)\.", r"\1", t)
    t = re.sub(r"(\w) -(?=\w)", r"\1-", t)               # "Bye -laws" -> "Bye-laws"
    return " ".join(t.split())


def _read(path):
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader
        text = " ".join((p.extract_text() or "") for p in PdfReader(path).pages)
    else:
        text = open(path, encoding="utf-8").read()
    return _clean(text)


def _split(text):
    out = []
    for s in re.split(r"(?<=[.!?])\s+|\s(?=\d{1,2}(?:\.\d{1,2}){1,3}\s)", text):
        s = re.sub(r"^\d+(\.\d+)+\s*", "", s.strip())      # drop clause number like 22.1.7
        s = re.sub(r"^\d+\s+", "", s)                       # drop stray table number like "2 "
        s = re.sub(r"^(\(?[A-Za-z0-9]{1,4}\)\s+)+", "", s)  # drop list markers like "a)" or "(5)"
        s = re.sub(r"^(?:[A-Z][A-Za-z\-]*\s){1,8}\(?[ivx]{1,3}\)\s+(?=[A-Z])", "", s)   # drop heading glued before "i) "
        s = re.sub(r"\s*(as detailed in|as per|as mentioned in|as given in)\s+Para\b.*$", ".", s, flags=re.I)
        if not s or s[0].islower() or not (8 <= len(s.split()) <= MAX_WORDS):
            continue
        if INSURER_DEADLINE.search(s) or TABLE_JUNK.search(s):
            continue
        out.append(s)
    return out


def _norm(t):
    return t.lower().replace("centre", "center")


def _stem(w):
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        w = w[:-1]
    return w[:6]


def _prefixes(text):
    return {_stem(w) for w in re.findall(r"[a-z]+", _norm(text))}


def load():
    global vectors, idf
    for path in sorted(glob.glob(os.path.join(DATA, "*.*"))):
        if not path.lower().endswith((".txt", ".pdf")):
            continue
        name = os.path.basename(path)
        for i, s in enumerate(_split(_read(path))):
            sentences.append(s)
            sources.append(name)
            positions.append(i)
    for s in sentences:
        sent_prefixes.append(_prefixes(s))
        has_num.append(bool(FIGURE.search(s)))
        lengths.append(len(s.split()))
    if sentences:
        vectors = embedder.encode(sentences, normalize_embeddings=True, batch_size=64)
    df = Counter(p for ps in sent_prefixes for p in ps)
    n = max(len(sentences), 1)
    idf = {p: math.log((n + 1) / (c + 1)) for p, c in df.items()}      # rare word = high weight


load()

NOT_VERIFIED = {"answer": "I could not verify this from official documents. Please contact your cooperative office.",
                "steps": [], "sources": [], "verified": False}


def _keywords(question):
    """Returns (all keyword stems for scoring, one synonym-group per question word, acronym stems, extra words)."""
    nq = _norm(question)
    words = [w for w in re.findall(r"[a-z]+", nq) if w not in STOP and len(w) > 2]
    groups = [{_stem(w)} | {_stem(x) for x in SYNONYMS.get(w, [])} for w in words]
    acr = {_stem(a) for phrase, a in ACRONYMS.items() if phrase in nq}
    kws = set().union(*groups, acr) if groups else set(acr)
    extra = [x for w in words for x in SYNONYMS.get(w, [])] + [a for phrase, a in ACRONYMS.items() if phrase in nq]
    return kws, groups, acr, extra


def _covered(i, groups, acr):
    """How many of the question's words (or their synonyms / acronyms) the sentence contains."""
    ps = sent_prefixes[i]
    return sum(1 for g in groups if g & ps) + (2 if acr & ps else 0)


def _wordset(s):
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def answer(question: str) -> dict:
    if len(sentences) == 0:
        return {**NOT_VERIFIED, "answer": "No documents loaded."}
    kws, groups, acr, extra = _keywords(question)
    rare = max(groups, key=lambda g: max((idf.get(p, 0.0) for p in g), default=0.0)) if groups else set()
    q = embedder.encode([question + " " + " ".join(extra)], normalize_embeddings=True)[0]
    sims = vectors @ q
    den = sum(idf.get(p, 0.0) for p in kws) or 1.0
    bonus = np.array([sum(idf.get(p, 0.0) for p in kws if p in ps) / den for ps in sent_prefixes])
    score = sims + LEX_WEIGHT * bonus - LEN_PENALTY * np.maximum(0, np.array(lengths) - 15)
    figs = np.array(has_num, dtype=bool)
    if NUMERIC_Q.search(question) and (figs & (sims >= MIN_SCORE)).any():
        score = score - 1.0 * (~figs)                # "how many" questions: only sentences with a figure
    order = np.argsort(-score)
    need = min(2, len(groups))
    best = next((int(i) for i in order[:30] if sims[i] >= MIN_SCORE and _covered(int(i), groups, acr) >= need), None)
    if best is None:                                  # nothing relevant enough: refuse instead of guessing
        return dict(NOT_VERIFIED)
    picked = [best]
    for i in order[:60]:
        i = int(i)
        if i == best:
            continue
        if score[i] < score[best] - GAP or len(picked) == 3:
            break
        if sims[i] < MIN_SCORE or sims[i] < sims[best] - 0.12 or _covered(i, groups, acr) < 1:
            continue
        if rare and not (rare & sent_prefixes[i]):      # extra sentences must contain the question's rarest keyword
            continue
        w = _wordset(sentences[i])
        # skip a sentence that mostly repeats one we already picked
        if any(len(w & _wordset(sentences[j])) / max(1, min(len(w), len(_wordset(sentences[j])))) > 0.8 for j in picked):
            continue
        picked.append(i)
    chosen, size = [], 0
    for i in picked:                                  # best first; keep total short for translation + voice
        if chosen and size + len(sentences[i]) > 900:
            continue
        chosen.append(i)
        size += len(sentences[i])
    chosen.sort(key=lambda i: (sources[i], positions[i]))
    return {"answer": " ".join(sentences[i] for i in chosen), "steps": [],
            "sources": sorted({sources[i] for i in chosen}), "verified": True}