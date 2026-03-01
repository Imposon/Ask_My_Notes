from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction, User
from app.schemas import AnalysisResponse, AnomalyResult, TransactionResponse
from app.services.anomaly_engine import detect_anomalies
from app.services.baseline import compute_baseline, save_baseline
from app.services.explanation_engine import generate_explanations
from app.services.feature_engineering import engineer_features

router = APIRouter(tags=["analysis"])


@router.post("/analyze/{user_id}", response_model=AnalysisResponse)
def analyze_user(
    user_id: str,
    threshold: float = Query(70.0, ge=0, le=100, description="Risk score threshold for flagging"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date)
        .all()
    )
    if not txns:
        raise HTTPException(status_code=404, detail="No transactions found for this user")

    df = _txns_to_dataframe(txns)

    df = engineer_features(df)

    baseline_data = compute_baseline(df)
    save_baseline(db, user_id, baseline_data)

    df = detect_anomalies(df, baseline_data, user_id, threshold=threshold)

    anomaly_results = generate_explanations(df, baseline_data)

    _update_transaction_scores(db, df, anomaly_results)

    return AnalysisResponse(
        user_id=user_id,
        total_transactions=len(df),
        anomalies_found=len(anomaly_results),
        anomalies=anomaly_results,
    )


@router.get("/transactions/{user_id}", response_model=list[TransactionResponse])
def get_transactions(
    user_id: str,
    anomalies_only: bool = Query(False, description="Return only flagged anomalies"),
    db: Session = Depends(get_db),
) -> list[TransactionResponse]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if anomalies_only:
        query = query.filter(Transaction.is_anomaly == True)  # noqa: E712

    txns = query.order_by(Transaction.date).all()
    return txns


def _txns_to_dataframe(txns: list[Transaction]) -> pd.DataFrame:
    rows = []
    for t in txns:
        rows.append({
            "id": t.id,
            "user_id": t.user_id,
            "date": pd.Timestamp(t.date),
            "amount": t.amount,
            "merchant": t.merchant or "Unknown",
            "description": t.description or "",
            "category": t.category or "Others",
            "hour": t.hour or 0,
            "day_of_week": t.day_of_week or 0,
        })
    return pd.DataFrame(rows)


def _update_transaction_scores(db: Session, df: pd.DataFrame, anomaly_results: list[AnomalyResult]) -> None:
    anomaly_map: dict[int, dict] = {}
    for _, row in df.iterrows():
        txn_id = row.get("id")
        if txn_id is None:
            continue
        anomaly_map[int(txn_id)] = {
            "anomaly_score": float(row.get("risk_score", 0)),
            "is_anomaly": bool(row.get("is_anomaly", False)),
        }

    if not anomaly_map:
        return

    # Build explanation map from the already-computed anomaly_results so that
    # the DB stores exactly the same explanations returned by the API response.
    explanation_map: dict[int, list[str]] = {
        r.transaction_id: r.explanations for r in anomaly_results
    }

    txn_ids = list(anomaly_map.keys())
    transactions = db.query(Transaction).filter(Transaction.id.in_(txn_ids)).all()
    for txn in transactions:
        data = anomaly_map.get(txn.id, {})
        txn.anomaly_score = data.get("anomaly_score", 0)
        txn.is_anomaly = data.get("is_anomaly", False)
        # Keep DB explanations consistent with the API response; clear stale
        # explanations for transactions that are no longer flagged.
        txn.explanations = explanation_map.get(txn.id) if txn.is_anomaly else None

    db.commit()


@router.post("/transactions/{user_id}/clear")
def clear_transactions(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": f"All transactions for user {user_id} cleared"}

