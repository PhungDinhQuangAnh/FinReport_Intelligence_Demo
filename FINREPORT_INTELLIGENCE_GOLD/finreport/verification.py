"""Gold verification layer: recompute core formulas and validate output evidence before explanation."""
from __future__ import annotations
import math
import pandas as pd
from .config import KEY

FORMULA_CHECKS = {
    "gross_margin_pct": lambda r: r.gross_profit_vnd_mn / r.revenue_vnd_mn * 100 if r.revenue_vnd_mn else float("nan"),
    "current_ratio_x": lambda r: r.total_current_assets_vnd_mn / r.total_current_liabilities_vnd_mn if r.total_current_liabilities_vnd_mn else float("nan"),
    "debt_to_assets_pct": lambda r: (r.short_term_debt_vnd_mn + r.long_term_debt_vnd_mn) / r.total_assets_vnd_mn * 100 if r.total_assets_vnd_mn else float("nan"),
    "cfo_to_net_income_x": lambda r: r.cfo_vnd_mn / r.net_income_vnd_mn if r.net_income_vnd_mn else float("nan"),
    "free_cash_flow_vnd_mn": lambda r: r.cfo_vnd_mn + r.capital_expenditure_vnd_mn,
    "interest_coverage_x": lambda r: r.operating_profit_vnd_mn / r.interest_expense_vnd_mn if r.interest_expense_vnd_mn else float("nan"),
}


def verify_calculations(df: pd.DataFrame, atol: float = 1e-6) -> pd.DataFrame:
    rows = []
    for r in df.itertuples(index=False):
        failed = []
        checked = 0
        for metric, fn in FORMULA_CHECKS.items():
            actual = getattr(r, metric)
            expected = fn(r)
            if pd.isna(actual) and pd.isna(expected):
                checked += 1
                continue
            if pd.isna(actual) != pd.isna(expected):
                failed.append(metric)
            elif not math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=atol):
                failed.append(metric)
            checked += 1
        status = "PASS" if not failed else "FAIL"
        rows.append({"company_id": r.company_id, "fiscal_year": int(r.fiscal_year),
                     "verification_status": status, "verification_checks": checked,
                     "verification_failed": ";".join(failed),
                     "verification_score": round((checked - len(failed)) / checked, 4) if checked else 0.0})
    return pd.DataFrame(rows)


def verify_alert_evidence(alerts_detail: pd.DataFrame) -> pd.DataFrame:
    if alerts_detail.empty:
        return pd.DataFrame(columns=KEY + ["evidence_complete", "evidence_issue_count"])
    d = alerts_detail.copy()
    d["_ok"] = d["evidence_fields"].astype(str).str.contains(".csv:", regex=False) & d["evidence_metrics"].astype(str).ne("")
    out = d.groupby(KEY, as_index=False).agg(evidence_complete=("_ok", "all"), evidence_issue_count=("_ok", lambda s: int((~s).sum())))
    return out
