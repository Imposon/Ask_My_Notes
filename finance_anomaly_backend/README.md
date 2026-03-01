# Personal Finance Anomaly Detector — Backend

AI-powered anomaly detection engine for personal bank transactions.

## Tech Stack

- **Python 3.11+** / **FastAPI** / **Pydantic v2**
- **SQLAlchemy** + **SQLite** (swap-in Postgres for production)
- **Scikit-learn** (Isolation Forest) / **Pandas** / **NumPy**
- **pdfplumber** (PDF bank statement parsing)
- **Joblib** (model serialisation)

## Quick Start

```bash
cd finance_anomaly_backend

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload
```

The API is available at **http://127.0.0.1:8000**.  
Interactive docs at **http://127.0.0.1:8000/docs**.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/users` | Create a new user |
| `POST` | `/upload?user_id=<uuid>` | Upload CSV / PDF bank statement |
| `POST` | `/analyze/{user_id}` | Run anomaly detection pipeline |
| `GET` | `/transactions/{user_id}` | List transactions (optional `?anomalies_only=true`) |

## Architecture

```
app/
├── main.py                  # FastAPI entry point
├── database.py              # SQLAlchemy engine + session
├── models.py                # ORM models (User, Transaction, UserBaseline)
├── schemas.py               # Pydantic request/response schemas
│
├── routes/
│   ├── upload.py            # POST /upload
│   └── analyze.py           # POST /analyze, GET /transactions
│
├── services/
│   ├── parser.py            # CSV + PDF parsing
│   ├── categorizer.py       # Keyword-based categorisation
│   ├── feature_engineering.py
│   ├── baseline.py          # Per-user behavioural baseline
│   ├── anomaly_engine.py    # Hybrid scoring (statistical + Isolation Forest)
│   └── explanation_engine.py
│
├── utils/
│   └── helpers.py           # Currency cleaning, merchant extraction, etc.
│
└── ml_models/               # Per-user serialised models (.pkl)
```

## Anomaly Detection Pipeline

1. **Parse** — CSV or PDF → structured DataFrame
2. **Categorise** — keyword-based mapping (Food, Transport, Shopping, …)
3. **Feature Engineering** — hour, day-of-week, rolling spend, merchant frequency, …
4. **Baseline** — per-user category/merchant/weekly spend statistics
5. **Statistical Scoring** — amount z-score, weekly deviation, new merchant, time deviation
6. **ML Scoring** — Isolation Forest trained on user's feature matrix
7. **Hybrid Score** — `0.6 × ML + 0.4 × Statistical`, normalised 0–100
8. **Explanations** — human-readable reasons for each flagged transaction

## Database

SQLite file: `finance_anomaly.db` (auto-created on first run).

Three tables: `users`, `transactions`, `user_baselines`.
