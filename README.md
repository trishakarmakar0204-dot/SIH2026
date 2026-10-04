# Cooperative Sahayak

**A multilingual voice and text assistant for cooperative governance and legal information.**
Built for Smart India Hackathon 2026, Problem Statement **26088**: *Multilingual Cooperative Governance & Legal Assistance Chatbot* (Ministry of Cooperation, NCCT).

| | |
|---|---|
| Team | LoadShedding |
| Team ID | 142669 |
| Category | Hardware + Software (working web prototype; Raspberry Pi kiosk setup guide in `kiosk/`) |

> **Disclaimer:** Answers are quoted from official Government of India documents. This is information, not legal advice.

---

## The problem

Members of cooperative societies often need to know their rights, procedures and benefits (crop insurance, society bye-laws, government initiatives), but the official documents are long, in English, and hard to search. Many members prefer to ask in their own language, by voice.

## What it does

- **Ask in your language, by voice or text.** Speak or type a question and get an answer in the same language, read aloud if you want.
- **Answers are quotes, not guesses.** The assistant does not generate free text. It finds the best-matching sentences in the official documents and shows them word for word, with the exact source file. If the documents don't cover a question, it does not invent an answer.
- **Grievance letter drafting.** A short form produces a ready-to-copy grievance letter.
- **Accessible by design.** Visible labels, keyboard use (Enter to send), status messages, screen-reader language announcements, visible focus outlines, and a "play the answer again" button.
- **Protected for public use.** Per-visitor rate limits, input limits and a daily cap protect the service and the API budget.

## Languages

English, Hindi, Bengali, Odia, Assamese, Tamil and Telugu (seven in total), using Sarvam AI for translation, speech-to-text and text-to-speech.

## Hardware: Raspberry Pi kiosk

A Raspberry Pi with a USB microphone and speaker works as a public kiosk. It opens the assistant full-screen in Chromium kiosk mode and connects to the backend running on a laptop on the same Wi-Fi or hotspot. Step-by-step setup is in [kiosk/README.md](kiosk/README.md).

Start the backend for the kiosk with:

```bash
uvicorn backend.main:app --host 0.0.0.0
```

On a local network the kiosk uses plain `http`, so Chromium is started with a flag that allows microphone access. Use this only on a network you trust.

## How it works

```mermaid
flowchart LR
    A[User: voice or text] --> B[Speech to text<br/>Sarvam AI]
    B --> C[Translate to English<br/>Sarvam AI]
    C --> D[Retrieve best sentences<br/>from official PDFs]
    D --> E[Quote sentences + source file]
    E --> F[Translate back<br/>Sarvam AI]
    F --> G[Text answer + spoken answer<br/>Sarvam AI]
```

**Retrieval (no LLM needed).** Every sentence of the knowledge-base PDFs is indexed with MiniLM sentence embeddings plus a keyword bonus (rarest-keyword filter). The answer is the top-matching sentences, quoted exactly, with their source. This keeps answers traceable and avoids made-up content.

**Knowledge base (current).**
- PMFBY Operational Guidelines 2023
- PACS Model Bye-laws 2023
- Ministry of Cooperation initiatives, Feb 2026

## Tech stack

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Retrieval:** sentence-transformers (MiniLM), keyword scoring, PDF text extraction
- **Language and speech:** Sarvam AI APIs
- **Frontend:** single accessible HTML/CSS/JavaScript page served by the backend

## Getting started

**Requirements:** Python 3.12, a [Sarvam AI](https://www.sarvam.ai/) API key, and a microphone for voice input.

```bash
# 1. Clone
git clone https://github.com/trishakarmakar0204-dot/SIH2026.git
cd SIH2026

# 2. Create and activate a virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key (see Configuration below)

# 5. Run (from the repository root)
uvicorn backend.main:app
```

Open **http://localhost:8000** in your browser. Open the page through this address (or a public link), not by double-clicking `index.html`.

### Configuration

Create a `.env` file in the repository root (never commit it) based on `.env.example`:

```
SARVAM_API_KEY=your_key_here
```

### Optional: share a temporary public demo

```bash
cloudflared tunnel --url http://localhost:8000 --protocol http2
```

This prints a temporary `trycloudflare.com` link (HTTPS, so the microphone works on phones). The link changes each time and only works while your computer is on and both windows are open.

## Usage limits and security

| Limit | Value |
|---|---|
| Typed questions | 12 per minute per visitor |
| Voice questions | 6 per minute per visitor |
| Grievance letters | 10 per minute per visitor |
| Chat + voice, all visitors combined | 3,000 per day |
| Question length | 500 characters |
| Recording length | about 90 seconds |

Other safeguards: only the seven supported languages are accepted, the API docs pages are disabled, a `/health` endpoint is available for checks, and CORS is not opened to all origins because the page is served by the same backend. Visitors over a limit see a polite "please wait" message. Limits can be changed at the top of `backend/main.py`.

## Project structure

```
SIH2026/
├── backend/        FastAPI app (main.py): endpoints, limits, validation
├── frontend/       index.html: accessible web page
├── rag/            engine.py: sentence indexing and retrieval
├── language/       translation and speech helpers
├── kiosk/          Raspberry Pi kiosk setup guide
├── docs/           project documents
├── .env.example    template for the API key
├── requirements.txt
└── README.md
```

## Current limitations

- Answers come only from the three documents above; questions outside them get no answer.
- Hindi and Bengali are the most tested languages; Odia, Assamese, Tamil and Telugu need further testing.
- Needs internet access for the Sarvam AI services.
- The kiosk needs the backend running on a laptop on the same network; it does not run offline.
- Rate limits are stored in memory, so they reset when the server restarts and apply to a single server instance.

## Roadmap

- Test the kiosk on the final Raspberry Pi hardware and make it start automatically on boot
- Full testing and tuning for Odia, Assamese, Tamil and Telugu
- More documents in the knowledge base (state cooperative acts, scheme guidelines)
- Persistent rate limiting for multi-server deployment

## Team

Team LoadShedding: add member names and roles here.
