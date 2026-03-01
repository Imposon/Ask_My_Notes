import io
import re
from typing import Optional

import pandas as pd
import pdfplumber

from app.utils.helpers import clean_currency, normalize_columns

# ── Constants ────────────────────────────────────────────────────────────────

_COLUMN_ALIASES: dict[str, list[str]] = {
    "date": [
        "date", "transaction_date", "txn_date", "trans_date", "value_date", "v-date",
        "posting_date", "tran_date", "tran._date", "valuedate", "trn_date", "tr_date",
        "t-date",
    ],
    "description": [
        "description", "narration", "details", "particulars", "remarks",
        "memo", "transaction_description", "transaction_remarks", "narrative",
        "chq./ref.no.", "ref_no./cheque_no.", "ref_no", "description/narration",
    ],
    "amount": [
        "amount", "debit", "withdrawal", "transaction_amount", "value",
        "withdrawal_amt.", "withdrawal_amt.(inr)", "debit_amount", "dr_amt",
        "dr", "dr_amount", "dr_amt", "debit_amt", "withdrawl", "spend",
    ],
    "credit": [
        "credit", "deposit", "cr", "credit_amount", "deposit_amt.",
        "deposit_amt.(inr)", "cr_amount", "cr_amt", "deposit_amt", "received",
    ],
}

# Column names (after normalize) that represent debits — amounts must be negated.
_DEBIT_COLUMN_NAMES = {
    "debit", "withdrawal", "withdrawal_amt.", "withdrawal_amt.(inr)",
    "debit_amount", "dr", "dr_amount", "dr_amt", "debit_amt",
}


def _read_csv_robust(file_bytes: bytes) -> pd.DataFrame:
    """Try multiple encodings and auto-skip bank metadata rows before the header."""
    text: Optional[str] = None
    used_encoding = "utf-8"
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("Could not decode the CSV file. Please save it as UTF-8 or Latin-1.")

    lines = text.splitlines()

    # Find the row that looks most like the column header row
    header_keywords = set(
        ["date"] + _COLUMN_ALIASES["date"]
        + _COLUMN_ALIASES["description"]
        + _COLUMN_ALIASES["amount"]
        + _COLUMN_ALIASES["credit"]
    )
    header_row_idx = 0
    best_score = 0
    for i, line in enumerate(lines[:100]):  # Peak at first 100 lines
        # Split by comma but handle basic quoted CSV
        cells = {c.strip().strip('"\'').lower().replace(" ", "_") for c in line.split(",")}
        score = len(cells & header_keywords)
        if score > best_score:
            best_score = score
            header_row_idx = i
        if score >= 3:  # stronger signal needed
            header_row_idx = i
            break

    df = pd.read_csv(
        io.BytesIO(file_bytes),
        encoding=used_encoding,
        skiprows=header_row_idx,
        dtype=str,
        skip_blank_lines=True,
        on_bad_lines="skip",
    )
    return df


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    df = _read_csv_robust(file_bytes)
    df = normalize_columns(df)

    # Remember original column names so we can decide sign later
    original_amount_col = None
    for alias in _COLUMN_ALIASES["amount"]:
        if alias in df.columns:
            original_amount_col = alias
            break

    col_map = _resolve_columns(df.columns.tolist())
    df = df.rename(columns=col_map)

    _validate_required_columns(df, ["date", "description", "amount"])

    # Clean and merge split Debit/Credit columns
    amount_vals = df["amount"].apply(clean_currency)
    if "credit" in df.columns:
        credit_vals = df["credit"].apply(clean_currency)
        use_credit = amount_vals.isna() | (amount_vals == 0.0)
        # Debit column values are withdrawals → negate
        amount_vals = amount_vals.where(
            amount_vals.isna() | (amount_vals == 0.0),
            -amount_vals.abs(),
        )
        df["amount"] = amount_vals.where(~use_credit, credit_vals)
    else:
        # Single amount column: negate if the source column is a debit-type
        if original_amount_col in _DEBIT_COLUMN_NAMES:
            amount_vals = amount_vals.where(
                amount_vals.isna() | (amount_vals == 0.0),
                -amount_vals.abs(),
            )
        df["amount"] = amount_vals

    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date", "amount"])
    df = df[df["amount"] != 0.0]  # drop zero-amount header/footer rows
    df["description"] = df["description"].fillna("").astype(str).str.strip()
    df = df.sort_values("date").reset_index(drop=True)

    return df[["date", "description", "amount"]]


# Robust regex for matching a date at the start of a line
# Supports: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, dd-MMM-yyyy etc.
_DATE_RE = re.compile(
    r"^\s*"                                       # Start of line + optional whitespace
    r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:\d{4}|\d{2})|\d{1,2}[/\-\.][A-Za-z]{3}[/\-\.](?:\d{4}|\d{2}))",
    re.IGNORECASE
)

