"""
Keyword-based transaction categoriser.

Easily extendable: just add keywords to CATEGORY_KEYWORDS.
"""

import pandas as pd


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
    return df
