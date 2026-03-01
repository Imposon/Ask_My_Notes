# Personal Finance Anomaly Detector

> Turning transaction data into actionable financial intelligence.


---

## Quick Start

```bash
# 1. Enter the backend directory and activate the virtual environment
cd finance_anomaly_backend
source .venv/bin/activate        # macOS/Linux
pip install -r requirements.txt  # first time only

# 2. Start the FastAPI backend (Terminal 1)
uvicorn app.main:app --reload --port 8000

# 3. Start the Streamlit frontend (Terminal 2)
streamlit run streamlit_app.py
```

- **Backend API:** http://localhost:8000/docs
- **Streamlit UI:** http://localhost:8501

---

## Project Structure

```
├── README.md                          ← You are here
├── Erdiagram.md                       ← Database ER diagram (Mermaid)
├── .gitignore
│
├── finance_anomaly_backend/           ← Main application
│   ├── requirements.txt               ← Python dependencies
│   ├── streamlit_app.py               ← Streamlit frontend (806 lines)
│   ├── finance_anomaly.db             ← SQLite database (auto-created)
│   │
│   └── app/                           ← FastAPI backend package
│       ├── main.py                    ← App entry point, routers, lifespan
│       ├── database.py                ← SQLAlchemy engine & session
│       ├── models.py                  ← ORM models (User, Transaction, UserBaseline)
│       ├── schemas.py                 ← Pydantic request/response schemas
│       │
│       ├── routes/
│       │   ├── upload.py              ← POST /upload (CSV/PDF parsing)
│       │   └── analyze.py             ← POST /analyze, GET /transactions
│       │
│       ├── services/
│       │   ├── parser.py              ← CSV & PDF bank statement parsing
│       │   ├── categorizer.py         ← Keyword-based transaction categorization
│       │   ├── feature_engineering.py ← Feature extraction for ML
│       │   ├── baseline.py            ← Per-user behavioral baseline
│       │   ├── anomaly_engine.py      ← Hybrid detection (statistical + Isolation Forest)
│       │   └── explanation_engine.py  ← Human-readable anomaly explanations
│       │
│       ├── utils/
│       │   └── helpers.py             ← Currency cleaning, merchant extraction, etc.
│       │
│       └── ml_models/                 ← Persisted per-user Isolation Forest models (.pkl)
│
└── notebooks/                         ← Research & demo notebooks
    ├── final_collab.ipynb             ← Standalone Colab prototype
    └── pipeline_demo.ipynb            ← Full backend pipeline walkthrough
```


---

# __Problem Statement__

With the rise of digital banking, users generate massive transaction data across bank accounts, UPI apps, and credit cards.

However, banks only provide **transaction lists**, not **behavioral insights**.

Users cannot easily detect:

- Abnormally high transactions  
- Sudden spending spikes  
- New or suspicious merchants  
- Long-term behavioral shifts  

There is no lightweight, user-centric system that intelligently analyzes personal financial behavior.


---

## __Problem Title__

Personal Finance Anomaly Detector


---

## __Problem Description__

Users receive raw transaction data but lack:

- Personalized anomaly detection  
- Intelligent categorization  
- Behavioral deviation alerts  
- Explainable financial insights  

The system must convert transaction data into **proactive financial awareness**.


---

## __Target Users__

Everyone Who does transaction through online mode or withdraw cash from ATM's


---

## __Existing Gaps__

- **Data without intelligence**
- No personalized anomaly detection
- No explainable alerts
- Reactive financial monitoring
- Fragmented financial data


---

# __Problem Understanding & Approach__


## __Root Cause Analysis__

The issue exists because:

- Transaction formats vary (CSV / PDF)
- “Unusual” is different for every user
- No personalized spending baseline exists
- Systems focus on fraud detection, not behavioral analysis

The real problem is:

> Lack of a personalized anomaly detection system.


---

## __Solution Strategy__

We follow a 3-layer approach:

### 1️Data Normalization
- Parse CSV & PDF
- Standardize columns
- Clean transaction descriptions

### 2️Intelligent Categorization
- Rule-based keyword matching
- Expandable ML classification

# 🔍 __Hybrid Anomaly Detection Framework__

Our system detects anomalies across multiple behavioral dimensions to provide **explainable financial intelligence**.


---

## 1️ __Amount-Based Anomalies__

Detects unusual transaction amounts relative to user history.

- **Z-Score Deviation**  
  Flags transactions significantly higher or lower than personal average.

- **Category-Based Deviation**  
  Compares transaction amount against category-specific historical mean.

