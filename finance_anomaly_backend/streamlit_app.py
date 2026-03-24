import json
import os
import time
from io import StringIO, BytesIO
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import requests as r_lib
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# --- Project Imports ---
from app.database import SessionLocal, create_all
from app.models import User, Transaction, UserBaseline
from app.services.parser import parse_csv, parse_pdf
from app.services.categorizer import categorize_dataframe
from app.services.anomaly_engine import detect_anomalies
from app.services.ai_insight_service import generate_financial_insights
from app.services.baseline import compute_baseline, save_baseline
from app.services.feature_engineering import engineer_features
from app.utils.helpers import extract_merchant, ensure_ml_models_dir

# Initialize System
create_all()
ensure_ml_models_dir()

st.set_page_config(
    page_title="Vortex Finance | AI Anomaly Detector",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- OAuth Configuration ---
def get_redirect_uri():
    if os.environ.get("SPACE_ID"):
        return f"https://huggingface.co/spaces/{os.environ.get('SPACE_ID')}"
    return "http://localhost:8501"

CLIENT_CONFIG = {
    "web": {
        "client_id": "55008642184-2ev9e0vbk088m6u7vblogsa801v3167c.apps.googleusercontent.com",
        "client_secret": "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",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [get_redirect_uri()]
    }
}
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

def get_auth_url():
    redirect_uri = get_redirect_uri()
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": CLIENT_CONFIG['web']['client_id'],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    query_str = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_str}"

def handle_oauth_callback(code):
    redirect_uri = get_redirect_uri()
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": CLIENT_CONFIG['web']['client_id'],
        "client_secret": CLIENT_CONFIG['web']['client_secret'],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    res = r_lib.post(token_url, data=data)
    res_data = res.json()
    if "error" in res_data:
        raise Exception(f"{res_data.get('error')}: {res_data.get('error_description')}")
    info = id_token.verify_oauth2_token(
        res_data["id_token"], google_requests.Request(), CLIENT_CONFIG['web']['client_id']
    )
    return info

# --- Monolith Service Wrappers ---
def api_get(path: str, params: dict = None):
    params = params or {}
    db = SessionLocal()
    try:
        if path == "/health":
            return {"status": "healthy"}, None
        if path == "/users/count":
            return {"count": db.query(User).count()}, None
        if path.startswith("/transactions/"):
            user_id = path.split("/")[-1]
            anom_only = params.get("anomalies_only") == "true"
            query = db.query(Transaction).filter(Transaction.user_id == user_id)
            if anom_only: query = query.filter(Transaction.is_anomaly == True)
            txns = query.order_by(Transaction.date.desc()).all()
            return [{"id": t.id, "date": t.date.isoformat(), "description": t.description, "amount": t.amount, "category": t.category, "merchant": t.merchant, "is_anomaly": t.is_anomaly, "anomaly_score": t.anomaly_score} for t in txns], None
        return None, "Not Found"
    finally:
        db.close()

def api_post(path: str, json_body: dict = None, files=None, params: dict = None):
    params = params or {}
    db = SessionLocal()
    try:
        if path == "/users":
            user = db.query(User).filter(User.email == json_body['email']).first()
            if not user:
                user = User(name=json_body['name'], email=json_body['email'])
                db.add(user)
                db.commit()
                db.refresh(user)
            return {"id": user.id, "name": user.name}, None
        
        if path == "/upload":
            user_id = params.get("user_id")
            filename, content = files['file'][0], files['file'][1]
            df = parse_pdf(content) if filename.endswith(".pdf") else parse_csv(content.decode())
            if df.empty: return None, "No transactions found in file"
            df = categorize_dataframe(df)
            df["merchant"] = df["description"].apply(extract_merchant)
            db.query(Transaction).filter(Transaction.user_id == user_id).delete()
            records = [Transaction(user_id=user_id, date=row["date"].to_pydatetime(), amount=float(row["amount"]), merchant=row["merchant"], description=row["description"], category=row["category"], hour=int(row["date"].hour), day_of_week=int(row["date"].dayofweek)) for _, row in df.iterrows()]
            db.bulk_save_objects(records)
            db.commit()
            return {"transactions_parsed": len(records)}, None
            
        if path.startswith("/analyze/"):
            user_id = path.split("/")[-1]
            threshold = float(params.get("threshold", 70))
            txns = db.query(Transaction).filter(Transaction.user_id == user_id).all()
            if not txns: return None, "No data to analyze"
            df = pd.DataFrame([{"id": t.id, "date": t.date, "amount": t.amount, "description": t.description, "merchant": t.merchant, "category": t.category} for t in txns])
            df = engineer_features(df)
            baseline = compute_baseline(df)
            save_baseline(db, user_id, baseline)
            res_df = detect_anomalies(df, baseline, user_id, threshold)
            res_df = res_df.drop_duplicates(subset=["id"])
            res_map = res_df.set_index("id")[["is_anomaly", "risk_score", "explanations"]].to_dict('index')
            for t in txns:
                if t.id in res_map:
                    m = res_map[t.id]
                    t.is_anomaly, t.anomaly_score = bool(m["is_anomaly"]), float(m["risk_score"])
            db.commit()
            anoms = [{"transaction_id": k, "risk_score": v["risk_score"], "explanations": v["explanations"]} for k, v in res_map.items() if v["is_anomaly"]]
            return {"total_transactions": len(txns), "anomalies_found": len(anoms), "anomalies": anoms}, None

        if path.endswith("/clear"):
            user_id = path.split("/")[-2]
            db.query(Transaction).filter(Transaction.user_id == user_id).delete()
            db.commit()
            return {"status": "cleared"}, None

        if path.startswith("/ai-insights/"):
            user_id = path.split("/")[-1]
            txns = db.query(Transaction).filter(Transaction.user_id == user_id).all()
            if not txns: return None, "No data for AI"
            df = pd.DataFrame([{"date": t.date, "amount": t.amount, "description": t.description, "category": t.category, "is_anomaly": t.is_anomaly} for t in txns])
            insights = generate_financial_insights(df)
            return insights, None

        return None, "Not Found"
    except Exception as e:
        return None, str(e)
    finally:
        db.close()

# --- Styling ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: radial-gradient(circle at 20% 20%, #1e1e2e 0%, #11111b 50%, #09090b 100%); }
    div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.03); padding: 24px !important; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08); }
    section[data-testid="stSidebar"] { background-color: #0c0c12; border-right: 1px solid rgba(255, 255, 255, 0.05); }
    .main-title { font-size: 3.5rem; font-weight: 900; background: linear-gradient(to bottom right, #fff 30%, #a5b4fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
    """, unsafe_allow_html=True)

# --- App State ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "user_name" not in st.session_state: st.session_state.user_name = None
if "user_email" not in st.session_state: st.session_state.user_email = None
if "transactions" not in st.session_state: st.session_state.transactions = None
if "analysis_result" not in st.session_state: st.session_state.analysis_result = None

# OAuth Callback
qp = st.query_params
if "code" in qp:
    try:
        info = handle_oauth_callback(qp["code"])
        st.query_params.clear()
        res, err = api_post("/users", json_body={"name": info['name'], "email": info['email']})
        if not err:
            st.session_state.update({"user_id": res["id"], "user_name": res["name"], "user_email": info['email']})
            st.rerun()
    except Exception as e:
        st.error(f"Auth Failed: {e}")

# Login Screen
if not st.session_state.user_id:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-weight: 900; color: #6366f1; font-size: 4.5rem; margin-bottom: 0px;'>VORTEX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.5); font-size: 1.2rem; margin-top: 0px; letter-spacing: 2px;'>AI ANOMALY DETECTOR</p>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<div style='background: rgba(255,255,255,0.02); padding: 40px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; margin-bottom: 25px; color: white;'>Secure Login</h3>", unsafe_allow_html=True)
        st.markdown(f"<a href='{get_auth_url()}' target='_self' style='text-decoration:none;'><div style='background:white; color:#444; padding:12px; border-radius:8px; text-align:center; font-weight:700; display:flex; align-items:center; justify-content:center; gap:10px; border:1px solid #ddd;'><img src='https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg' width='20px'/>Continue with Google</div></a>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-weight: 800; color: #6366f1; margin: 0;'>VORTEX</h1>", unsafe_allow_html=True)
    st.markdown("<div style='background: rgba(0,255,100,0.1); border: 1px solid rgba(0,255,100,0.2); padding: 5px; border-radius: 8px; color: #00ff66; text-align: center; font-size: 0.75rem; font-weight: 600;'>System Online</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    page = st.radio("Navigate", [" Dashboard", " Upload Statement", " Run Analysis", " Transactions", " AI Insights", " About"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown(f"<p style='opacity:0.6; font-size:0.8rem; color:white;'>User: {st.session_state.user_name}</p>", unsafe_allow_html=True)
    if st.button("Log Out"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# Pages
if page == " Dashboard":
    st.markdown('<h1 class="main-title">Vortex Finance</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: rgba(255,255,255,0.6); font-size: 1.2rem; margin-top: -10px;'>Intelligent anomaly detection for your personal finance.</p>", unsafe_allow_html=True)
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1: st.info("**Step 1**\n\n Upload your bank statement (CSV or PDF)")
    with col2: st.info("**Step 2**\n\n Run anomaly analysis and review results")
    with col3: st.info("**Step 3**\n\n Run AI insights and get a summary view")
    st.markdown("---")
    if not st.session_state.transactions:
        txns, _ = api_get(f"/transactions/{st.session_state.user_id}")
        st.session_state.transactions = txns
    if st.session_state.transactions:
        df = pd.DataFrame(st.session_state.transactions)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Transactions", f"{len(df):,}")
        anoms = int(df['is_anomaly'].sum())
        m2.metric("Anomalies", f"{anoms:,}", delta=f"{anoms/len(df)*100:.1f}%" if len(df)>0 else None, delta_color="inverse")
        m3.metric("Total Spend", f"₹{df['amount'].sum():,.0f}")
        m4.metric("Avg Transaction", f"₹{df['amount'].mean():,.0f}")
    else:
        st.warning("No data yet. Head to **Upload Statement** to begin.")

elif page == " Upload Statement":
    st.title(" Upload Bank Statement")
    ts1, ts2, ts3 = st.tabs([" Use Sample Data", " Upload PDF", " Upload CSV"])
    with ts1:
        if st.button("Load Sample Data"):
            csv = "date,description,amount\n2025-01-01 10:00:00,Swiggy,450\n2025-01-02 12:00:00,Uber,300\n2025-01-05 02:00:00,Suspicious Large Txn,85000"
            api_post("/upload", files={"file": ("sample.csv", csv.encode())}, params={"user_id": st.session_state.user_id})
            st.success("Sample Loaded!")
            st.session_state.transactions = None
    with ts2:
        up_pdf = st.file_uploader("Choose PDF", type=["pdf"])
        if up_pdf and st.button("Upload PDF"):
            api_post("/upload", files={"file": (up_pdf.name, up_pdf.getvalue())}, params={"user_id": st.session_state.user_id})
            st.success("PDF Uploaded!")
            st.session_state.transactions = None
    with ts3:
        up_csv = st.file_uploader("Choose CSV", type=["csv"])
        if up_csv and st.button("Upload CSV"):
            api_post("/upload", files={"file": (up_csv.name, up_csv.getvalue())}, params={"user_id": st.session_state.user_id})
            st.success("CSV Uploaded!")
            st.session_state.transactions = None

elif page == " Run Analysis":
    st.title(" Anomaly Detection")
    th = st.slider("Threshold", 0, 100, 70)
    if st.button("Run Analysis", type="primary"):
        res, err = api_post(f"/analyze/{st.session_state.user_id}", params={"threshold": th})
        if not err:
            st.session_state.analysis_result = res
            st.success("Analysis Complete!")
            st.session_state.transactions = None

elif page == " Transactions":
    st.title(" Transaction History")
    if st.button("Clear History"):
        api_post(f"/transactions/{st.session_state.user_id}/clear")
        st.session_state.transactions = None
        st.rerun()
    if not st.session_state.transactions: 
        txns, _ = api_get(f"/transactions/{st.session_state.user_id}")
        st.session_state.transactions = txns
    if st.session_state.transactions:
        st.dataframe(pd.DataFrame(st.session_state.transactions), use_container_width=True)

elif page == " AI Insights":
    st.title(" AI Insights")
    if st.button("Generate Insights"):
        res, err = api_post(f"/ai-insights/{st.session_state.user_id}")
        if not err: st.info(res.get("ai_summary", "No summary"))

elif page == " About":
    st.title(" About This System")
    data, _ = api_get("/users/count")
    if data:
        st.metric("👥 Total Registered Users", f"{data['count']:,}")
    
    # Admin View
    if st.session_state.user_email == "8461000993as@gmail.com":
        st.markdown("---")
        st.subheader("👨‍💻 Admin View: Registered Users")
        db = SessionLocal()
        users = db.query(User).all()
        db.close()
        user_list = [{"Name": u.name, "Email": u.email, "Join Date": u.created_at.strftime("%Y-%m-%d")} for u in users]
        st.table(user_list)
    
    st.markdown("""Vortex answers: **'Is this transaction unusual for THIS user?'** via hybrid Statistical + ML scoring.""")
