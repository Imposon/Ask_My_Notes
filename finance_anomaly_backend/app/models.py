import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(128), nullable=False)
    email = Column(String(256), unique=True, nullable=False, index=True)
    google_id = Column(String(256), unique=True, nullable=True, index=True)
    picture = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    baseline = relationship("UserBaseline", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    merchant = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=True)
    hour = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    explanations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="transactions")


class UserBaseline(Base):
    __tablename__ = "user_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    category_stats = Column(JSON, nullable=True)
    merchant_stats = Column(JSON, nullable=True)
    weekly_avg_spend = Column(Float, nullable=True)
    weekly_std_spend = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="baseline")
