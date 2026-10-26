"""Industry-year peer medians and percentiles (cross-sectional, no future leakage)."""
import pandas as pd

BENCHMARK_METRICS = [
    "revenue_growth_pct", "gross_margin_pct", "operating_margin_pct", "net_margin_pct",
    "current_ratio_x", "quick_ratio_x", "debt_to_assets_pct", "debt_to_equity_x",
    "roa_pct", "roe_pct", "cfo_margin_pct", "cfo_to_net_income_x", "dso_days",
    "inventory_days", "interest_coverage_x", "free_cash_flow_vnd_mn",
]


def add_benchmarks(metrics: pd.DataFrame) -> pd.DataFrame:
    d = metrics.copy()
    groups = d.groupby(["subindustry", "fiscal_year"], sort=False)
    d["peer_size"] = groups["company_id"].transform("size")
    for col in BENCHMARK_METRICS:
        d[f"peer_median__{col}"] = groups[col].transform("median")
        d[f"peer_delta__{col}"] = d[col] - d[f"peer_median__{col}"]
        # Percentile means % of company-year observations at or below this value.
        d[f"peer_percentile__{col}"] = groups[col].rank(pct=True, method="average") * 100
    return d
