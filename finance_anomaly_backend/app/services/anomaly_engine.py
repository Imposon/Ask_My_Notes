from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.services.feature_engineering import get_feature_matrix
from app.utils.helpers import ML_MODELS_DIR, ensure_ml_models_dir


def detect_anomalies(
    df: pd.DataFrame,
    baseline: dict[str, Any],
    user_id: str,
    threshold: float = 70.0,
) -> pd.DataFrame:
    df = df.copy()

    # Pre-calculate category statistics to avoid repetitive dict lookups in apply
    category_stats = baseline.get("category_stats", {})
    weekly_avg = baseline.get("weekly_avg_spend", 0)
    weekly_std = baseline.get("weekly_std_spend", 0)
    known_merchants = set(baseline.get("merchant_stats", {}).keys())
    
    # Use vectorized operations where possible
    # 1. Amount Z-Score
    def get_zscore(row):
        stats = category_stats.get(row.get("category", ""), {})
        mean, std = stats.get("mean_amount", 0), stats.get("std_amount", 0)
        if std == 0: return 0.0
        return min(abs(row["abs_amount"] - mean) / (std * 4.0), 1.0)
    
    df["stat_amount_zscore"] = df.apply(get_zscore, axis=1)

    # 2. Weekly Deviation
    if weekly_avg > 0:
        std_val = weekly_std if weekly_std > 0 else weekly_avg
        df["stat_weekly_dev"] = ((df["rolling_7_day_spend"] - weekly_avg).abs() / (std_val * 4.0)).clip(0, 1)
    else:
        df["stat_weekly_dev"] = 0.0

    # 3. New Merchant Score
    df["stat_new_merchant"] = df["merchant"].apply(
        lambda m: 1.0 if m and m != "Unknown" and m not in known_merchants else 0.0
    )

    # 4. Time Deviation (Vectorized)
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


def _amount_zscore(row: pd.Series, baseline: dict) -> float:
    cat_stats = baseline.get("category_stats", {}).get(row.get("category", ""), {})
    mean = cat_stats.get("mean_amount", 0)
    std = cat_stats.get("std_amount", 0)
    if std == 0:
        return 0.0
    z = abs(row["abs_amount"] - mean) / std
    return float(min(z / 4.0, 1.0))


def _weekly_deviation(row: pd.Series, df: pd.DataFrame, baseline: dict) -> float:
    avg = baseline.get("weekly_avg_spend", 0)
    std = baseline.get("weekly_std_spend", 0)
    if avg == 0:
        return 0.0

    current_week = row.get("rolling_7_day_spend", 0)
    if std == 0:
        deviation = abs(current_week - avg) / max(avg, 1)
    else:
        deviation = abs(current_week - avg) / std

    return float(min(deviation / 4.0, 1.0))


def _new_merchant_score(row: pd.Series, baseline: dict) -> float:
    merchant = row.get("merchant", "")
    merchants = baseline.get("merchant_stats", {})
    if not merchant or merchant == "Unknown":
        # Cannot determine merchant — do not penalise; it is common for many
        # transactions where extraction fails.
        return 0.0
    return 0.0 if merchant in merchants else 1.0


def _time_deviation(row: pd.Series, df: pd.DataFrame) -> float:
    if df.empty or "hour_of_day" not in df.columns:
        return 0.0
    median_hour = df["hour_of_day"].median()
    hour = row.get("hour_of_day", 12)
    diff = abs(hour - median_hour)
    circular_diff = min(diff, 24 - diff)
    return float(min(circular_diff / 12.0, 1.0))


def _train_isolation_forest(
    feature_matrix: np.ndarray,
    user_id: str,
) -> np.ndarray:
    ensure_ml_models_dir()

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


def load_model(user_id: str) -> Optional[IsolationForest]:
    model_path = ML_MODELS_DIR / f"{user_id}_model.pkl"
    if model_path.exists():
        return joblib.load(model_path)
    return None
