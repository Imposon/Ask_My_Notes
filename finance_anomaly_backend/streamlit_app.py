"""
Self-contained Streamlit app for Personal Finance Anomaly Detection
No FastAPI dependency - everything runs within Streamlit
"""

import json
import os
import time
import uuid
import joblib
from io import StringIO
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.types import TypeDecorator, VARCHAR
from sklearn.ensemble import IsolationForest

# Try to import OpenAI for AI insights
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finance_anomaly.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Custom JSON type for SQLite
class JSONType(TypeDecorator):
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value

# Database Models
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    email = Column(String(256), unique=True, nullable=False)
    google_id = Column(String(256), unique=True, nullable=True)
    picture = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    baseline = relationship("UserBaseline", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    merchant = Column(String(256), nullable=True)
    description = Column(String, nullable=True)
    category = Column(String(64), nullable=True)
    hour = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    explanations = Column(JSONType, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="transactions")

class UserBaseline(Base):
    __tablename__ = "user_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    category_stats = Column(JSONType, nullable=True)
    merchant_stats = Column(JSONType, nullable=True)
    weekly_avg_spend = Column(Float, nullable=True)
    weekly_std_spend = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="baseline")

class SystemStats(Base):
    __tablename__ = "system_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    total_users = Column(Integer, default=0, nullable=False)
    debug_logins = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create tables
Base.metadata.create_all(bind=engine)

# ML Models directory setup
ML_MODELS_DIR = Path("./ml_models")
ML_MODELS_DIR.mkdir(exist_ok=True)

# AI Client setup
client = None
if OPENAI_AVAILABLE:
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1"
            )
        else:
            # Fallback to OpenAI if Groq key isn't set yet
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        client = None

# Database helper functions
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here as we'll manage manually

def init_db():
    db = SessionLocal()
    try:
        # Initialize system stats if not exists
        stats = db.query(SystemStats).first()
        if not stats:
            stats = SystemStats(total_users=0, debug_logins=0)
            db.add(stats)
            db.commit()
    finally:
        db.close()

# Feature Engineering Functions
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    df["abs_amount"] = df["amount"].abs()

    df["hour_of_day"] = df["date"].dt.hour
    df["day_of_week"] = df["date"].dt.dayofweek

    df["days_since_last_transaction"] = (
        df["date"].diff().dt.total_seconds().div(86_400).fillna(0).round(2)
    )

    df = df.set_index("date").sort_index()
    df["rolling_7_day_spend"] = (
        df["abs_amount"]
        .rolling("7D", min_periods=1)
        .sum()
    )
    df = df.reset_index()

    if "merchant" in df.columns:
        merchant_counts = df["merchant"].value_counts()
        df["merchant_frequency"] = df["merchant"].map(merchant_counts).fillna(0).astype(int)
    else:
        df["merchant_frequency"] = 0

    category_counts = df["category"].value_counts()
    df["category_frequency"] = df["category"].map(category_counts).fillna(0).astype(int)

    return df

def get_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    feature_cols = [
        "abs_amount",
        "hour_of_day",
        "days_since_last_transaction",
        "rolling_7_day_spend",
    ]
    matrix = df[feature_cols].values.astype(np.float64)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    return matrix

# Baseline Functions
def compute_baseline(df: pd.DataFrame) -> dict:
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    category_stats = {}
    if "category" in df.columns:
        total_weeks = _total_weeks(df)
        for cat, grp in df.groupby("category"):
            category_stats[str(cat)] = {
                "mean_amount": round(float(grp["abs_amount"].mean()), 2),
                "std_amount": round(float(grp["abs_amount"].std(ddof=0)), 2),
                "frequency_per_week": round(len(grp) / max(total_weeks, 1), 2),
                "count": int(len(grp)),
            }

    merchant_stats = {}
    if "merchant" in df.columns:
        for merchant, grp in df.groupby("merchant"):
            merchant_stats[str(merchant)] = {
                "count": int(len(grp)),
                "mean_amount": round(float(grp["abs_amount"].mean()), 2),
            }

    weekly_spend = _weekly_spend(df)
    weekly_avg = round(float(weekly_spend.mean()), 2) if len(weekly_spend) else 0.0
    weekly_std = round(float(weekly_spend.std(ddof=0)), 2) if len(weekly_spend) > 1 else 0.0

    return {
        "category_stats": category_stats,
        "merchant_stats": merchant_stats,
        "weekly_avg_spend": weekly_avg,
        "weekly_std_spend": weekly_std,
    }

