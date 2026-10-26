"""Financial metrics computed directly from statement fields, with prior-year rules."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .config import KEY


def divide(numerator, denominator):
    """Undefined denominators return NaN, never silently inf or zero."""
    return (numerator / denominator.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)


def calculate_metrics(data: pd.DataFrame) -> pd.DataFrame:
    d = data.sort_values(KEY).copy()
    key = d.groupby("company_id", sort=False)
    d["total_debt_vnd_mn"] = d.short_term_debt_vnd_mn + d.long_term_debt_vnd_mn
    prev = {}
    for col in ["revenue_vnd_mn", "total_assets_vnd_mn", "total_equity_vnd_mn", "accounts_receivable_vnd_mn", "inventory_vnd_mn", "accounts_payable_vnd_mn", "total_debt_vnd_mn", "gross_profit_vnd_mn", "gross_margin_pct"]:
        if col in d:
            prev[col] = key[col].shift(1)
    d["revenue_growth_pct"] = divide(d.revenue_vnd_mn - prev["revenue_vnd_mn"], prev["revenue_vnd_mn"]) * 100
    d["gross_margin_pct"] = divide(d.gross_profit_vnd_mn, d.revenue_vnd_mn) * 100
    d["operating_margin_pct"] = divide(d.operating_profit_vnd_mn, d.revenue_vnd_mn) * 100
    d["net_margin_pct"] = divide(d.net_income_vnd_mn, d.revenue_vnd_mn) * 100
    d["current_ratio_x"] = divide(d.total_current_assets_vnd_mn, d.total_current_liabilities_vnd_mn)
    d["quick_ratio_x"] = divide(d.cash_and_cash_equivalents_vnd_mn + d.accounts_receivable_vnd_mn, d.total_current_liabilities_vnd_mn)
    d["debt_to_assets_pct"] = divide(d.total_debt_vnd_mn, d.total_assets_vnd_mn) * 100
    d["debt_to_equity_x"] = divide(d.total_debt_vnd_mn, d.total_equity_vnd_mn)
    # All average-balance ratios need t-1. 2021 is NA, not 2020 imputed.
    d["roa_pct"] = divide(d.net_income_vnd_mn, (d.total_assets_vnd_mn + prev["total_assets_vnd_mn"]) / 2) * 100
    d["roe_pct"] = divide(d.net_income_vnd_mn, (d.total_equity_vnd_mn + prev["total_equity_vnd_mn"]) / 2) * 100
    d["cfo_vnd_mn"] = d.net_cash_from_operating_activities_vnd_mn
    d["cfo_margin_pct"] = divide(d.cfo_vnd_mn, d.revenue_vnd_mn) * 100
    d["cfo_to_net_income_x"] = divide(d.cfo_vnd_mn, d.net_income_vnd_mn)
    d["free_cash_flow_vnd_mn"] = d.cfo_vnd_mn + d.capital_expenditure_vnd_mn
    d["dso_days"] = divide((d.accounts_receivable_vnd_mn + prev["accounts_receivable_vnd_mn"]) / 2, d.revenue_vnd_mn) * 365
    d["inventory_days"] = divide((d.inventory_vnd_mn + prev["inventory_vnd_mn"]) / 2, d.cost_of_goods_sold_vnd_mn) * 365
    d["dpo_days"] = divide((d.accounts_payable_vnd_mn + prev["accounts_payable_vnd_mn"]) / 2, d.cost_of_goods_sold_vnd_mn) * 365
    d["interest_coverage_x"] = divide(d.operating_profit_vnd_mn, d.interest_expense_vnd_mn)
    d["working_capital_vnd_mn"] = d.total_current_assets_vnd_mn - d.total_current_liabilities_vnd_mn
    d["accounts_receivable_growth_pct"] = divide(d.accounts_receivable_vnd_mn - prev["accounts_receivable_vnd_mn"], prev["accounts_receivable_vnd_mn"]) * 100
    d["inventory_growth_pct"] = divide(d.inventory_vnd_mn - prev["inventory_vnd_mn"], prev["inventory_vnd_mn"]) * 100
    d["total_debt_growth_pct"] = divide(d.total_debt_vnd_mn - prev["total_debt_vnd_mn"], prev["total_debt_vnd_mn"]) * 100
    d["gross_margin_change_pp"] = d.gross_margin_pct - d.groupby("company_id")["gross_margin_pct"].shift(1)
    return d.reset_index(drop=True)


METRICS_SAMPLE_COLS = [
    "revenue_growth_pct", "gross_margin_pct", "operating_margin_pct", "net_margin_pct", "current_ratio_x", "quick_ratio_x",
    "total_debt_vnd_mn", "debt_to_assets_pct", "debt_to_equity_x", "roa_pct", "roe_pct", "cfo_vnd_mn", "cfo_margin_pct",
    "cfo_to_net_income_x", "free_cash_flow_vnd_mn", "dso_days", "inventory_days", "dpo_days", "interest_coverage_x",
    "accounts_receivable_growth_pct", "inventory_growth_pct", "total_debt_growth_pct", "working_capital_vnd_mn",
]
