# SettleLens

**AI-powered payment settlement investigation platform.**  
Trace any transaction across gateway, bank, and ledger records in seconds — with a full-screen investigation view, deterministic reconciliation engine, and an integrated Copilot-style AI chatbot.

---

## Features

- **Full-screen Investigate view** — Enter a transaction ID to get a complete investigation: timeline, money flow, exception detection, next steps, and evidence chips
- **Embedded AI Copilot** — Powered by Gemini (`gemini-3.6-flash`). Ask anything about a transaction in plain English. Also responds to general questions and greetings
- **Deterministic reconciliation engine** — Gateway, bank, and ledger records are cross-referenced using rule-based logic; the LLM only explains, never decides
- **Overview dashboard** — Settled / Pending / Needs attention metrics, settlement flow chart, filterable transaction table
- **Exceptions queue** — Surfaces transactions with missing bank outcomes, amount mismatches, or failed payouts
- **Data sources page** — Inspect and download the raw gateway, bank, and ledger CSVs
- **Export** — Download filtered reports as CSV or individual investigations as JSON
- **Two landing-page themes** — Midnight (`index.html`) and Pearl (`pearl.html`)
- **Responsive + accessible** — Keyboard navigation, reduced-motion support, mobile layout, skip-link

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| AI Engine | Google Gemini (`google-genai`) with Groq fallback |
| ML Model | XGBoost · scikit-learn · joblib |
| Frontend | Vanilla HTML · CSS · JavaScript (no framework) |
| Deployment | Railway (Procfile + `railway.toml`) |

---

## Quick Start (local)

### Prerequisites
- Python 3.11+
- A Gemini API key ([get one free](https://aistudio.google.com/app/apikey))

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/Devaditya01/SettleAI.git
cd SettleAI

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set your environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 3000
```

Open **`http://localhost:3000/dashboard/index.html`** in your browser.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key |
| `GEMINI_MODEL` | Optional | Model name (default: `gemini-3.6-flash`) |
| `GROQ_API_KEY` | Optional | Groq API key for fallback LLM |
| `GROQ_MODEL` | Optional | Groq model (default: `llama-3.1-8b-instant`) |
| `LLM_PRIMARY_PROVIDER` | Optional | `gemini` or `groq` (default: `gemini`) |
| `PORT` | Auto-set | Injected by Railway at deploy time |

---

## Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select this repo and the `main` branch
3. Under **Variables**, add `GEMINI_API_KEY` (and optionally `GROQ_API_KEY`)
4. Railway auto-detects the `Procfile` and starts the server

The app will be live at your Railway URL at `/dashboard/index.html`.

---

## Project Structure

```
SettleAI/
├── main.py                  # FastAPI app — serves API + static files
├── requirements.txt         # Python dependencies
├── Procfile                 # Railway start command
├── railway.toml             # Railway config
├── runtime.txt              # Python version pin
├── .env.example             # Environment variable template
│
├── src/
│   ├── llm.py               # LLM integration (Gemini + Groq)
│   ├── service.py           # Business logic — analyze + chat
│   ├── evidence.py          # EvidencePacket schema
│   ├── loader.py            # CSV data loader
│   ├── tracer.py            # Transaction record tracer
│   └── rules.py             # Deterministic reconciliation rules
│
├── dashboard/
│   ├── index.html           # Dashboard shell
│   ├── css/
│   │   ├── styles.css       # Core layout
│   │   ├── theme.css        # Dark/light themes
│   │   ├── refinement.css   # Visual polish
│   │   └── investigate.css  # Full-screen Investigate + chat panel
│   └── js/
│       ├── app.js           # Dashboard logic + AI chat integration
│       └── engine.js        # Reconciliation engine (client-side)
│
├── data/                    # CSV source files (gateway, bank, ledger)
├── models/                  # Trained ML model artifacts
├── assets/                  # Images and shared JS
├── index.html               # Landing page (Midnight theme)
├── pearl.html               # Landing page (Pearl theme)
├── login.html               # Auth page
└── terms.html               # Terms & Conditions
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/analyze/{transaction_id}` | Full deterministic analysis for a transaction |
| `POST` | `/api/chat` | AI chat — `{ transaction_id?, question }` |
| `GET` | `/health` | Health check |

---

## AI Safety

- The LLM only receives an `EvidencePacket` — a bounded, validated schema. Raw CSV rows, webhooks, and logs never reach the model
- Deterministic rules are always authoritative; the LLM only explains
- Invalid or unavailable LLM output falls back to approved deterministic wording
- See [MODEL_CARD.md](MODEL_CARD.md) for full governance details

---

## Demo Transactions

| ID | Scenario |
|---|---|
| TXN000001 | Initiated — bank outcome missing |
| TXN000002 | Successfully settled |
| TXN000003+ | Various: delayed, mismatched, pending, failed |