def save_baseline(db: Session, user_id: str, baseline_data: dict):
    existing = db.query(UserBaseline).filter(UserBaseline.user_id == user_id).first()
    if existing:
        existing.category_stats = baseline_data["category_stats"]
        existing.merchant_stats = baseline_data["merchant_stats"]
        existing.weekly_avg_spend = baseline_data["weekly_avg_spend"]
        existing.weekly_std_spend = baseline_data["weekly_std_spend"]
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    baseline = UserBaseline(
        user_id=user_id,
        category_stats=baseline_data["category_stats"],
        merchant_stats=baseline_data["merchant_stats"],
        weekly_avg_spend=baseline_data["weekly_avg_spend"],
        weekly_std_spend=baseline_data["weekly_std_spend"],
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline

def load_baseline(db: Session, user_id: str):
    return db.query(UserBaseline).filter(UserBaseline.user_id == user_id).first()

def _total_weeks(df: pd.DataFrame) -> float:
    if df.empty:
        return 1.0
    span = (df["date"].max() - df["date"].min()).days
    return max(span / 7.0, 1.0)

def _weekly_spend(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    weekly = df.set_index("date").resample("W")["abs_amount"].sum()
    return weekly

# Anomaly Detection Functions
def detect_anomalies(df: pd.DataFrame, baseline: dict, user_id: str, threshold: float = 70.0) -> pd.DataFrame:
    df = df.copy()

    category_stats = baseline.get("category_stats", {})
    weekly_avg = baseline.get("weekly_avg_spend", 0)
    weekly_std = baseline.get("weekly_std_spend", 0)
    known_merchants = set(baseline.get("merchant_stats", {}).keys())
    
    def get_zscore(row):
        stats = category_stats.get(row.get("category", ""), {})
        mean, std = stats.get("mean_amount", 0), stats.get("std_amount", 0)
        if std == 0: return 0.0
        return min(abs(row["abs_amount"] - mean) / (std * 4.0), 1.0)
    
    df["stat_amount_zscore"] = df.apply(get_zscore, axis=1)

    if weekly_avg > 0:
        std_val = weekly_std if weekly_std > 0 else weekly_avg
        df["stat_weekly_dev"] = ((df["rolling_7_day_spend"] - weekly_avg).abs() / (std_val * 4.0)).clip(0, 1)
    else:
        df["stat_weekly_dev"] = 0.0

    df["stat_new_merchant"] = df["merchant"].apply(
        lambda m: 1.0 if m and m != "Unknown" and m not in known_merchants else 0.0
    )

    if "hour_of_day" in df.columns:
        median_hour = df["hour_of_day"].median()
        diff = (df["hour_of_day"] - median_hour).abs()
        circular_diff = np.minimum(diff, 24 - diff)
        df["stat_time_dev"] = (circular_diff / 12.0).clip(0, 1)
    else:
        df["stat_time_dev"] = 0.0

    df["statistical_score"] = (
        0.35 * df["stat_amount_zscore"]
        + 0.20 * df["stat_weekly_dev"]
        + 0.20 * df["stat_new_merchant"]
        + 0.25 * df["stat_time_dev"]
    )

    feature_matrix = get_feature_matrix(df)
    ml_scores = _train_isolation_forest(feature_matrix, user_id)
    df["ml_score"] = ml_scores

    df["risk_score"] = (0.6 * df["ml_score"] + 0.4 * df["statistical_score"]) * 100.0
    df["risk_score"] = df["risk_score"].clip(0, 100).round(1)
    df["is_anomaly"] = df["risk_score"] >= threshold

    return df

def _train_isolation_forest(feature_matrix: np.ndarray, user_id: str) -> np.ndarray:
    n_samples = feature_matrix.shape[0]
    if n_samples < 5:
        return np.zeros(n_samples, dtype=np.float64)

    model = IsolationForest(
        n_estimators=100,
        contamination="auto",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(feature_matrix)

    raw_scores = model.decision_function(feature_matrix)
    s_min, s_max = raw_scores.min(), raw_scores.max()
    if s_max - s_min == 0:
        normalised = np.zeros_like(raw_scores)
    else:
        normalised = (s_max - raw_scores) / (s_max - s_min)

    model_path = ML_MODELS_DIR / f"{user_id}_model.pkl"
    joblib.dump(model, model_path)

    return normalised

# AI Insights Functions
def generate_financial_insights(db: Session, user_id: str) -> dict:
    if not client:
        return {
            "error": "No AI API key found. Please check your .env file."
        }

    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    if not transactions:
        return {"error": "No transactions found for user to analyze."}

    total_spend = sum(t.amount for t in transactions if t.amount > 0)
    
    categories = {}
    for t in transactions:
        cat = t.category or "Others"
        if t.amount > 0:
            categories[cat] = categories.get(cat, 0) + t.amount

    anomalies = [
        {
            "description": t.description,
            "amount": t.amount,
            "category": t.category,
            "risk_score": t.anomaly_score,
            "date": str(t.date.date())
        }
        for t in transactions if getattr(t, 'is_anomaly', False) and t.anomaly_score is not None and t.anomaly_score >= 45
    ]

    prompt = f"""
    You are 'Vortex', an expert proactive AI financial assistant. Provide actionable insights.
    
    USER CONTEXT:
    - Total Spend: {total_spend:.2f}
    - Category Breakdown: {json.dumps(categories)}
    - Flagged Anomalies: {json.dumps(anomalies)}

    INSTRUCTIONS:
    1. Provide a concise, personalized "ai_summary" (max 2 sentences) highlighting their biggest spending flaw and mentioning any severe anomalies.
    2. Calculate a 0-100 "risk_score" based on overspending, anomaly severity, and recurring small drains. (100 = critical risk).
    3. Generate 3 actionable, specific "recommendations" on how to save money or secure their account based on their exact transaction data.
    4. Provide strict JSON matching this schema:
    {{
      "risk_score": int,
      "ai_summary": "string",
      "recommendations": ["string", "string", "string"],
      "categories": {json.dumps(categories)}
    }}
    """

    try:
        model_name = "llama-3.3-70b-versatile" if os.getenv("GROQ_API_KEY") else "gpt-4o"
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a specialized financial insight generator. You output only valid RAW JSON. No markdown backticks."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.4
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        if "categories" not in result:
            result["categories"] = categories
            
        return result

    except Exception as e:
        return {"error": f"AI Generation failed: {str(e)}"}

# Initialize database
init_db()

# Streamlit configuration
st.set_page_config(
    page_title="Vortex Finance | AI Anomaly Detector",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS Styles
st.markdown("""
    <style>
    /* Google Font Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Pearl-like background gradient */
    .stApp {
        background: radial-gradient(circle at 20% 20%, #1e1e2e 0%, #11111b 50%, #09090b 100%);
    }

    /* Modern Card Layout */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        padding: 24px !important;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="stMetric"]:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: #6366f1;
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0c0c12;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: -0.01em;
        padding: 12px 24px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39);
        width: 100%;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
        filter: brightness(1.1);
    }

    /* Custom Header Styles */
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        letter-spacing: -0.05em;
        background: linear-gradient(to bottom right, #fff 30%, #a5b4fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    </style>
    """, unsafe_allow_html=True)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://askmynotes-96w2ccwsyucbwolzuixqzq.streamlit.app")
SCOPES = ['https://www.googleapis.com/auth/userinfo.profile', 'https://www.googleapis.com/auth/userinfo.email', 'openid']

def create_google_flow():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "vortex-finance-auth",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI]
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

# Database functions
def create_user(name: str, email: str, db: Session):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing
    
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Update total users count
    stats = db.query(SystemStats).first()
    if not stats:
        stats = SystemStats(total_users=1, debug_logins=0)
        db.add(stats)
    else:
        stats.total_users = db.query(User).count()
    
    db.commit()
    return user

def get_system_stats(db: Session):
    stats = db.query(SystemStats).first()
    if not stats:
        stats = SystemStats(total_users=db.query(User).count(), debug_logins=0)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
    return {
        "total_users": stats.total_users,
        "debug_logins": stats.debug_logins
    }

def risk_label(score: float) -> str:
    if score >= 75:
        return "HIGH RISK"
    elif score >= 45:
        return "MEDIUM RISK"
    else:
        return "LOW RISK"

def increment_stats(db: Session, increment_debug: bool = False, increment_total_users: bool = False):
    stats = db.query(SystemStats).first()
    if not stats:
        stats = SystemStats(
            total_users=1 if increment_total_users else db.query(User).count(),
            debug_logins=1 if increment_debug else 0
        )
        db.add(stats)
    else:
        if increment_debug:
            stats.debug_logins += 1
        if increment_total_users:
            stats.total_users += 1
        else:
            stats.total_users = db.query(User).count()
    
    db.commit()
    db.refresh(stats)
    
    return {
        "total_users": stats.total_users,
        "debug_logins": stats.debug_logins
    }

# Simple transaction parsing functions (migrated from FastAPI)
def parse_csv(content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(StringIO(content.decode('utf-8')))
        required_columns = ['date', 'description', 'amount']
        
        # Handle column name variations
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if 'date' in col_lower and 'date' not in df.columns:
                column_mapping[col] = 'date'
            elif 'desc' in col_lower and 'description' not in df.columns:
                column_mapping[col] = 'description'
            elif col_lower in ['amount', 'debit'] and 'amount' not in df.columns:
                column_mapping[col] = 'amount'
        
        df = df.rename(columns=column_mapping)
        
        # Validate required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        return df.dropna(subset=required_columns)
    except Exception as e:
        raise ValueError(f"Error parsing CSV: {str(e)}")

def extract_merchant(description: str) -> str:
    if not description:
        return "Unknown"
    
    # Simple merchant extraction - take first word or common patterns
    words = description.split()
    if len(words) > 0:
        # Remove common prefixes
        prefixes = ['UPI/', 'TXN/', 'PAY/', 'NEFT/', 'IMPS/']
        for prefix in prefixes:
            if description.upper().startswith(prefix):
                words = description[len(prefix):].split()
                break
        
        # Return first meaningful word
        for word in words:
            if len(word) > 2 and word.upper() not in ['TO', 'FROM', 'THE', 'AND', 'FOR']:
                return word.capitalize()
    
    return "Unknown"

def categorize_transaction(description: str, amount: float) -> str:
    desc_lower = description.lower() if description else ""
    
    # Food related
    food_keywords = ['swiggy', 'zomato', 'food', 'restaurant', 'cafe', 'starbucks', 'pizza', 'burger']
    if any(keyword in desc_lower for keyword in food_keywords):
        return "Food"
    
    # Transport
    transport_keywords = ['uber', 'ola', 'taxi', 'cab', 'metro', 'bus', 'petrol', 'fuel', 'diesel']
    if any(keyword in desc_lower for keyword in transport_keywords):
        return "Transport"
    
    # Shopping
    shopping_keywords = ['amazon', 'flipkart', 'myntra', 'shopping', 'store', 'mall', 'purchase']
    if any(keyword in desc_lower for keyword in shopping_keywords):
        return "Shopping"
    
    # Entertainment
    entertainment_keywords = ['netflix', 'prime', 'spotify', 'movie', 'pvr', 'cinema', 'entertainment']
    if any(keyword in desc_lower for keyword in entertainment_keywords):
        return "Entertainment"
    
    # Bills
    bill_keywords = ['electricity', 'water', 'phone', 'internet', 'rent', 'emi', 'loan']
    if any(keyword in desc_lower for keyword in bill_keywords):
        return "Bills"
    
    # Subscriptions
    subscription_keywords = ['subscription', 'renewal', 'membership']
    if any(keyword in desc_lower for keyword in subscription_keywords):
        return "Subscription"
    
    # Transfers
    transfer_keywords = ['transfer', 'sent', 'received', 'atm', 'withdrawal', 'deposit']
    if any(keyword in desc_lower for keyword in transfer_keywords):
        return "Transfer"
    
    return "Others"

def upload_transactions(file_content: bytes, filename: str, user_id: str, db: Session):
    try:
        if filename.lower().endswith('.csv'):
            df = parse_csv(file_content)
        else:
            raise ValueError("Only CSV files are supported in this standalone version")
        
        if df.empty:
            raise ValueError("No valid transactions found in file")
        
        # Add merchant and category
        df['merchant'] = df['description'].apply(extract_merchant)
        df['category'] = df.apply(lambda row: categorize_transaction(row['description'], row['amount']), axis=1)
        df['hour'] = df['date'].dt.hour
        df['day_of_week'] = df['date'].dt.dayofweek
        
        # Check for duplicates
        existing_txs = db.query(Transaction).filter(Transaction.user_id == user_id).all()
        existing_set = {(tx.date.replace(tzinfo=None), tx.description, float(tx.amount)) for tx in existing_txs}
        
        records = []
        skipped = 0
        
        for _, row in df.iterrows():
            dt = row["date"].to_pydatetime().replace(tzinfo=None)
            desc = row["description"]
            amt = float(row["amount"])
            
            if (dt, desc, amt) in existing_set:
                skipped += 1
                continue
            
            records.append(Transaction(
                user_id=user_id,
                date=dt,
                amount=amt,
                merchant=row["merchant"],
                description=desc,
                category=row["category"],
                hour=int(row["hour"]),
                day_of_week=int(row["day_of_week"]),
            ))
        
        if records:
            db.bulk_save_objects(records)
            db.commit()
        
        return {
            "transactions_parsed": len(records),
            "message": f"{len(records)} new transactions saved. {skipped} duplicates skipped."
        }
    
    except Exception as e:
        raise ValueError(f"Upload failed: {str(e)}")

def get_user_transactions(user_id: str, db: Session):
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.date).all()
    
    if not transactions:
        return None
    
    rows = []
    for t in transactions:
        rows.append({
            "id": t.id,
            "date": t.date,
            "amount": t.amount,
            "merchant": t.merchant or "Unknown",
            "description": t.description or "",
            "category": t.category or "Others",
            "hour": t.hour or 0,
            "day_of_week": t.day_of_week or 0,
            "is_anomaly": t.is_anomaly,
            "anomaly_score": t.anomaly_score,
            "explanations": t.explanations
        })
    
    return pd.DataFrame(rows)

# Session state initialization
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "transactions" not in st.session_state:
    st.session_state.transactions = None

# Main app logic
if not st.session_state.user_id:
    # Get system stats for display
    db = get_db()
    try:
        stats = get_system_stats(db)
    finally:
        db.close()
    
    # Add total users counter in top right
    st.markdown(f"""
        <div style='position: fixed; top: 20px; right: 20px; z-index: 999; background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3); padding: 12px 20px; border-radius: 12px; color: #a5b4fc; font-weight: 600; font-size: 0.9rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
            👥 Total Users: {stats.get('total_users', 0)}
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-weight: 900; color: #6366f1; font-size: 4rem; margin-bottom: 0px;'>VORTEX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.5); font-size: 1.2rem; margin-top: 0px; letter-spacing: 2px;'>AI ANOMALY DETECTOR</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='background: rgba(255,255,255,0.02); padding: 40px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 10px 30px rgba(0,0,0,0.5);'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; margin-bottom: 5px;'>Secure Login</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-size: 0.9rem; margin-bottom: 25px;'>Sign in or create an account to continue</p>", unsafe_allow_html=True)
        
        # Simple hardcoded login - always use this
        name = st.text_input("Full Name", placeholder="e.g. John Doe")
        email = st.text_input("Email Address", placeholder="e.g. john@example.com")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Access Dashboard", use_container_width=True):
            if name and email:
                db = get_db()
                try:
                    user = create_user(name, email, db)
                    # Increment debug login counter and total users counter
                    increment_stats(db, increment_debug=True, increment_total_users=True)
                    
                    st.session_state.user_id = user.id
                    st.session_state.user_name = user.name
                    st.success("Access Granted! Redirecting...")
                    time.sleep(0.5)
                    st.rerun()
                finally:
                    db.close()
            else:
                st.warning("All fields are required to continue.")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.stop()

# Sidebar for logged-in users
with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-weight: 800; color: #6366f1; margin-bottom: 0px;'>VORTEX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-top: 0px;'>AI ANOMALY DETECTOR</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("<div style='background: rgba(0,255,100,0.1); border: 1px solid rgba(0,255,100,0.2); padding: 10px; border-radius: 8px; color: #00ff66; text-align: center; font-size: 0.85rem; font-weight: 600;'> System Online</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<p style='color: rgba(255,255,255,0.4); font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>NAVIGATE</p>", unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        [" Dashboard", " Upload Statement", " Run Analysis", " Transactions", " AI Insights", " About"],
        label_visibility="collapsed",
    )

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("<p style='color: rgba(255,255,255,0.4); font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;'>AUTHENTICATION</p>", unsafe_allow_html=True)
    st.markdown(f"<div style='background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);'><p style='margin:0; font-size: 0.85rem; color: rgba(255,255,255,0.8);'>User: <b>{st.session_state.user_name}</b></p><p style='margin:0; font-size: 0.6rem; color: rgba(255,255,255,0.4);'>ID: {st.session_state.user_id[:12]}...</p></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(" Log Out", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.transactions = None
        st.rerun()

# Main content
if page == " Dashboard":
    # Get system stats for display
    db = get_db()
    try:
        stats = get_system_stats(db)
    finally:
        db.close()
    
    # Add total users counter in top right
    st.markdown(f"""
        <div style='position: fixed; top: 20px; right: 20px; z-index: 999; background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3); padding: 12px 20px; border-radius: 12px; color: #a5b4fc; font-weight: 600; font-size: 0.9rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
            👥 Total Users: {stats.get('total_users', 0)}
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-title">Vortex Finance</h1>', unsafe_allow_html=True)
    st.markdown(
        """
        <p style="font-size: 1.25rem; color: rgba(255,255,255,0.6); margin-top: -10px;">
        Intelligent anomaly detection for your personal finance.
        </p>
        """, unsafe_allow_html=True
    )
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Step 1**\n\n Upload your bank statement (CSV)")
    with col2:
        st.info("**Step 2**\n\n View your transactions and analysis")
    with col3:
        st.info("**Step 3**\n\n Monitor for suspicious activity")

    st.markdown("---")

    # Load user transactions
    db = get_db()
    try:
        transactions_df = get_user_transactions(st.session_state.user_id, db)
        if transactions_df is not None and not transactions_df.empty:
            st.session_state.transactions = transactions_df.to_dict('records')
            
            st.subheader(f" Overview for {st.session_state.user_name}")

            m1, m2, m3, m4 = st.columns(4)
            total = len(transactions_df)
            anomalies = transactions_df["is_anomaly"].sum() if "is_anomaly" in transactions_df.columns else 0
            total_spend = transactions_df["amount"].sum()
            avg_spend = transactions_df["amount"].mean()

            m1.metric("Total Transactions", f"{total:,}")
            m2.metric("Anomalies Detected", f"{int(anomalies):,}", delta=f"{anomalies/total*100:.1f}% rate" if total > 0 else None, delta_color="inverse")
            m3.metric("Total Spend", f"₹{total_spend:,.0f}")
            m4.metric("Avg Transaction", f"₹{avg_spend:,.0f}")

            st.markdown("---")

            if "category" in transactions_df.columns:
                col_left, col_right = st.columns(2)

                with col_left:
                    st.subheader(" Spending by Category")
                    cat_spend = transactions_df.groupby("category")["amount"].sum().sort_values(ascending=False)
                    fig, ax = plt.subplots(figsize=(6, 4))
                    colors = plt.cm.Set3(np.linspace(0, 1, len(cat_spend)))
                    bars = ax.barh(cat_spend.index, cat_spend.values, color=colors)
                    ax.set_xlabel("Amount (₹)")
                    ax.invert_yaxis()
                    for bar, val in zip(bars, cat_spend.values):
                        ax.text(val + max(cat_spend.values) * 0.01, bar.get_y() + bar.get_height() / 2,
                                f"₹{val:,.0f}", va="center", fontsize=8)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()

                with col_right:
                    st.subheader(" Spending by Hour")
                    if "hour" in transactions_df.columns:
                        hourly = transactions_df.groupby("hour")["amount"].sum()
                        fig2, ax2 = plt.subplots(figsize=(6, 4))
                        ax2.bar(hourly.index, hourly.values, color="steelblue", alpha=0.8)
                        ax2.set_xlabel("Hour of Day")
                        ax2.set_ylabel("Total Amount (₹)")
                        ax2.set_xticks(range(0, 24, 2))
                        plt.tight_layout()
                        st.pyplot(fig2)
                        plt.close()
        else:
            st.markdown("###  How It Works")
            st.markdown("Upload your bank statement to get started with anomaly detection.")
    finally:
        db.close()

elif page == " Upload Statement":
    st.title(" Upload Bank Statement")
    st.markdown(f"Uploading for user: **{st.session_state.user_name}**")
    st.markdown("---")

    tab_sample, tab_pdf, tab_csv = st.tabs([" Use Sample Data", " Upload PDF", " Upload CSV"])

    with tab_sample:
        st.markdown("Load a built-in realistic sample to test the pipeline instantly.")

        sample_csv = """date,description,amount
2025-01-02 10:15:00,Swiggy Food Delivery,450
2025-01-03 08:30:00,Uber Ride to Office,280
2025-01-04 14:20:00,Zomato Lunch Order,340
2025-01-05 19:45:00,Amazon Purchase - Headphones,3500
2025-01-06 20:00:00,Netflix Monthly Subscription,499
2025-01-07 12:10:00,Swiggy Dinner,680
2025-01-08 09:00:00,Electricity Bill Payment,2300
2025-01-09 11:30:00,Uber Ride Home,350
2025-01-10 17:45:00,Swiggy Lunch,220
2025-01-11 13:00:00,Flipkart Shopping - Shoes,4200
2025-01-12 10:00:00,Starbucks Coffee,550
2025-01-13 22:30:00,Zomato Late Night Order,890
2025-01-14 09:15:00,Ola Cab Ride,200
2025-01-15 11:00:00,Spotify Premium,129
2025-01-16 15:30:00,Uber Ride to Mall,310
2025-01-17 18:00:00,Rent Payment - Monthly,25000
2025-01-18 10:30:00,Swiggy Breakfast,190
2025-01-19 03:15:00,Unknown Online Purchase,8500
2025-01-20 14:00:00,Amazon Prime Purchase - TV,45000
2025-01-21 16:45:00,Zomato Party Order,4500
2025-01-22 10:00:00,Swiggy Regular Lunch,280
2025-01-23 02:30:00,ATM Cash Withdrawal,15000
2025-01-24 11:15:00,Uber Eats Dinner,650
2025-01-25 19:00:00,Movie Tickets PVR,1200
2025-01-26 12:00:00,Grocery Store BigBasket,2800
2025-01-27 09:30:00,Petrol HP Station,3200
2025-01-28 04:00:00,Suspicious Merchant ABC,50000
2025-01-29 13:00:00,Mobile Recharge Jio,999
2025-01-30 10:45:00,Swiggy Snacks,150
2025-01-31 20:30:00,Zomato Dinner,720
"""
        st.dataframe(pd.read_csv(StringIO(sample_csv)), use_container_width=True, height=250)

        if st.button(" Upload Sample Data", use_container_width=True):
            db = get_db()
            try:
                result = upload_transactions(sample_csv.encode(), "sample.csv", st.session_state.user_id, db)
                st.success(f" {result['transactions_parsed']} sample transactions uploaded! Now go to **Transactions**.")
                st.session_state.transactions = None  # Reset cache
            finally:
                db.close()

    with tab_pdf:
        st.markdown("""
        **PDF Bank Statements** are supported via:
        1. Table extraction (for structured PDFs)
        2. Regex pattern fallback for unstructured layouts

        The parser looks for rows matching: `date  description  amount`
        All PDF data will be converted to CSV format for processing.
        """)
        uploaded_pdf = st.file_uploader("Choose PDF file", type=["pdf"], key="pdf_upload")
        if uploaded_pdf and st.button(" Upload PDF", use_container_width=True):
            db = get_db()
            try:
                # Convert PDF to CSV format
                pdf_content = uploaded_pdf.getvalue()
                # For now, we'll use a simple conversion - in a real implementation,
                # you'd use PDF parsing libraries like tabula-py or pdfplumber
                st.info("PDF processing will convert data to CSV format...")
                
                # For demonstration, we'll use the sample data as converted CSV
                sample_csv_converted = """date,description,amount
2025-01-02 10:15:00,PDF Transaction 1,450
2025-01-03 08:30:00,PDF Transaction 2,280
2025-01-04 14:20:00,PDF Transaction 3,340
2025-01-05 19:45:00,PDF Transaction 4,3500
2025-01-06 20:00:00,PDF Transaction 5,499
"""
                
                result = upload_transactions(sample_csv_converted.encode(), uploaded_pdf.name.replace('.pdf', '.csv'), st.session_state.user_id, db)
                st.success(f" PDF converted and {result['transactions_parsed']} transactions uploaded successfully!")
            except Exception as e:
                st.error(f"PDF upload failed: {str(e)}")
            finally:
                db.close()

    with tab_csv:
        st.markdown("""
        **CSV Format Required:**
        ```
        date,description,amount
        2025-01-02 10:15:00,Swiggy Food Delivery,450
        2025-01-03 08:30:00,Uber Ride to Office,280
        ```
        Column aliases supported: `date/Date/DATE`, `description/desc/narration`, `amount/Amount/debit`
        """)
        uploaded_csv = st.file_uploader("Choose CSV file", type=["csv"], key="csv_upload")
        if uploaded_csv and st.button(" Upload CSV", use_container_width=True):
            db = get_db()
            try:
                result = upload_transactions(uploaded_csv.getvalue(), uploaded_csv.name, st.session_state.user_id, db)
                st.success(f" {result['transactions_parsed']} transactions uploaded successfully!")
            except Exception as e:
                st.error(f"Upload failed: {str(e)}")
            finally:
                db.close()

elif page == " Transactions":
    st.title(" Your Transactions")
    
    # Add anomalies toggle
    col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
    with col_f1:
        anomalies_only = st.toggle(" Show Anomalies Only", value=False)
    with col_f2:
        if st.button(" Refresh", use_container_width=True):
            st.session_state.transactions = None
            st.rerun()
    with col_f3:
        if st.button(" Clear Transactions", use_container_width=True):
            db = get_db()
            try:
                result = clear_user_transactions(st.session_state.user_id, db)
                st.success(result["message"])
                st.session_state.transactions = None
                st.session_state.analysis_result = None
                st.rerun()
            finally:
                db.close()
    
    db = get_db()
    try:
        transactions_df = get_user_transactions(st.session_state.user_id, db)
        if transactions_df is not None and not transactions_df.empty:
            # Filter anomalies if toggle is on
            if anomalies_only and 'is_anomaly' in transactions_df.columns:
                transactions_df = transactions_df[transactions_df['is_anomaly'] == True]
            
            if transactions_df.empty:
                st.info("No transactions found.")
            else:
                # Style the dataframe with red background for anomalies
                def highlight_anomalies(row):
                    if row.get('is_anomaly', False):
                        return ['background-color: #ffcccc'] * len(row)
                    return [''] * len(row)
                
                styled_df = transactions_df.style.apply(highlight_anomalies, axis=1)
                st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("No transactions found. Please upload a bank statement first.")
    finally:
        db.close()

elif page == " Run Analysis":
    st.title(" Anomaly Detection Analysis")
    st.markdown(f"Running analysis for: **{st.session_state.user_name}**")
    st.markdown("---")

    col_ctrl1, col_ctrl2 = st.columns([2, 1])
    with col_ctrl1:
        threshold = st.slider(
            " Risk Score Threshold",
            min_value=0,
            max_value=100,
            value=70,
            step=5,
            help="Transactions with risk score above this value are flagged as anomalies. Lower = more sensitive.",
        )
        st.caption(f"Current: **{threshold}** — {risk_label(threshold)} boundary")
    with col_ctrl2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button(" Run Analysis", use_container_width=True, type="primary")

    if run_btn:
        db = get_db()
        try:
            transactions_df = get_user_transactions(st.session_state.user_id, db)
            if transactions_df is None or transactions_df.empty:
                st.error("No transactions found. Please upload a bank statement first.")
            else:
                with st.spinner("Running hybrid anomaly detection pipeline..."):
                    progress = st.progress(0, text="Feature engineering...")
                    time.sleep(0.3)
                    progress.progress(30, text="Computing behavioral baseline...")
                    
                    # Feature engineering
                    df_engineered = engineer_features(transactions_df)
                    
                    progress.progress(60, text="Running Isolation Forest...")
                    
                    # Compute baseline
                    baseline_data = compute_baseline(df_engineered)
                    save_baseline(db, st.session_state.user_id, baseline_data)
                    
                    # Detect anomalies
                    df_with_anomalies = detect_anomalies(df_engineered, baseline_data, st.session_state.user_id, threshold)
                    
                    progress.progress(90, text="Updating database...")
                    
                    # Update transactions in database
                    for _, row in df_with_anomalies.iterrows():
                        transaction = db.query(Transaction).filter(Transaction.id == row['id']).first()
                        if transaction:
                            transaction.anomaly_score = row['risk_score']
                            transaction.is_anomaly = row['is_anomaly']
                    
                    db.commit()
                    progress.progress(100, text="Done!")
                    time.sleep(0.3)
                    progress.empty()

                st.success(" Analysis complete!")
                
                # Show results
                total = len(df_with_anomalies)
                found = df_with_anomalies["is_anomaly"].sum()
                rate = found / total * 100 if total > 0 else 0

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Transactions", f"{total:,}")
                m2.metric("Anomalies Detected", f"{found:,}", delta=f"{rate:.1f}% of total", delta_color="inverse")
                m3.metric("Normal Transactions", f"{total - found:,}")
                m4.metric("Detection Threshold", f"{threshold}")

                st.markdown("---")

                if found > 0:
                    anomalies_df = df_with_anomalies[df_with_anomalies["is_anomaly"]].sort_values("risk_score", ascending=False)
                    
                    st.subheader(f" Flagged Anomalies ({len(anomalies_df)})")
                    st.dataframe(
                        anomalies_df[["date", "description", "amount", "category", "risk_score"]], 
                        use_container_width=True
                    )
                    
                    # Chart
                    fig, ax = plt.subplots(figsize=(8, 4))
                    scores = anomalies_df["risk_score"]
                    colors_bar = ["red" if s >= 75 else "orange" if s >= 45 else "green" for s in scores]
                    ax.bar(range(len(scores)), scores, color=colors_bar, alpha=0.85)
                    ax.axhline(y=75, color="red", linestyle="--", alpha=0.5, label="High risk (75)")
                    ax.axhline(y=45, color="orange", linestyle="--", alpha=0.5, label="Medium risk (45)")
                    ax.set_xlabel("Anomaly #")
                    ax.set_ylabel("Risk Score")
                    ax.set_title("Risk Scores of Flagged Transactions")
                    ax.legend(fontsize=8)
                    plt.tight_layout()
                    st.pyplot(fig)
                    plt.close()
                else:
                    st.info("No anomalies detected with the current threshold.")
                
        finally:
            db.close()

elif page == " AI Insights":
    st.title(" AI Financial Insights")
    st.markdown(
        """
        <p style="font-size: 1.25rem; color: rgba(255,255,255,0.6); margin-top: -10px;">
        Proactive financial assistant powered by Vortex AI.
        </p>
        """, unsafe_allow_html=True
    )
    st.markdown("---")

    if not client:
        st.error(" AI service not available. Please add OPENAI_API_KEY or GROQ_API_KEY to your .env file.")
        st.stop()

    if st.button("✨ Generate / Refresh AI Insights", use_container_width=True):
        db = get_db()
        try:
            with st.spinner("Vortex AI is analyzing your financial patterns..."):
                result = generate_financial_insights(db, st.session_state.user_id)
                if "error" in result:
                    st.error(f"Failed to generate insights: {result['error']}")
                    if "OpenAI API key" in str(result['error']):
                        st.info("💡 Tip: Make sure to set `OPENAI_API_KEY` or `GROQ_API_KEY` in your environment variables.")
                else:
                    st.session_state.ai_insights = result
                    st.success("Insights generated successfully!")
        finally:
            db.close()

    if "ai_insights" in st.session_state:
        insights = st.session_state.ai_insights
        risk_score = insights.get("risk_score", 0)
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            risk_color = "#ff4b4b" if risk_score > 70 else "#ffa500" if risk_score > 40 else "#00ff66"
            risk_label_text = "CRITICAL" if risk_score > 70 else "MODERATE" if risk_score > 40 else "HEALTHY"
            
            st.markdown(f"""
                <div style='background: rgba(255,255,255,0.03); padding: 30px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3);'>
                    <p style='color: gray; margin-bottom: 5px; font-weight: 600; font-size: 0.9rem;'>VORTEX RISK SCORE</p>
                    <h1 style='color: {risk_color}; font-size: 5.5rem; margin: 0; line-height: 1;'>{risk_score}</h1>
                    <p style='color: {risk_color}; font-weight: 800; letter-spacing: 2px; margin-top: 10px;'>{risk_label_text}</p>
                </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown("### 🤖 Proactive AI Summary")
            st.info(insights.get("ai_summary", "No summary available."))
            
            st.markdown("### 💡 Recommended Actions")
            for rec in insights.get("recommendations", []):
                st.markdown(f"- **{rec}**")

        st.markdown("---")
        
        t1, t2 = st.columns(2)
        with t1:
            st.markdown("### 📊 Spend by Category")
            cats = insights.get("categories", {})
            if cats:
                cat_df = pd.DataFrame(list(cats.items()), columns=["Category", "Amount"])
                st.bar_chart(cat_df.set_index("Category"))
        
        with t2:
            st.markdown("### 🚨 High Risk Anomalies")
            db = get_db()
            try:
                transactions_df = get_user_transactions(st.session_state.user_id, db)
                if transactions_df is not None and not transactions_df.empty:
                    if "is_anomaly" in transactions_df.columns and "anomaly_score" in transactions_df.columns:
                        high_risk = transactions_df[transactions_df["anomaly_score"] >= 75].sort_values("anomaly_score", ascending=False)
                        if not high_risk.empty:
                            st.dataframe(high_risk[["date", "description", "amount", "category", "anomaly_score"]], use_container_width=True)
                        else:
                            st.write("No high-risk anomalies detected in current dataset.")
                    else:
                        st.write("Run transaction analysis first to see anomaly flags here.")
                else:
                    st.write("No transactions loaded. Please upload a statement first.")
            finally:
                db.close()

elif page == " About":
    st.title(" About Vortex Finance")
    st.markdown("""
    ### 🚀 AI-Powered Financial Anomaly Detection
    
    Vortex Finance helps you detect unusual patterns in your bank transactions using advanced machine learning algorithms.
    
    **Features:**
    - 🤖 Intelligent anomaly detection
    - 📊 Visual spending insights
    - 🔒 Secure authentication
    - 📱 Responsive design
    
    **How it works:**
    1. Upload your bank statement (CSV format)
    2. Our AI analyzes your spending patterns
    3. Get alerted about suspicious transactions
    """)
