import os
import re
import math
from pathlib import Path

import pandas as pd


_CURRENCY_RE = re.compile(r"[^\d.\-+]")


def clean_currency(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()

    # Parenthesised amounts are negative: (1,234.56) → -1234.56
    is_negative = raw.startswith("(") and raw.endswith(")")
    if is_negative:
        raw = raw[1:-1]

    if re.search(r"\bDr\b", raw, re.IGNORECASE):
        is_negative = True
        raw = re.sub(r"\s*\bDr\b", "", raw, flags=re.IGNORECASE)

    raw = re.sub(r"\s*\bCr\b", "", raw, flags=re.IGNORECASE)

    cleaned = _CURRENCY_RE.sub("", raw)

    if cleaned.endswith("-"):
        cleaned = "-" + cleaned[:-1]

    if cleaned in ("", "-", "+"):
        return 0.0

    try:
        result = float(cleaned)
    except ValueError:
        return float("nan")  # will be dropped by dropna in parser

    return -abs(result) if is_negative else result


_NOISE_WORDS = {
    "upi", "neft", "imps", "pos", "atm", "ach", "debit", "credit",
    "card", "payment", "transfer", "txn", "ref", "no", "to", "from",
    "via", "by", "on", "the", "for", "at", "and", "pvt", "ltd",
}


def extract_merchant(description: str) -> str:
    if not description:
        return "Unknown"
    tokens = re.split(r"[\s/\-_|*#]+", description.strip())
    meaningful = [t for t in tokens if t.lower() not in _NOISE_WORDS and len(t) > 1]
    if not meaningful:
        return description.strip()[:60]
    return " ".join(meaningful[:3]).title()[:60]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


ML_MODELS_DIR = Path(__file__).resolve().parent.parent / "ml_models"


def ensure_ml_models_dir() -> Path:
    ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return ML_MODELS_DIR
