"""Map original fields and calculated metrics back to competition data files."""
from .alerts import FIELD_SOURCE

METRIC_INPUTS = {
    "revenue_growth_pct": ["revenue_vnd_mn"],
    "gross_margin_pct": ["gross_profit_vnd_mn", "revenue_vnd_mn"],
    "operating_margin_pct": ["operating_profit_vnd_mn", "revenue_vnd_mn"],
    "net_margin_pct": ["net_income_vnd_mn", "revenue_vnd_mn"],
    "current_ratio_x": ["total_current_assets_vnd_mn", "total_current_liabilities_vnd_mn"],
    "quick_ratio_x": ["cash_and_cash_equivalents_vnd_mn", "accounts_receivable_vnd_mn", "total_current_liabilities_vnd_mn"],
    "debt_to_assets_pct": ["short_term_debt_vnd_mn", "long_term_debt_vnd_mn", "total_assets_vnd_mn"],
    "debt_to_equity_x": ["short_term_debt_vnd_mn", "long_term_debt_vnd_mn", "total_equity_vnd_mn"],
    "roa_pct": ["net_income_vnd_mn", "total_assets_vnd_mn"],
    "roe_pct": ["net_income_vnd_mn", "total_equity_vnd_mn"],
    "cfo_margin_pct": ["net_cash_from_operating_activities_vnd_mn", "revenue_vnd_mn"],
    "cfo_to_net_income_x": ["net_cash_from_operating_activities_vnd_mn", "net_income_vnd_mn"],
    "free_cash_flow_vnd_mn": ["net_cash_from_operating_activities_vnd_mn", "capital_expenditure_vnd_mn"],
    "dso_days": ["accounts_receivable_vnd_mn", "revenue_vnd_mn"],
    "inventory_days": ["inventory_vnd_mn", "cost_of_goods_sold_vnd_mn"],
    "dpo_days": ["accounts_payable_vnd_mn", "cost_of_goods_sold_vnd_mn"],
    "interest_coverage_x": ["operating_profit_vnd_mn", "interest_expense_vnd_mn"],
    "working_capital_vnd_mn": ["total_current_assets_vnd_mn", "total_current_liabilities_vnd_mn"],
}
# Supplement base mapping for sources outside alert rule coverage.
FIELD_SOURCE.update({"cost_of_goods_sold_vnd_mn": "income_statement.csv", "accounts_payable_vnd_mn": "balance_sheet.csv",
    "ending_cash_vnd_mn": "cashflow.csv", "capex_intensity_pct": "financial_notes.csv",
    "debt_maturing_within_12m_pct": "financial_notes.csv"})


def evidence_for_metric(company: str, year: int, metric: str) -> str:
    sources = METRIC_INPUTS.get(metric, [metric] if metric in FIELD_SOURCE else [])
    yrs = [year - 1, year] if metric in {"revenue_growth_pct", "roa_pct", "roe_pct", "dso_days", "inventory_days", "dpo_days"} else [year]
    return ";".join(f"{FIELD_SOURCE[field]}:{company}:{y}:{field}" for y in yrs for field in sources)
