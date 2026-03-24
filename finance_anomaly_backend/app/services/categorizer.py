import os
import json
import pandas as pd
from openai import OpenAI

# Use Groq for categorization for free/cheap high-speed Llama models
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
except:
    client = None


# Keyword → category mapping.  Keys are lowercase substrings matched against
# the transaction description.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Food": [
        "zomato", "swiggy", "uber eats", "dominos", "pizza", "mcdonald",
        "starbucks", "cafe", "restaurant", "food", "burger", "kfc",
        "subway", "dunkin", "bakery", "biryani", "dine", "eat",
    ],
    "Transport": [
        "uber", "ola", "lyft", "rapido", "metro", "railway", "irctc",
        "petrol", "fuel", "diesel", "parking", "toll", "cab", "taxi",
        "bike", "ride",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "walmart",
        "target", "zara", "h&m", "shopping", "mart", "store", "retail",
        "ebay", "aliexpress",
    ],
    "Subscription": [
        "netflix", "spotify", "hotstar", "prime video", "disney",
        "youtube", "apple music", "hulu", "hbo", "subscription",
        "membership", "annual plan",
    ],
    "Housing": [
        "rent", "lease", "mortgage", "maintenance", "society",
        "housing", "apartment", "property",
    ],
    "Entertainment": [
        "movie", "cinema", "pvr", "inox", "concert", "event",
        "ticket", "game", "gaming", "playstation", "xbox", "steam",
    ],
    "Bills": [
        "electricity", "water", "gas bill", "internet", "broadband",
        "wifi", "phone", "mobile", "recharge", "postpaid", "prepaid",
        "insurance", "emi",
    ],
    "Transfer": [
        "neft", "imps", "upi", "transfer", "sent to", "received from",
    ],
}


def categorize(description: str) -> str:
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return category
    return "Others"


def categorize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["category"] = df["description"].apply(categorize)
    
    # LLM Fallback for "Others" if API key is present
    if client:
        others_mask = df["category"] == "Others"
        unknown_desc = df.loc[others_mask, "description"].unique().tolist()
        
        if unknown_desc:
            # We use Llama-3.1-8b-instant for fast, low-latency categorization
            model_name = "llama-3.1-8b-instant" if os.getenv("GROQ_API_KEY") else "gpt-4o-mini"
            # Categorize only unique unknown descriptions to save tokens
            prompt = f"Categorize these merchants: {json.dumps(unknown_desc[:20])}. Options: {', '.join(CATEGORY_KEYWORDS.keys())}. Return RAW JSON mapping: {{\"mapping\": {{\"merchant\": \"category\"}}}}"
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": "You are a financial categorizer. Output ONLY a raw JSON mapping."},
                              {"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" }
                )
                mapping = json.loads(resp.choices[0].message.content).get("mapping", {})
                df.loc[others_mask, "category"] = df.loc[others_mask, "description"].map(lambda x: mapping.get(x, "Others"))
            except:
                pass
                
    return df
