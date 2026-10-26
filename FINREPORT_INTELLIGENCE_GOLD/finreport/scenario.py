"""What-if scenario engine for a single company-year.

Assumptions are percentage changes applied to selected raw fields. Operating profit,
PBT, tax and net income are recomputed consistently using fixed selling/admin/D&A and
original effective tax rate where applicable.
"""
from __future__ import annotations
import copy
import pandas as pd

DEFAULT_ASSUMPTIONS = {
    "revenue_pct": 0.0,
    "cogs_pct": 0.0,
    "accounts_receivable_pct": 0.0,
    "inventory_pct": 0.0,
    "short_term_debt_pct": 0.0,
    "long_term_debt_pct": 0.0,
    "interest_expense_pct": 0.0,
    "cfo_pct": 0.0,
}


def _pct(v, pct):
    return float(v) * (1 + float(pct) / 100)


def simulate_raw_row(base: pd.Series, assumptions: dict | None = None) -> pd.Series:
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    r = base.copy()
    r["revenue_vnd_mn"] = _pct(r["revenue_vnd_mn"], a["revenue_pct"])
    r["cost_of_goods_sold_vnd_mn"] = _pct(r["cost_of_goods_sold_vnd_mn"], a["cogs_pct"])
    r["gross_profit_vnd_mn"] = r["revenue_vnd_mn"] - r["cost_of_goods_sold_vnd_mn"]
    r["operating_profit_vnd_mn"] = r["gross_profit_vnd_mn"] - r["selling_expense_vnd_mn"] - r["administrative_expense_vnd_mn"] - r["depreciation_amortization_vnd_mn"]
    r["accounts_receivable_vnd_mn"] = _pct(r["accounts_receivable_vnd_mn"], a["accounts_receivable_pct"])
    r["inventory_vnd_mn"] = _pct(r["inventory_vnd_mn"], a["inventory_pct"])
    r["short_term_debt_vnd_mn"] = _pct(r["short_term_debt_vnd_mn"], a["short_term_debt_pct"])
    r["long_term_debt_vnd_mn"] = _pct(r["long_term_debt_vnd_mn"], a["long_term_debt_pct"])
    r["interest_expense_vnd_mn"] = _pct(r["interest_expense_vnd_mn"], a["interest_expense_pct"])
    r["net_cash_from_operating_activities_vnd_mn"] = _pct(r["net_cash_from_operating_activities_vnd_mn"], a["cfo_pct"])
    r["profit_before_tax_vnd_mn"] = r["operating_profit_vnd_mn"] + r["finance_income_vnd_mn"] - r["interest_expense_vnd_mn"] + r["other_income_vnd_mn"]
    old_pbt = float(base["profit_before_tax_vnd_mn"])
    old_tax = float(base["income_tax_expense_vnd_mn"])
    tax_rate = old_tax / old_pbt if old_pbt > 0 else 0.20
    r["income_tax_expense_vnd_mn"] = max(0.0, r["profit_before_tax_vnd_mn"] * tax_rate)
    r["net_income_vnd_mn"] = r["profit_before_tax_vnd_mn"] - r["income_tax_expense_vnd_mn"]
    return r


def scenario_metrics(base: pd.Series, assumptions: dict | None = None) -> dict:
    r = simulate_raw_row(base, assumptions)
    debt = r["short_term_debt_vnd_mn"] + r["long_term_debt_vnd_mn"]
    def div(a,b): return a/b if b not in [0, None] else float("nan")
    result = {
        "revenue_vnd_mn": r["revenue_vnd_mn"],
        "gross_margin_pct": div(r["gross_profit_vnd_mn"], r["revenue_vnd_mn"]) * 100,
        "operating_margin_pct": div(r["operating_profit_vnd_mn"], r["revenue_vnd_mn"]) * 100,
        "net_margin_pct": div(r["net_income_vnd_mn"], r["revenue_vnd_mn"]) * 100,
        "debt_to_assets_pct": div(debt, r["total_assets_vnd_mn"]) * 100,
        "interest_coverage_x": div(r["operating_profit_vnd_mn"], r["interest_expense_vnd_mn"]),
        "cfo_vnd_mn": r["net_cash_from_operating_activities_vnd_mn"],
        "cfo_to_net_income_x": div(r["net_cash_from_operating_activities_vnd_mn"], r["net_income_vnd_mn"]),
        "free_cash_flow_vnd_mn": r["net_cash_from_operating_activities_vnd_mn"] + r["capital_expenditure_vnd_mn"],
        "accounts_receivable_vnd_mn": r["accounts_receivable_vnd_mn"],
        "inventory_vnd_mn": r["inventory_vnd_mn"],
        "short_term_debt_vnd_mn": r["short_term_debt_vnd_mn"],
        "long_term_debt_vnd_mn": r["long_term_debt_vnd_mn"],
    }
    # Simplified 7-check simulation proxy, NOT the full 14-rule calculation.
    # Every recognized signal contributes equally 1/14 to match the scoring scale;
    # peer percentiles, YoY metrics and robust anomaly remain unchanged/unavailable.
    indicators = [
        result["cfo_vnd_mn"] < 0,
        pd.notna(result["cfo_to_net_income_x"]) and 0 <= result["cfo_to_net_income_x"] < 0.8,
        result["debt_to_assets_pct"] > 35,
        pd.notna(result["interest_coverage_x"]) and result["interest_coverage_x"] < 4,
        result["free_cash_flow_vnd_mn"] < 0,
        result["net_margin_pct"] < 5,
        result["gross_margin_pct"] < 25,
    ]
    from .alerts import RULE_COUNT
    result["scenario_risk_proxy"] = round(sum(bool(v) for v in indicators) / RULE_COUNT, 4)
    return result
