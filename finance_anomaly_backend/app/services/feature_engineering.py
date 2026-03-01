import numpy as np
import pandas as pd


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
