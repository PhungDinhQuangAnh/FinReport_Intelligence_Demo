"""Transparent peer-relative health score and dimension scores."""

from __future__ import annotations
import numpy as np
import pandas as pd

DIMENSIONS = {
    "profitability": [
        ("peer_percentile__gross_margin_pct", 1),
        ("peer_percentile__operating_margin_pct", 1),
        ("peer_percentile__net_margin_pct", 1),
        ("peer_percentile__roa_pct", 1),
        ("peer_percentile__roe_pct", 1),
    ],
    "liquidity": [
        ("peer_percentile__current_ratio_x", 1),
        ("peer_percentile__quick_ratio_x", 1),
    ],
    "cash_quality": [
        ("peer_percentile__cfo_margin_pct", 1),
        ("peer_percentile__cfo_to_net_income_x", 1),
        ("peer_percentile__free_cash_flow_vnd_mn", 1),
    ],
    "leverage": [
        ("peer_percentile__debt_to_assets_pct", -1),
        ("peer_percentile__debt_to_equity_x", -1),
        ("peer_percentile__interest_coverage_x", 1),
    ],
    "working_capital": [
        ("peer_percentile__dso_days", -1),
        ("peer_percentile__inventory_days", -1),
    ],
}

WEIGHTS = {
    "profitability": 0.20,
    "liquidity": 0.20,
    "cash_quality": 0.20,
    "leverage": 0.20,
    "working_capital": 0.20,
}


def _dimension_score(row, specs):
    vals = []
    for col, direction in specs:
        v = row.get(col)
        if pd.isna(v):
            continue
        v = float(v)
        vals.append(v if direction > 0 else 100 - v)
    return float(np.mean(vals)) if vals else np.nan


def add_health_scores(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for name, specs in DIMENSIONS.items():
        d[f"health__{name}"] = d.apply(lambda r: _dimension_score(r, specs), axis=1)

    def overall(row):
        total = weight = 0.0
        for name, w in WEIGHTS.items():
            v = row.get(f"health__{name}")
            if pd.notna(v):
                total += float(v) * w
                weight += w
        return total / weight if weight else np.nan

    d["financial_health_score"] = d.apply(overall, axis=1).round(1)
    return d
