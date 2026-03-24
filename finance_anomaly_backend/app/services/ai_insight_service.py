import json
import os
from typing import Dict, Any

from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Transaction

# Initialize Groq client (using OpenAI-compatible SDK)
# Groq provides high-speed Llama models for free/low cost
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

def generate_financial_insights(db: Session, user_id: str) -> Dict[str, Any]:
    if not client:
        return {
            "error": "No AI API key found. Please check your .env file."
        }

    # 1. Gather User Context from DB
    transactions = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    if not transactions:
        return {"error": "No transactions found for user to analyze."}

    total_spend = sum(t.amount for t in transactions if t.amount > 0)
    
    # Aggregate spending by category
    categories = {}
    for t in transactions:
        cat = t.category or "Others"
        if t.amount > 0:
            categories[cat] = categories.get(cat, 0) + t.amount

    # Collect anomalies (High risk)
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

    # 2. Construct the Prompt
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
        # Use Groq's super-fast Llama-3.3-70b/3.1-8b model
        # llama-3.3-70b-versatile is excellent for complex reasoning
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
