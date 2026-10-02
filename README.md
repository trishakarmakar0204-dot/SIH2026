# Cooperative Sahayak (SIH 26088)
Setup (Windows, Python 3.12):
  py -3.12 -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  copy .env.example .env      (then fill in keys)
Run (from this folder):  uvicorn backend.main:app --reload
Open http://localhost:8000

Who edits what: rag/ = M1, language/ = M2, backend/ = M3, frontend/ = M4, kiosk/ = M5, docs/ = M6.
Put official documents (.txt/.pdf) in rag/data/ . Contract: /chat, /voice, /grievance. Don't change it without telling everyone.
