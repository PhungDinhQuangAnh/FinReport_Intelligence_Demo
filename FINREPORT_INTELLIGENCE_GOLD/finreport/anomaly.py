"""Robust peer anomaly detection using same-year median and MAD.

No public labels are used. Scores are directional: only financially adverse deviations
contribute to risk. This module exists to support Silver/Gold multi-signal detection
while preserving explainability.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from .config import ANOMALY_Z_THRESHOLD

# +1: high value is adverse, -1: low value is adverse
RISK_DIRECTIONS = {
    "debt_to_assets_pct": 1,
    "dso_days": 1,
    "inventory_days": 1,
    "accounts_receivable_growth_pct": 1,
    "inventory_growth_pct": 1,
    "total_debt_growth_pct": 1,
    "gross_margin_pct": -1,
    "operating_margin_pct": -1,
    "net_margin_pct": -1,
    "current_ratio_x": -1,
    "quick_ratio_x": -1,
    "interest_coverage_x": -1,
    "cfo_margin_pct": -1,
    "cfo_to_net_income_x": -1,
}


def _robust_z(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce")
    if values.notna().sum() < 2:
        return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
    med = values.median()
    mad = (values - med).abs().median()
    if pd.isna(mad) or mad <= 1e-12:
        # fallback to standard deviation only when MAD collapses
        std = values.std(ddof=0)
        if pd.isna(std) or std <= 1e-12:
            return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
        return (values - med) / std
    return 0.67448975 * (values - med) / mad


def add_anomaly_scores(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    groups = d.groupby(["subindustry", "fiscal_year"], sort=False)
    risk_cols = []
    for metric, direction in RISK_DIRECTIONS.items():
        rz = groups[metric].transform(_robust_z)
        d[f"robust_z__{metric}"] = rz
        directional = (rz * direction).clip(lower=0)
        d[f"risk_anomaly__{metric}"] = directional
        risk_cols.append(f"risk_anomaly__{metric}")

    def summarize(row):
        items = []
        for metric, direction in RISK_DIRECTIONS.items():
            z = row.get(f"risk_anomaly__{metric}")
            if pd.notna(z) and float(z) >= ANOMALY_Z_THRESHOLD:
                items.append((metric, float(z)))
        items.sort(key=lambda x: x[1], reverse=True)
        return ";".join(f"{m}:{z:.2f}" for m, z in items)

    d["anomaly_tags"] = d.apply(summarize, axis=1)
    arr = d[risk_cols].fillna(0).to_numpy(dtype=float)
    # emphasize the strongest 3 adverse peer deviations; map to 0..1
    top3 = np.sort(arr, axis=1)[:, -3:]
    raw = top3.mean(axis=1)
    d["anomaly_score"] = 1 - np.exp(-raw / 2.0)
    d["anomaly_score"] = d["anomaly_score"].clip(0, 1).round(4)
    d["anomaly_count"] = d["anomaly_tags"].apply(lambda x: 0 if not x else len(str(x).split(";")))
    return d
