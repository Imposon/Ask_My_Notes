import io
import re
from typing import Optional, Dict, List

import pandas as pd
import pdfplumber

from app.utils.helpers import clean_currency

# ── Exhaustive Column Aliases ───────────────────────────────────────────────
# These categories cover almost all major banks (HDFC, ICICI, SBI, Axis, etc.)
COLUMN_ALIASES: Dict[str, List[str]] = {
    "date": [
        "date", "transaction date", "txn date", "trans date", "value date", "v-date",
        "posting date", "tran date", "tran. date", "valuedate", "trn date", "tr date",
        "t-date", "txndate", "statement date", "chq date"
    ],
    "description": [
        "description", "narration", "details", "particulars", "remarks",
        "memo", "transaction description", "transaction remarks", "narrative",
        "chq./ref.no.", "ref_no./cheque_no.", "ref_no", "description/narration",
        "transaction details", "other information", "particulars/description"
    ],
    "amount": [
        "amount", "debit", "withdrawal", "transaction amount", "value",
        "withdrawal amt.", "withdrawal amt.(inr)", "debit amount", "dr amt",
        "dr", "dr amount", "debit amt", "withdrawl", "spend", "paid out"
    ],
    "credit": [
        "credit", "deposit", "cr", "credit amount", "deposit amt.",
        "deposit amt.(inr)", "cr amount", "cr amt", "deposit amt", "received", "paid in"
    ],
}

_DEBIT_KEYWORDS = {"debit", "withdrawal", "dr", "paid out", "withdraw"}

def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intelligently maps raw bank columns to our internal format: date, description, amount.
    Handles multiple aliases and identifies debit vs credit columns.
    """
    df.columns = [str(c).lower().strip().replace("_", " ") for c in df.columns]
    mapping = {}
    
    # 1. Map columns based on aliases
    for canonical, aliases in COLUMN_ALIASES.items():
        for col in df.columns:
            if any(alias == col or alias in col for alias in aliases):
                mapping[col] = canonical
                break
    
    # Check if we found the absolute essentials
    if "date" not in mapping.values() or "description" not in mapping.values():
        # Last resort: try exact matches if partial matching failed
        for canonical, aliases in COLUMN_ALIASES.items():
             for col in df.columns:
                 if col in aliases:
                     mapping[col] = canonical

    # 2. Rename
    df = df.rename(columns=mapping)
    
    # 3. Handle Amount Logic (Debit/Credit vs Single Amount)
    # If we have both 'amount' (debit) and 'credit' columns, merge them.
    if "amount" in df.columns and "credit" in df.columns:
        amt_vals = df["amount"].apply(clean_currency)
        cr_vals = df["credit"].apply(clean_currency)
        
        # Negate debit values
        amt_vals = amt_vals.apply(lambda x: -abs(x) if x != 0 else 0)
        
        # Result is Debit + Credit (where Debit is negative and Credit is positive)
        # Use Credit value if Debit is null/zero
        final_amt = amt_vals.where((amt_vals != 0) & amt_vals.notna(), cr_vals)
        df["amount"] = final_amt
    else:
        # Check if the single amount column was actually a 'debit' column
        original_cols = [c for c, mapped in mapping.items() if mapped == "amount"]
        if original_cols:
            orig_name = original_cols[0]
            if any(k in orig_name for k in _DEBIT_KEYWORDS):
                df["amount"] = df["amount"].apply(clean_currency).apply(lambda x: -abs(x))
            else:
                df["amount"] = df["amount"].apply(clean_currency)
        else:
             df["amount"] = df.get("amount", pd.Series([0.0]*len(df))).apply(clean_currency)

    # 4. Final Cleanup
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    df["description"] = df["description"].fillna("Transaction").astype(str).str.strip()
    
    # Ensure correct columns exist before returning
    required = ["date", "description", "amount"]
    for col in required:
        if col not in df.columns:
            df[col] = None if col != "amount" else 0.0

    return df[required].sort_values("date").reset_index(drop=True)

def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    """Robustly reads CSV files, skipping bank headers."""
    for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    
    lines = text.splitlines()
    header_idx = 0
    best_score = 0
    
    # Look for the header row in first 100 lines
    for i, line in enumerate(lines[:100]):
        cells = [c.strip().lower() for c in line.split(",")]
        score = 0
        for category in COLUMN_ALIASES.values():
            if any(alias in cells for alias in category):
                score += 1
        if score > best_score:
            best_score = score
            header_idx = i
        if score >= 3:
            header_idx = i
            break
            
    df = pd.read_csv(io.BytesIO(file_bytes), skiprows=header_idx, on_bad_lines="skip")
    return normalize_dataframe_columns(df)

def parse_pdf(file_bytes: bytes) -> pd.DataFrame:
    """
    Extracts data from PDF and processes it via the same normalization pipeline.
    Uses Table Extraction first, then falls back to Raw text parsing.
    """
    all_data = []
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # 1. Try Tables
            table = page.extract_table()
            if table and len(table) > 1:
                df_page = pd.DataFrame(table[1:], columns=table[0])
                all_data.append(df_page)
            else:
                # 2. Try Raw Text if table extraction fails
                text = page.extract_text()
                if text:
                    # Look for lines that contain a date and something that looks like an amount
                    # Regex: [Date] ... [Amount]
                    pattern = re.compile(r"(\d{1,2}[/\-\.\s](?:\d{1,2}|[A-Za-z]{3})[/\-\.\s](?:\d{4}|\d{2}))\s+(.*?)\s+([-+]?[\d,]+\.\d{2})")
                    for line in text.splitlines():
                        match = pattern.search(line)
                        if match:
                            all_data.append(pd.DataFrame([{
                                "date": match.group(1),
                                "description": match.group(2),
                                "amount": match.group(3)
                            }]))

    if not all_data:
        raise ValueError("Could not extract any data from the PDF. Please ensure it's a digitally generated statement.")

    combined_df = pd.concat(all_data, ignore_index=True)
    return normalize_dataframe_columns(combined_df)