- **Extreme Outlier Detection**  
  Identifies transactions far outside normal financial range.


---

## 2️ __Frequency-Based Anomalies__

Detects abnormal transaction bursts or activity spikes.

- **Transaction Burst Detection**  
  Multiple transactions within a short time window.

- **Daily/Weekly Spike Detection**  
  Sudden increase in transaction count compared to rolling average.

- **Rapid Repeat Merchant Activity**  
  Same merchant used multiple times within minutes.


---

## 3️ __Merchant-Based Anomalies__

Detects irregular merchant behavior.

- **New Merchant Detection**  
  First-time transaction with a merchant.

- **Rare Merchant Usage**  
  Merchant historically used very infrequently.

- **Merchant Category Mismatch**  
  Merchant category inconsistent with usual spending behavior.


---

## 4️ __Behavioral Shift Anomalies__

Detects long-term spending pattern changes.

- **Monthly Category Spike**  
  Significant increase compared to last 3-month average.

- **Budget Drift Detection**  
  Category spending exceeds normal proportion.

- **Income-to-Expense Ratio Shift**  
  Sudden imbalance in spending behavior.


---

## 5️ __Location-Based Anomalies__

Detects geographic irregularities.

- **New Location Detection**  
  First transaction from a new city or region.

- **Geo-Deviation Detection**  
  Transaction outside normal geographic radius.

- **Impossible Travel Detection**  
  Transactions occurring in distant cities within unrealistic time gaps.


---

## 6️ __Time-Based Anomalies__

Detects unusual transaction timing behavior.

- **Unusual Time of Day**  
  Transactions outside normal activity hours.

- **Weekend/Weekday Behavior Shift**  
  Spending inconsistent with historical weekday patterns.

- **Night-Time High-Value Transactions**  
  High-risk activity during late hours.


---

## 7️ __Transaction Pattern Anomalies__

Detects structured suspicious behavior.

- **Round Number Pattern Detection**  
  Repeated transactions of identical rounded amounts.

- **Split Transaction Pattern**  
  Large payment divided into multiple smaller transactions.

- **Micro-Transaction Clusters**  
  Multiple small deductions within short duration.


---

## 8️ __Machine Learning-Based Anomalies (Optional Enhancement)__

- **Isolation Forest Detection**  
  Detects multi-dimensional outliers in feature space.

- **Feature-Space Outlier Scoring**  
  Identifies abnormal patterns across combined behavioral features.

- **Composite Risk Score (0–100)**  
  Weighted anomaly scoring model.


---

# __Final Composite Risk Scoring__

Each anomaly dimension contributes to a final **Risk Score (0–100)**:

- Amount Deviation  
- Frequency Spike  
- Merchant Novelty  
- Behavioral Shift  
- Location Irregularity  
- Time-Based Risk  

Only transactions exceeding a defined threshold generate alerts to minimize false positives.


---

> The goal is not just anomaly detection —  
> but **multi-dimensional, explainable financial behavior intelligence.**

Focus: **Explainable AI**, not black-box alerts.


---

# __Proposed Solution__


## __Solution Overview__

A web-based system that:

- Imports bank statements
- Learns personal spending behavior
- Detects anomalies
- Assigns risk scores
- Visualizes irregularities


---

## __Core Idea__

Instead of showing a transaction list, the system:

- Learns what is **normal**
- Detects deviations
- Generates **risk score (0–100)**
- Explains WHY a transaction is unusual

Example:

₹4,982 at SWIGGY  
3.2× higher than usual  
New merchant  
48% increase in food spending  

This transforms raw data into **financial intelligence**.


---

## __Key Features__

### Multi-Format Parsing
- CSV upload
- PDF parsing
- Data cleaning

### Automatic Categorization
- Merchant keyword detection
- ML-based classification (optional)

### Hybrid Anomaly Detection
- Statistical deviation
- Behavioral shift detection
- Frequency spike detection
- New merchant flagging

### Explainable Risk Scoring
- Composite anomaly score
- Clear reasoning for alerts

### Interactive Dashboard
- Spending timeline
- Category breakdown
- Highlighted anomalies
- Monthly comparisons

### Smart Notification System
- Threshold-based alerts
- Reduced false positives


---

# __System Architecture__

Bank Statement  
↓  
Parsing & Normalization  
↓  
Categorization  
↓  
Feature Engineering  
↓  
Anomaly Detection Engine  
↓  
Risk Scoring  
↓  
Dashboard & Alerts  


---

# __Objective__

Move personal finance from:

**Passive transaction viewing**

to

**Proactive behavioral financial monitoring**