# Robust regex for finding an amount (the last numeric-ish block in a line)
# Handles 1,234.56, -123, 123.00 Dr, (123.00), etc.
_AMOUNT_SUFFIX_RE = re.compile(
    r"((?:[+-]?\s*[\$₹€£]?\s*[\d,]+\.?\d*)|(?:\([\$₹€£]?\s*[\d,]+\.?\d*\)))"  # The number
    r"(?:\s*(?:Dr|Cr|DR|CR|dr|cr))?\s*$",                                     # Optional suffix + end of line
    re.IGNORECASE
)

def _parse_text_lines(text: str) -> list[dict]:
    """A flexible, non-strict line parser for bank statements."""
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 1. Line must start with a date
        date_match = _DATE_RE.search(line)
        if not date_match:
            continue
        
        date_str = date_match.group(1)
        remaining = line[date_match.end():].strip()
        
        # 2. Extract the LAST numeric value as the amount
        # We search from the end of the line
        amt_match = _AMOUNT_SUFFIX_RE.search(remaining)
        if not amt_match:
            continue
            
        full_amt_match = amt_match.group(0) # Includes suffix if present
        amt_str = amt_match.group(1)        # Just the digits/symbols
        
        # 3. Everything in between is the description
        # Remove the amount part from the end of 'remaining'
        desc_str = remaining[:amt_match.start()].strip()
        
        # Ignore common header fragments if they shifted into descriptions
        if any(hdr in desc_str.lower() for hdr in ["balance", "date", "particulars"]):
            if len(desc_str) < 15: # Simple heuristic to avoid killing real transactions with these words
                continue

        # Final validation: skip rows if description is empty and we have a valid-looking line
        if not desc_str and len(line) > 10:
            # Maybe the amount was in the middle? (Less likely for bank statements)
            continue
            
        rows.append({
            "date": date_str,
            "description": desc_str if desc_str else "Transaction",
            "amount": full_amt_match if full_amt_match else amt_str,
        })
    return rows


def parse_pdf(file_bytes: bytes) -> pd.DataFrame:
    rows: list[dict] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_rows: list[dict] = []

            # 1. Try extracting tables
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    extracted = _parse_table(table)
                    page_rows.extend(extracted)
            
            existing_keys = set()
            for r in page_rows:
                key = (str(r.get("date")), str(r.get("amount")))
                existing_keys.add(key)

            # 2. Try Regex on raw text
            text = page.extract_text() or ""
            text_rows = _parse_text_lines(text)
            
            # De-duplication: Add regex rows only if not found in table
            for tr in text_rows:
                key = (str(tr.get("date")), str(tr.get("amount")))
                if key not in existing_keys:
                    page_rows.append(tr)
                    existing_keys.add(key)

            # 3. Last Resort: Structured Text Extraction (word by word)
            # This is slow but catches rows that table/regex miss due to wrapping
            if len(page_rows) < 2:
                words = page.extract_words()
                # Sort words: top first (row), then x0 (left edge)
                # Some versions of pdfplumber use 'x0' instead of 'left'
                def sort_key(w):
                    top = float(w.get("top", 0))
                    left = float(w.get("x0", w.get("left", 0)))
                    return (round(top), left)
                
                words.sort(key=sort_key)
                
                # Group words into lines
                current_top = -1
                line_text = ""
                for w in words:
                    w_top = float(w.get("top", 0))
                    if abs(w_top - current_top) > 3:
                        if line_text:
                            # Use our new flexible line processor
                            lrows = _parse_text_lines(line_text)
                            for lr in lrows:
                                if (str(lr["date"]), str(lr["amount"])) not in existing_keys:
                                    page_rows.append(lr)
                                    existing_keys.add((str(lr["date"]), str(lr["amount"])))
                        line_text = w["text"]
                        current_top = w_top
                    else:
                        line_text += " " + w["text"]
                # Final line check
                if line_text:
                    lrows = _parse_text_lines(line_text)
                    for lr in lrows:
                        if (str(lr["date"]), str(lr["amount"])) not in existing_keys:
                            page_rows.append(lr)

            rows.extend(page_rows)

    if not rows:
        # Final emergency fallback: if no dates/amounts found via line parsing,
        # try a very broad search for ANY numeric values and dates in the text
        text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        dates = _DATE_RE.findall(text)
        if len(dates) > 10:
             # Just return a dummy DF if we see many dates but logic failed
             # (Allows debugging in front end instead of 404/Null)
             pass 
        raise ValueError("Could not extract any transactions from the PDF. The file may be an image-based PDF or have a non-standard layout.")

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["amount"] = df["amount"].apply(clean_currency)
    df = df.dropna(subset=["date", "amount"])
    df = df[df["amount"] != 0.0]  # drop zero-amount header/footer rows
    df["description"] = df["description"].fillna("").astype(str).str.strip()
    df = df.sort_values("date").reset_index(drop=True)

    return df[["date", "description", "amount"]]


