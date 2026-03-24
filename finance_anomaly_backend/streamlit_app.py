"""
Streamlit frontend for the Personal Finance Anomaly Detection System.

Run with:
    streamlit run streamlit_app.py

Make sure the FastAPI backend is running:
    uvicorn app.main:app --reload --port 8000
"""

import json
import time
from io import StringIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import streamlit as st


API_BASE = "http://127.0.0.1:8000"
st.set_page_config(
    page_title="Vortex Finance | AI Anomaly Detector",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

    /* Modern Card Layout (Shadcn-inspired) */
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

    /* Sidebar Refinement */
    section[data-testid="stSidebar"] {
        background-color: #0c0c12;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Buttons with Glow Effect */
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

    /* Tabs Styling (Pearl Finish) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        padding: 4px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 8px;
        border: none;
        transition: all 0.2s ease;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.15) !important;
        color: #818cf8 !important;
    }

    /* Animation Keyframes */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .stMarkdown, .stDataFrame, .stPlotlyChart {
        animation: fadeIn 0.5s ease-out forwards;
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
    
    /* Input Fields (Shadcn style) */
    .stTextInput>div>div>input {
        background-color: rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: #e2e8f0;
        transition: border-color 0.2s ease;
    }
    .stTextInput>div>div>input:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 1px #6366f1;
    }

    /* Expander - Clean Modern Look */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        border-bottom: 1px solid rgba(255,255,255,0.05) !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderContent {
        background-color: rgba(255,255,255,0.01) !important;
    }

    /* Alert Boxes */
    div[data-testid="stNotification"] {
        background-color: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        color: #c7d2fe;
    }
    </style>
    """, unsafe_allow_html=True)


def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend. Is the FastAPI server running on port 8000?"
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail
    except Exception as e:
        return None, str(e)


def api_post(path: str, json_body: dict = None, files=None, params: dict = None):
    try:
        r = requests.post(
            f"{API_BASE}{path}",
            json=json_body,
            files=files,
            params=params,
            timeout=60,
        )
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend. Is the FastAPI server running on port 8000?"
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail
    except Exception as e:
        return None, str(e)


def check_backend() -> bool:
    data, err = api_get("/health")
    return data is not None and data.get("status") == "healthy"


def risk_color(score: float) -> str:
    if score >= 75:
        return ""
    elif score >= 45:
        return ""
    else:
        return ""


def risk_label(score: float) -> str:
    if score >= 75:
        return "HIGH RISK"
    elif score >= 45:
        return "MEDIUM RISK"
    else:
        return "LOW RISK"



if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "transactions" not in st.session_state:
    st.session_state.transactions = None



if not st.session_state.user_id:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-weight: 900; color: #6366f1; font-size: 4rem; margin-bottom: 0px;'>VORTEX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.5); font-size: 1.2rem; margin-top: 0px; letter-spacing: 2px;'>AI ANOMALY DETECTOR</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='background: rgba(255,255,255,0.02); padding: 40px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 10px 30px rgba(0,0,0,0.5);'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; margin-bottom: 5px;'>Secure Login</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-size: 0.9rem; margin-bottom: 25px;'>Sign in or create an account to continue</p>", unsafe_allow_html=True)
        
        backend_ok = check_backend()
        
        name = st.text_input("Full Name", placeholder="e.g. John Doe")
        email = st.text_input("Email Address", placeholder="e.g. john@example.com")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Access Dashboard", use_container_width=True, disabled=not backend_ok):
            if name and email:
                with st.spinner("Authenticating..."):
                    result, err = api_post("/users", json_body={"name": name, "email": email})
                if err:
                    st.error(err)
                else:
                    st.session_state.user_id = result["id"]
                    st.session_state.user_name = result["name"]
                    st.success("Access Granted! Redirecting...")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.warning("All fields are required to continue.")
                
        if not backend_ok:
            st.markdown("<br>", unsafe_allow_html=True)
            st.error("System Offline - Backend is not running on port 8000")
            
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.stop()


with st.sidebar:
    st.markdown("<h1 style='text-align: center; font-weight: 800; color: #6366f1; margin-bottom: 0px;'>VORTEX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-top: 0px;'>AI ANOMALY DETECTOR</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    backend_ok = check_backend()
    if backend_ok:
        st.markdown("<div style='background: rgba(0,255,100,0.1); border: 1px solid rgba(0,255,100,0.2); padding: 10px; border-radius: 8px; color: #00ff66; text-align: center; font-size: 0.85rem; font-weight: 600;'> System Online</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='background: rgba(255,50,50,0.1); border: 1px solid rgba(255,50,50,0.2); padding: 10px; border-radius: 8px; color: #ff3232; text-align: center; font-size: 0.85rem; font-weight: 600;'> System Offline</div>", unsafe_allow_html=True)

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
        st.session_state.analysis_result = None
        st.session_state.transactions = None
        st.rerun()



if page == " Dashboard":
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
        st.info("**Step 1**\n\n Upload your bank statement (CSV or PDF)")
    with col2:
        st.info("**Step 2**\n\n Run anomaly analysis and review results")
    with col3:
        st.info("**Step 3**\n\n Run AI insights and get a summary view")

    st.markdown("---")

    if st.session_state.user_id and st.session_state.transactions:
        df = pd.DataFrame(st.session_state.transactions)

        st.subheader(f" Overview for {st.session_state.user_name}")

        m1, m2, m3, m4 = st.columns(4)
        total = len(df)
        anomalies = df["is_anomaly"].sum() if "is_anomaly" in df.columns else 0
        total_spend = df["amount"].sum()
        avg_spend = df["amount"].mean()

        m1.metric("Total Transactions", f"{total:,}")
        m2.metric("Anomalies Detected", f"{int(anomalies):,}", delta=f"{anomalies/total*100:.1f}% rate" if total > 0 else None, delta_color="inverse")
        m3.metric("Total Spend", f"₹{total_spend:,.0f}")
        m4.metric("Avg Transaction", f"₹{avg_spend:,.0f}")

        st.markdown("---")

        if "category" in df.columns:
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader(" Spending by Category")
                cat_spend = df.groupby("category")["amount"].sum().sort_values(ascending=False)
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
                if "hour" in df.columns:
                    hourly = df.groupby("hour")["amount"].sum()
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
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            ** Detection Methods**
            - **Statistical Scoring**: Compares each transaction against your personal spending baseline
            - **Isolation Forest ML**: Spots multivariate outliers in amount, timing, and frequency
            - **Hybrid Score**: `0.6 × ML + 0.4 × Statistical` → Risk Score (0–100)

            ** Features Analyzed**
            - Transaction amount vs. your category average
            - Time of day (unusual hours flagged)
            - New merchants you've never spent at
            - Weekly spending spikes
            - Rolling 7-day spend window
            """)
        with col_b:
            st.markdown("""
            ** Supported Formats**
            - `.csv` files with `date`, `description`, `amount` columns
            - `.pdf` bank statements (table extraction + regex fallback)

            ** Auto-Categories**
            Food · Transport · Shopping · Subscription · Housing · Entertainment · Bills · Transfer · Others

            ** Risk Levels**
            -  **≥75** — High Risk
            -  **45–74** — Medium Risk
            -  **<45** — Normal
            """)

elif page == " AI Insights":
    st.markdown('<h1 class="main-title">AI Financial Insights</h1>', unsafe_allow_html=True)
    st.markdown(
        """
        <p style="font-size: 1.25rem; color: rgba(255,255,255,0.6); margin-top: -10px;">
        Proactive financial assistant powered by Vortex AI (GPT-4o).
        </p>
        """, unsafe_allow_html=True
    )
    st.markdown("---")

    if not st.session_state.user_id:
        st.warning(" Please create or login with a user profile in the sidebar first.")
        st.stop()

    if not backend_ok:
        st.error(" Backend is not running. Please start the FastAPI server.")
        st.stop()

    if st.button("✨ Generate / Refresh AI Insights", use_container_width=True):
        with st.spinner("Vortex AI is analyzing your financial patterns..."):
            result, err = api_post(f"/ai-insights/{st.session_state.user_id}")
            if err:
                st.error(f"Failed to generate insights: {err}")
                if "OpenAI API key" in str(err):
                    st.info("💡 Tip: Make sure to set `OPENAI_API_KEY` in your environment variables.")
            else:
                st.session_state.ai_insights = result
                st.success("Insights generated successfully!")

    if "ai_insights" in st.session_state:
        insights = st.session_state.ai_insights
        risk_score = insights.get("risk_score", 0)
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            risk_color = "#ff4b4b" if risk_score > 70 else "#ffa500" if risk_score > 40 else "#00ff66"
            risk_label = "CRITICAL" if risk_score > 70 else "MODERATE" if risk_score > 40 else "HEALTHY"
            
            st.markdown(f"""
                <div style='background: rgba(255,255,255,0.03); padding: 30px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3);'>
                    <p style='color: gray; margin-bottom: 5px; font-weight: 600; font-size: 0.9rem;'>VORTEX RISK SCORE</p>
                    <h1 style='color: {risk_color}; font-size: 5.5rem; margin: 0; line-height: 1;'>{risk_score}</h1>
                    <p style='color: {risk_color}; font-weight: 800; letter-spacing: 2px; margin-top: 10px;'>{risk_label}</p>
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
            if st.session_state.transactions:
                df = pd.DataFrame(st.session_state.transactions)
                if "is_anomaly" in df.columns and "anomaly_score" in df.columns:
                    high_risk = df[df["anomaly_score"] >= 75].sort_values("anomaly_score", ascending=False)
                    if not high_risk.empty:
                        st.dataframe(high_risk[["date", "description", "amount", "category", "anomaly_score"]], use_container_width=True)
                    else:
                        st.write("No high-risk anomalies detected in current dataset.")
                else:
                    st.write("Run transaction analysis first to see anomaly flags here.")
            else:
                st.write("No transactions loaded. Please upload a statement first.")

elif page == " Upload Statement":
    st.title(" Upload Bank Statement")

    if not st.session_state.user_id:
        st.warning(" Please create or login with a user profile in the sidebar first.")
        st.stop()

    if not backend_ok:
        st.error(" Backend is not running. Please start the FastAPI server.")
        st.stop()

    st.markdown(f"Uploading for user: **{st.session_state.user_name}**")
    st.markdown("---")

    tab_sample, tab_pdf, tab_csv = st.tabs([" Use Sample Data", " Upload PDF", " Upload CSV"])

    with tab_sample:
        st.markdown("Load a built-in realistic 30-transaction sample to test the pipeline instantly.")

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
            with st.spinner("Uploading sample transactions..."):
                data, err = api_post(
                    "/upload",
                    files={"file": ("sample.csv", sample_csv.encode(), "text/csv")},
                    params={"user_id": st.session_state.user_id},
                )
            if err:
                st.error(f"Upload failed: {err}")
            else:
                st.success(f" {data['transactions_parsed']} sample transactions uploaded! Now go to **Run Analysis**.")
                st.session_state.transactions = None  # Reset cache

    with tab_pdf:
        st.markdown("""
        **PDF Bank Statements** are supported via:
        1. Table extraction (for structured PDFs)
        2. Regex pattern fallback for unstructured layouts

        The parser looks for rows matching: `date  description  amount`
        """)
        uploaded_pdf = st.file_uploader("Choose PDF file", type=["pdf"], key="pdf_upload")
        if uploaded_pdf and st.button(" Upload PDF", use_container_width=True):
            with st.spinner("Extracting and parsing PDF..."):
                data, err = api_post(
                    "/upload",
                    files={"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")},
                    params={"user_id": st.session_state.user_id},
                )
            if err:
                st.error(f"Upload failed: {err}")
            else:
                st.success(f" {data['transactions_parsed']} transactions uploaded!")
                st.json(data)

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
            with st.spinner("Parsing and storing transactions..."):
                data, err = api_post(
                    "/upload",
                    files={"file": (uploaded_csv.name, uploaded_csv.getvalue(), "text/csv")},
                    params={"user_id": st.session_state.user_id},
                )
            if err:
                st.error(f"Upload failed: {err}")
            else:
                st.success(f" {data['transactions_parsed']} transactions uploaded successfully!")
                st.json(data)


elif page == " Run Analysis":
    st.title(" Anomaly Detection Analysis")

    if not st.session_state.user_id:
        st.warning(" Please create or login with a user profile in the sidebar first.")
        st.stop()

    if not backend_ok:
        st.error(" Backend is not running. Please start the FastAPI server.")
        st.stop()

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
        with st.spinner("Running hybrid anomaly detection pipeline..."):
            progress = st.progress(0, text="Feature engineering...")
            time.sleep(0.3)
            progress.progress(30, text="Computing behavioral baseline...")
            time.sleep(0.3)
            progress.progress(60, text="Running Isolation Forest...")

            result, err = api_post(
                f"/analyze/{st.session_state.user_id}",
                params={"threshold": threshold},
            )
            progress.progress(90, text="Generating explanations...")
            time.sleep(0.2)
            progress.progress(100, text="Done!")
            time.sleep(0.3)
            progress.empty()

        if err:
            st.error(f"Analysis failed: {err}")
        else:
            st.session_state.analysis_result = result
            txns, _ = api_get(f"/transactions/{st.session_state.user_id}")
            if txns:
                st.session_state.transactions = txns
            st.success(" Analysis complete!")

    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        st.markdown("---")
        st.subheader(" Analysis Results")

        m1, m2, m3, m4 = st.columns(4)
        total = result["total_transactions"]
        found = result["anomalies_found"]
        rate = found / total * 100 if total > 0 else 0

        m1.metric("Total Transactions", f"{total:,}")
        m2.metric("Anomalies Detected", f"{found:,}", delta=f"{rate:.1f}% of total", delta_color="inverse")
        m3.metric("Normal Transactions", f"{total - found:,}")
        m4.metric("Detection Threshold", f"{threshold}")

        st.markdown("---")

        if result["anomalies"]:
            anomalies = result["anomalies"]

            anomalies = sorted(anomalies, key=lambda x: x["risk_score"], reverse=True)

            st.subheader(f" Flagged Anomalies ({len(anomalies)})")

            scores = [a["risk_score"] for a in anomalies]
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                fig, ax = plt.subplots(figsize=(6, 3))
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

            with col_chart2:
                risk_counts = {
                    " High (≥75)": sum(1 for s in scores if s >= 75),
                    " Medium (45-74)": sum(1 for s in scores if 45 <= s < 75),
                    " Low (<45)": sum(1 for s in scores if s < 45),
                }
                non_zero = {k: v for k, v in risk_counts.items() if v > 0}
                if non_zero:
                    fig2, ax2 = plt.subplots(figsize=(5, 3))
                    clrs = ["#d62728" if "High" in k else "#ff7f0e" if "Medium" in k else "#2ca02c" for k in non_zero]
                    ax2.pie(non_zero.values(), labels=non_zero.keys(), colors=clrs,
                            autopct="%1.0f%%", startangle=90)
                    ax2.set_title("Risk Level Distribution")
                    plt.tight_layout()
                    st.pyplot(fig2)
                    plt.close()

            st.markdown("---")

            st.subheader(" Anomaly Details")

            txn_map = {}
            if st.session_state.transactions:
                for t in st.session_state.transactions:
                    txn_map[t["id"]] = t

            for i, anom in enumerate(anomalies, 1):
                txn = txn_map.get(anom["transaction_id"], {})
                score = anom["risk_score"]
                icon = risk_color(score)
                label = risk_label(score)

                default_desc = "Transaction #" + str(anom["transaction_id"])
                desc_label = txn.get("description", default_desc)[:55]
                with st.expander(
                    f"{icon} #{i} — {desc_label}  |  "
                    f"₹{txn.get('amount', 0):,.0f}  |  Risk: {score:.1f} ({label})",
                    expanded=i <= 3,
                ):
                    col_l, col_r = st.columns([1, 1])
                    with col_l:
                        st.markdown(f"**Transaction ID:** `{anom['transaction_id']}`")
                        st.markdown(f"**Date:** {txn.get('date', 'N/A')[:19] if txn.get('date') else 'N/A'}")
                        st.markdown(f"**Amount:** ₹{txn.get('amount', 0):,.2f}")
                        st.markdown(f"**Category:** {txn.get('category', 'Unknown')}")
                        st.markdown(f"**Merchant:** {txn.get('merchant', 'Unknown')}")
                        st.markdown(f"**Hour:** {txn.get('hour', 'N/A')}:00")

                    with col_r:
                        st.markdown(f"**Risk Score:** {score:.1f} / 100")
                        bar_html = f"""
                        <div style="background:#eee;border-radius:5px;height:18px;width:100%">
                          <div style="background:{'#d62728' if score>=75 else '#ff7f0e' if score>=45 else '#2ca02c'};
                                      width:{score}%;height:18px;border-radius:5px"></div>
                        </div>
                        """
                        st.markdown(bar_html, unsafe_allow_html=True)
                        st.markdown("")
                        st.markdown("**Why flagged:**")
                        for reason in anom.get("explanations", ["Unusual pattern detected"]):
                            st.markdown(f"  → {reason}")

        else:
            st.success("🎉 No anomalies detected with current threshold. Try lowering the threshold to be more sensitive.")


elif page == " Transactions":
    st.title(" Transaction History")

    if not st.session_state.user_id:
        st.warning(" Please create or login with a user profile in the sidebar first.")
        st.stop()

    if not backend_ok:
        st.error(" Backend is not running. Please start the FastAPI server.")
        st.stop()

    col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
    with col_f1:
        anomalies_only = st.toggle(" Show Anomalies Only", value=False)
    with col_f2:
        if st.button(" Refresh", use_container_width=True):
            st.session_state.transactions = None
    with col_f3:
        if st.button(" Clear Transactions", use_container_width=True):
            with st.spinner("Clearing history..."):
                _, err = api_post(f"/transactions/{st.session_state.user_id}/clear")
                if err:
                    st.error(f"Failed to clear: {err}")
                else:
                    st.session_state.transactions = None
                    st.session_state.analysis_result = None
                    st.success("Transactions cleared!")
                    st.rerun()

    if not st.session_state.transactions or anomalies_only:
        with st.spinner("Loading transactions..."):
            txns, err = api_get(
                f"/transactions/{st.session_state.user_id}",
                params={"anomalies_only": str(anomalies_only).lower()},
            )
        if err:
            st.error(f"Failed to load transactions: {err}")
            st.stop()
        if not anomalies_only:
            st.session_state.transactions = txns
    else:
        txns = st.session_state.transactions

    if not txns:
        st.info("No transactions found. Upload a bank statement first.")
        st.stop()

    df = pd.DataFrame(txns)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Transactions", f"{len(df):,}")
    if "is_anomaly" in df.columns:
        anom_count = df["is_anomaly"].sum()
        m2.metric("Anomalies", f"{int(anom_count):,}")
    if "amount" in df.columns:
        m3.metric("Total Spend", f"₹{df['amount'].sum():,.0f}")

    st.markdown("---")

    with st.expander(" Filters", expanded=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            if "category" in df.columns:
                cats = ["All"] + sorted(df["category"].dropna().unique().tolist())
                sel_cat = st.selectbox("Category", cats)
        with f_col2:
            if "amount" in df.columns:
                min_amt = float(df["amount"].min())
                max_amt = float(df["amount"].max())
                if min_amt == max_amt:
                    st.info(f"Amount: ₹{min_amt:,.2f}")
                    amt_range = (min_amt, max_amt)
                else:
                    amt_range = st.slider("Amount Range (₹)", min_amt, max_amt, (min_amt, max_amt))
        with f_col3:
            sort_by = st.selectbox("Sort By", ["date", "amount", "anomaly_score", "category"])

    disp = df.copy()
    if "category" in df.columns and sel_cat != "All":
        disp = disp[disp["category"] == sel_cat]
    if "amount" in df.columns:
        disp = disp[(disp["amount"] >= amt_range[0]) & (disp["amount"] <= amt_range[1])]
    if sort_by in disp.columns:
        disp = disp.sort_values(sort_by, ascending=False)

    show_cols = ["date", "description", "amount", "category", "merchant", "hour"]
    if "is_anomaly" in disp.columns:
        show_cols += ["is_anomaly", "anomaly_score"]

    show_cols = [c for c in show_cols if c in disp.columns]
    disp_show = disp[show_cols].copy()

    if "date" in disp_show.columns:
        disp_show["date"] = disp_show["date"].astype(str).str[:19]

    def highlight_anomaly(row):
        is_anom = row.get("is_anomaly")
        # Handle cases where is_anomaly might be a string or boolean
        if str(is_anom).lower() == "true":
            return ["background-color: rgba(255, 75, 75, 0.25); color: #ff4b4b; font-weight: 700;"] * len(row)
        return ["background-color: #0e1117; color: rgba(255,255,255,0.8);"] * len(row)

    st.dataframe(
        disp_show.style.apply(highlight_anomaly, axis=1),
        use_container_width=True,
        height=600,
    )

    st.caption(f"Showing {len(disp_show):,} of {len(df):,} transactions. Anomalies highlighted in red.")

    csv_out = disp_show.to_csv(index=False)
    st.download_button(
        " Download as CSV",
        data=csv_out,
        file_name=f"transactions_{st.session_state.user_id[:8]}.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.subheader(" Transaction Insights")

    tab1, tab2, tab3 = st.tabs(["Category Breakdown", "Timeline", "Amount Distribution"])

    with tab1:
        if "category" in df.columns and "amount" in df.columns:
            cat_data = df.groupby("category")["amount"].agg(["sum", "count"]).reset_index()
            cat_data.columns = ["Category", "Total Spend", "Count"]
            cat_data = cat_data.sort_values("Total Spend", ascending=False)

            fig, ax = plt.subplots(figsize=(10, 4))
            colors = plt.cm.Set3(np.linspace(0, 1, len(cat_data)))
            ax.bar(cat_data["Category"], cat_data["Total Spend"], color=colors)
            ax.set_ylabel("Total Amount (₹)")
            ax.set_title("Spending by Category")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()
            st.dataframe(cat_data, use_container_width=True)

    with tab2:
        if "date" in df.columns and "amount" in df.columns:
            timeline = df.copy()
            timeline["date"] = pd.to_datetime(timeline["date"])
            timeline = timeline.sort_values("date")

            fig, ax = plt.subplots(figsize=(12, 4))
            normal = timeline[~timeline.get("is_anomaly", pd.Series([False] * len(timeline))).astype(bool)]
            anomal = timeline[timeline.get("is_anomaly", pd.Series([False] * len(timeline))).astype(bool)]

            ax.scatter(normal["date"], normal["amount"], color="steelblue", alpha=0.6, s=40, label="Normal")
            if len(anomal) > 0:
                ax.scatter(anomal["date"], anomal["amount"], color="red", s=80, marker="^",
                           edgecolors="black", linewidth=1, label="Anomaly", zorder=5)
            ax.set_xlabel("Date")
            ax.set_ylabel("Amount (₹)")
            ax.set_title("Transaction Timeline")
            ax.legend()
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

    with tab3:
        if "amount" in df.columns:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.hist(df["amount"], bins=30, color="steelblue", edgecolor="white", alpha=0.8)
            ax.axvline(df["amount"].mean(), color="red", linestyle="--",
                       label=f"Mean: ₹{df['amount'].mean():,.0f}")
            ax.axvline(df["amount"].median(), color="green", linestyle="--",
                       label=f"Median: ₹{df['amount'].median():,.0f}")
            ax.set_xlabel("Amount (₹)")
            ax.set_ylabel("Frequency")
            ax.set_title("Transaction Amount Distribution")
            ax.legend()
            plt.tight_layout()
            st.pyplot(fig)
            plt.close()


elif page == " About":
    st.title(" About This System")

    st.markdown("""

    This system answers: **"Is this transaction unusual for THIS user?"**

    ---


    | Layer | Component | Description |
    |-------|-----------|-------------|
    | **Frontend** | Streamlit | Interactive UI for upload, analysis, and visualization |
    | **Backend** | FastAPI | REST API for data ingestion and analysis |
    | **Database** | SQLite | Stores users, transactions, baselines |
    | **ML** | Isolation Forest | Per-user model with `contamination='auto'` |

    ---


    ```
    CSV/PDF Upload
         ↓
    Parsing & Cleaning
         ↓
    Auto-Categorization (keyword-based)
         ↓
    Feature Engineering (7 features from 3 raw columns)
         ↓
    Behavioral Baseline (per-category & per-merchant stats)
         ↓
    Statistical Scoring (4 sub-scores × weights)
         ↓
    Isolation Forest ML Score
         ↓
    Hybrid Score = 0.6 × ML + 0.4 × Statistical
         ↓
    Explanation Generation
         ↓
    Results via API / Streamlit UI
    ```

    ---


    | Feature | Weight | Description |
    |---------|--------|-------------|
    | `abs_amount` | — | Absolute transaction value |
    | `hour_of_day` | 25% | Circular distance from preferred hour |
    | `day_of_week` | — | Day 0=Mon to 6=Sun |
    | `days_since_last_transaction` | — | Gap between consecutive transactions |
    | `rolling_7_day_spend` | 20% | 7-day trailing spend |
    | `merchant_frequency` | 20% | First-time merchant flag |
    | `category_frequency` | 35% | Amount deviation vs category baseline |

    ---


    ```bash
    cd finance_anomaly_backend
    source .venv/bin/activate
    uvicorn app.main:app --reload --port 8000

    cd finance_anomaly_backend
    source .venv/bin/activate
    streamlit run streamlit_app.py
    ```

    **API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
    """)
