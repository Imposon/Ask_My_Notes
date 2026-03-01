from typing import Any

import pandas as pd

from app.schemas import AnomalyResult


def generate_explanations(
    df: pd.DataFrame,
    baseline: dict[str, Any],
) -> list[AnomalyResult]:
    flagged = df[df["is_anomaly"] == True]  # noqa: E712
    results: list[AnomalyResult] = []
    total_txns = len(df)

    for _, row in flagged.iterrows():
        reasons: list[str] = []

        _explain_amount(row, baseline, reasons)
        _explain_merchant(row, baseline, reasons)
        _explain_hour(row, reasons)
        _explain_weekly_spike(row, baseline, reasons)
        _explain_rare_category(row, total_txns, reasons)

        if not reasons:
            reasons.append("Unusual spending pattern detected")

        results.append(
            AnomalyResult(
                transaction_id=int(row.get("id", 0)),
                risk_score=round(float(row["risk_score"]), 1),
                explanations=reasons,
            )
        )

    return results


def _explain_amount(row: pd.Series, baseline: dict, reasons: list[str]) -> None:
    cat = row.get("category", "")
    cat_stats = baseline.get("category_stats", {}).get(cat, {})
    mean = cat_stats.get("mean_amount", 0)
    if mean > 0:
        ratio = row["abs_amount"] / mean
        if ratio >= 2.0:
            reasons.append(
                f"Amount is {ratio:.1f}x higher than your {cat} average"
            )


def _explain_merchant(row: pd.Series, baseline: dict, reasons: list[str]) -> None:
    merchant = row.get("merchant", "")
    merchants = baseline.get("merchant_stats", {})
    if merchant and merchant != "Unknown" and merchant not in merchants:
        reasons.append("First time spending at this merchant")


def _explain_hour(row: pd.Series, reasons: list[str]) -> None:
    hour = row.get("hour_of_day", 12)
    if hour < 6 or hour >= 22:
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        reasons.append(f"Spending at unusual hour ({display_hour} {period})")


def _explain_weekly_spike(row: pd.Series, baseline: dict, reasons: list[str]) -> None:
    avg = baseline.get("weekly_avg_spend", 0)
    std = baseline.get("weekly_std_spend", 0)
    current = row.get("rolling_7_day_spend", 0)
    if avg > 0 and current > avg + std:
        pct = ((current - avg) / avg) * 100
        if pct >= 30:
            reasons.append(f"Weekly spending increased by {pct:.0f}%")


def _explain_rare_category(
    row: pd.Series, total_txns: int, reasons: list[str]
) -> None:
    cat_freq = row.get("category_frequency", 0)
    if total_txns > 0:
        pct = (cat_freq / total_txns) * 100
        if pct < 5:
            reasons.append(
                f"Rare category — only {pct:.1f}% of your transactions"
            )