def _resolve_columns(header: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        found_target = False
        for h in header:
            h_clean = h.lower().replace(" ", "_")
            if any(alias in h_clean for alias in aliases):
                mapping[h] = canonical
                found_target = True
                break
        if not found_target:
            # Fallback exact word
            for h in header:
                if any(h.lower().strip() == alias for alias in aliases):
                    mapping[h] = canonical
                    break
    return mapping


def _parse_table(table: list[list[Optional[str]]]) -> list[dict]:
    if not table or len(table) < 2:
        return []

    # Clean header row (first non-empty row)
    header_idx = 0
    while header_idx < len(table) and all(not c or str(c).strip() == "" for c in table[header_idx]):
        header_idx += 1
    
    if header_idx >= len(table): return []
    
    header_row = table[header_idx]
    header = [
        str(h).strip().lower().replace(" ", "_") if h else f"col_{i}"
        for i, h in enumerate(header_row)
    ]
    col_map = _resolve_columns(header)

    rows: list[dict] = []
    for row in table[header_idx + 1:]:
        if not row or all(not c or str(c).strip() == "" for c in row):
            continue
        
        record = {}
        for i, cell in enumerate(row):
            if i < len(header):
                col_name = header[i]
                canonical = col_map.get(col_name)
                if canonical:
                    record[canonical] = str(cell).strip() if cell else ""
        
        if "date" in record and (record.get("amount") or record.get("credit")):
            # Basic validation
            if len(record["date"]) < 5: continue 
            rows.append(record)

    return rows


# More flexible date regex: supports dates anywhere at the start or near-start of a line
# Supports: dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, dd MMM yyyy, etc.
_DATE_RE = re.compile(
    r"(?:\d{1,2}[/\-\.\s](?:\d{1,2}|[A-Za-z]{3})[/\-\.\s](?:\d{4}|\d{2}))",
    re.IGNORECASE
)

# Flexible amount regex: looks for numbers like 1,234.56 or 123.00
_AMOUNT_RE = re.compile(
    r"((?:[+-]?\s*[\$₹€£]?\s*[\d,]+\.\d{2})|(?:\([\$₹€£]?\s*[\d,]+\.\d{2}\)))" # Usually bank amounts have 2 decimals
    r"(?:\s*(?:Dr|Cr|DR|CR|dr|cr))?",
    re.IGNORECASE
)

def _parse_text_lines(text: str) -> list[dict]:
    """A highly flexible parser that extracts any line containing both a date and an amount."""
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 1. Look for a date anywhere in the first half of the line
        date_matches = list(_DATE_RE.finditer(line))
        if not date_matches:
            continue
        
        # Use the first date found
        date_match = date_matches[0]
        date_str = date_match.group(0)
        
        # 2. Look for an amount anywhere after the date
        remaining = line[date_match.end():].strip()
        amt_matches = list(_AMOUNT_RE.finditer(remaining))
        
        if not amt_matches:
            # Try a looser numeric check if 2-decimal check fails
            loose_amt_re = re.compile(r"([\d,]+\.\d{2})")
            amt_matches = list(loose_amt_re.finditer(remaining))

        if not amt_matches:
            continue
            
        # Usually the last amount on the line is the transaction amount (others might be balance)
        # However, many bank statements have [Date] [Description] [Debit] [Credit] [Balance]
        # We'll take the first one found after the date as a heuristic for the transaction.
        amt_match = amt_matches[0]
        amt_str = amt_match.group(0)
        
        # 3. Description is usually between the date and the first amount
        desc_str = remaining[:amt_match.start()].strip()
        
        # Heuristic: If description is empty, check if there's text after the amount
        if not desc_str and len(remaining) > amt_match.end():
             desc_str = remaining[amt_match.end():].strip()

        # Clean common garbage
        if len(desc_str) < 2 and len(line) > 20: 
            desc_str = "Transaction"

        rows.append({
            "date": date_str,
            "description": desc_str if desc_str else "Transaction",
            "amount": amt_str,
        })
    return rows


def _validate_required_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available columns: {df.columns.tolist()}"
        )
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _PDF_ROW_RE.search(line)
        if match:
            rows.append({
                "date": match.group(1),
                "description": match.group(2).strip(),
                "amount": match.group(3).strip(),
            })
    return rows


def _validate_required_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available columns: {df.columns.tolist()}"
        )
