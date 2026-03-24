from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    name: str
    email: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    google_id: Optional[str] = None
    picture: Optional[str] = None
    created_at: datetime


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    date: datetime
    amount: float
    merchant: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    hour: Optional[int] = None
    day_of_week: Optional[int] = None
    anomaly_score: Optional[float] = None
    is_anomaly: bool = False
    explanations: Optional[list[str]] = None
    created_at: datetime



class UploadResponse(BaseModel):
    user_id: str
    transactions_parsed: int
    message: str = "Transactions uploaded successfully"



class AnomalyResult(BaseModel):
    transaction_id: int
    risk_score: float
    explanations: list[str]


class AnalysisResponse(BaseModel):
    user_id: str
    total_transactions: int
    anomalies_found: int
    anomalies: list[AnomalyResult]
