from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, User
from app.schemas import UploadResponse
from app.services.categorizer import categorize_dataframe
from app.services.parser import parse_csv, parse_pdf
from app.utils.helpers import extract_merchant

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    user_id: str = Query(..., description="UUID of the user"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    filename = (file.filename or "").lower()
    try:
        if filename.endswith(".pdf"):
            df = parse_pdf(content)
        elif filename.endswith(".csv"):
            df = parse_csv(content)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a .csv or .pdf file.",
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if df.empty:
        raise HTTPException(status_code=422, detail="No valid transactions found in the file.")

    df = categorize_dataframe(df)

    df["merchant"] = df["description"].apply(extract_merchant)
    df["hour"] = df["date"].dt.hour
    df["day_of_week"] = df["date"].dt.dayofweek

    records: list[Transaction] = []
    skipped = 0
    
    # Pre-fetch existing transaction hashes for this user to deduplicate efficiently
    existing_txs = db.query(Transaction.date, Transaction.description, Transaction.amount).filter(
        Transaction.user_id == user_id
    ).all()
    
    # Create a set of (date, desc, amount) tuples for fast lookup
    # We use .date() or timestamp comparison depending on frequency, but tuple is safest.
    existing_set = { (tx.date.replace(tzinfo=None), tx.description, float(tx.amount)) for tx in existing_txs }

    for _, row in df.iterrows():
        # Prepare current row tuple for comparison
        dt = row["date"].to_pydatetime().replace(tzinfo=None)
        desc = row["description"]
        amt = float(row["amount"])
        
        if (dt, desc, amt) in existing_set:
            skipped += 1
            continue

        records.append(
            Transaction(
                user_id=user_id,
                date=dt,
                amount=amt,
                merchant=row["merchant"],
                description=desc,
                category=row["category"],
                hour=int(row["hour"]),
                day_of_week=int(row["day_of_week"]),
            )
        )

    if records:
        db.bulk_save_objects(records)
        db.commit()

    return UploadResponse(
        user_id=user_id,
        transactions_parsed=len(records),
        message=f"{len(records)} new transactions saved. {skipped} duplicates skipped."
    )
