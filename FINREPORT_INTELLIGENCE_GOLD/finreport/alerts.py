"""Gold multi-signal alert engine.

Transparent rule signals are combined with same-year peer context and a robust anomaly
score. Public scenario labels are NEVER read here. Escalation uses financial conditions,
not company IDs or years.
"""
from __future__ import annotations
import math
import time
import pandas as pd
from .config import MODEL_NAME, GOLD_HIGH_THRESHOLD, GOLD_CRITICAL_THRESHOLD

# Fourteen binary rules. Each activated rule contributes EXACTLY 1/14.
RULES = (
    "CFO_NEGATIVE",
    "PROFIT_CASH_DIVERGENCE",
    "CFO_WEAKNESS",
    "LIQUIDITY_PRESSURE",
    "WORKING_CAPITAL_PRESSURE",
    "RECEIVABLES_RISK",
    "INVENTORY_RISK",
    "LEVERAGE_RISK",
    "DEBT_EXPANSION",
    "INTEREST_BURDEN",
    "GROSS_MARGIN_DECLINE",
    "PROFITABILITY_PRESSURE",
    "NEGATIVE_FCF",
    "DISTRESS_LOSS",
)
RULE_COUNT = len(RULES)
RULE_CONTRIBUTION = 1.0 / RULE_COUNT

FIELD_SOURCE = {
    "revenue_vnd_mn": "income_statement.csv", "cost_of_goods_sold_vnd_mn": "income_statement.csv",
    "gross_profit_vnd_mn": "income_statement.csv", "net_income_vnd_mn": "income_statement.csv",
    "operating_profit_vnd_mn": "income_statement.csv", "interest_expense_vnd_mn": "income_statement.csv",
    "net_cash_from_operating_activities_vnd_mn": "cashflow.csv", "capital_expenditure_vnd_mn": "cashflow.csv",
    "ending_cash_vnd_mn": "cashflow.csv", "accounts_receivable_vnd_mn": "balance_sheet.csv",
    "inventory_vnd_mn": "balance_sheet.csv", "accounts_payable_vnd_mn": "balance_sheet.csv",
    "total_current_assets_vnd_mn": "balance_sheet.csv", "total_current_liabilities_vnd_mn": "balance_sheet.csv",
    "cash_and_cash_equivalents_vnd_mn": "balance_sheet.csv", "short_term_debt_vnd_mn": "balance_sheet.csv",
    "long_term_debt_vnd_mn": "balance_sheet.csv", "total_assets_vnd_mn": "balance_sheet.csv",
    "average_customer_credit_terms_days": "financial_notes.csv", "inventory_policy_days_target": "financial_notes.csv",
    "average_borrowing_rate_pct": "financial_notes.csv", "debt_maturing_within_12m_pct": "financial_notes.csv",
    "capex_intensity_pct": "financial_notes.csv",
}

PRIOR_FIELDS = {
    "RECEIVABLES_RISK": {"accounts_receivable_vnd_mn", "revenue_vnd_mn"},
    "INVENTORY_RISK": {"inventory_vnd_mn", "revenue_vnd_mn"},
    "GROSS_MARGIN_DECLINE": {"gross_profit_vnd_mn", "revenue_vnd_mn"},
    "DEBT_EXPANSION": {"short_term_debt_vnd_mn", "long_term_debt_vnd_mn"},
}


def _num(row, key):
    v = row.get(key, float("nan"))
    try:
        v = float(v)
    except (ValueError, TypeError):
        return None
    return v if math.isfinite(v) else None


def _fmt(v):
    return "NA" if v is None else f"{v:,.2f}"


# Eight proposed RECOVERING checks. The source project did not define these
# checks; they are explicit, editable MVP assumptions, NOT official BTC criteria.
# A missing (NA) metric always makes its condition False (e.g. first-year growth).
RECOVERY_CRITERIA = (
    ("revenue_non_decreasing", "Doanh thu không giảm YoY", "revenue_growth_pct", ">=", 0.0),
    ("gross_margin_stable", "Gross Margin không giảm YoY", "gross_margin_change_pp", ">=", 0.0),
    ("net_margin_healthy", "Net Margin >= 8%", "net_margin_pct", ">=", 8.0),
    ("positive_cfo", "CFO dương", "cfo_vnd_mn", ">", 0.0),
    ("earnings_cash_conversion", "CFO/Net Income >= 0.8", "cfo_to_net_income_x", ">=", 0.8),
    ("sufficient_liquidity", "Current Ratio >= 1.5", "current_ratio_x", ">=", 1.5),
    ("interest_coverage", "Interest Coverage >= 4", "interest_coverage_x", ">=", 4.0),
    ("debt_not_expanding", "Tổng nợ vay không tăng YoY", "total_debt_growth_pct", "<=", 0.0),
)
assert len(RECOVERY_CRITERIA) == 8


def recovery_status(row) -> tuple[bool, dict[str, bool]]:
    """Eight explicit, all-required checks; NA never silently counts as passing."""
    checks = {}
    for name, _, field, operator, threshold in RECOVERY_CRITERIA:
        value = _num(row, field)
        if value is None:
            checks[name] = False
        elif operator == ">=":
            checks[name] = value >= threshold
        elif operator == ">":
            checks[name] = value > threshold
        elif operator == "<=":
            checks[name] = value <= threshold
        else:
            raise ValueError(f"Unsupported recovery comparison: {operator}")
    return all(checks.values()), checks


def _escalation(row, base_score: float, rule_count: int = 0) -> tuple[str, str, str]:
    """Severity decision order: CRITICAL > LOW/RECOVERING > HIGH (GM) > HIGH > MEDIUM > LOW."""
    net = _num(row, "net_margin_pct")
    cfo = _num(row, "cfo_vnd_mn")
    cov = _num(row, "interest_coverage_x")
    debt = _num(row, "debt_to_assets_pct")
    debt_growth = _num(row, "total_debt_growth_pct")
    dso = _num(row, "dso_days")
    inv = _num(row, "inventory_days")
    gm_change = _num(row, "gross_margin_change_pp")
    anomaly = _num(row, "anomaly_score")
    anomaly = 0.0 if anomaly is None else anomaly

    # PRIORITY 01: CRITICAL by score OR any of three financial crisis combinations.
    critical_reason = ""
    if base_score >= GOLD_CRITICAL_THRESHOLD:
        critical_reason = f"Risk Score >= {GOLD_CRITICAL_THRESHOLD:.2f}."
    elif net is not None and net < 0 and cov is not None and cov < 1 and cfo is not None and cfo < 0:
        critical_reason = "Lỗ/biên ròng âm đồng thời CFO âm và Interest Coverage < 1."
    elif debt_growth is not None and debt_growth > 25 and debt is not None and debt > 30 and cov is not None and cov < 4:
        critical_reason = "Nợ tăng nhanh, đòn bẩy cao và khả năng trả lãi suy yếu đồng thời."
    elif cfo is not None and cfo < 0 and cov is not None and cov < 2 and ((dso or 0) > 90 or (inv or 0) > 120):
        critical_reason = "CFO âm đi cùng áp lực trả lãi và vốn lưu động rất cao."
    if critical_reason:
        return "CRITICAL", "HIGH_RISK", critical_reason

    # PRIORITY 02: all 8 independent recovery conditions, except CRITICAL above.
    recovering, _ = recovery_status(row)
    if recovering:
        return "LOW", "RECOVERING", "Đạt cả 8/8 điều kiện phục hồi (quy ước MVP)."

    # PRIORITY 03: special severe gross-margin deterioration.
    if gm_change is not None and gm_change <= -3.0 and net is not None and net < 8.0:
        return "HIGH", "HIGH_RISK", "Gross Margin giảm >= 3 điểm % và Net Margin < 8%."

    # PRIORITY 04: normal HIGH score/anomaly thresholds.
    if base_score >= GOLD_HIGH_THRESHOLD or anomaly >= 0.50:
        return "HIGH", "HIGH_RISK" if base_score >= 0.45 else "WATCH", "Risk Score >= 0.25 hoặc Anomaly Score >= 0.50."

    # PRIORITY 05: any rule or significant anomaly -> MEDIUM.
    if rule_count > 0 or anomaly >= 0.28:
        return "MEDIUM", "WATCH", "Có rule kích hoạt hoặc Anomaly Score >= 0.28."
    return "LOW", "HEALTHY", "Không kích hoạt điều kiện nào ở trên."


def _primary_scenario(codes: list[str], row) -> str:
    s = set(codes)
    if "DISTRESS_LOSS" in s and "CFO_NEGATIVE" in s:
        return "DISTRESS_BASELINE"
    if "DEBT_EXPANSION" in s and ("INTEREST_BURDEN" in s or "LEVERAGE_RISK" in s):
        return "DEBT_EXPANSION"
    if "CFO_NEGATIVE" in s and ("RECEIVABLES_RISK" in s or "INVENTORY_RISK" in s):
        return "LIQUIDITY_STRESS"
    if "PROFIT_CASH_DIVERGENCE" in s:
        return "PROFIT_CASH_DIVERGENCE"
    if "RECEIVABLES_RISK" in s:
        return "RECEIVABLES_RISK"
    if "INVENTORY_RISK" in s:
        return "INVENTORY_BUILDUP"
    if "GROSS_MARGIN_DECLINE" in s or "PROFITABILITY_PRESSURE" in s:
        return "MARGIN_DETERIORATION"
    if "CFO_WEAKNESS" in s and (_num(row, "revenue_growth_pct") or 0) > 5:
        return "REVENUE_GROWTH_WEAK_CASH"
    if not codes:
        # Positive/recovery interpretations are descriptive, not risk alerts.
        gmchg = _num(row, "gross_margin_change_pp")
        debtg = _num(row, "total_debt_growth_pct")
        if gmchg is not None and gmchg > 2 and debtg is not None and debtg < 0:
            return "OPERATIONAL_IMPROVEMENT"
        if (_num(row, "gross_margin_pct") or 0) >= 35 and (_num(row, "cfo_margin_pct") or 0) >= 15 and (_num(row, "debt_to_assets_pct") or 100) < 15:
            return "STRONG_PERFORMANCE"
        return "NORMAL_STABLE"
    return codes[0]


def detect_alerts(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    allrows, details = [], []
    history = {(str(r.company_id), int(r.fiscal_year)): r for _, r in d.iterrows()}
    for _, row in d.iterrows():
        t0 = time.perf_counter()
        cid, year = str(row.company_id), int(row.fiscal_year)
        flags = []

        def add(code, explanation, source_fields, metrics):
            if any(x["rule_id"] == code for x in flags):
                return
            proof = []
            for field in source_fields:
                if field not in FIELD_SOURCE:
                    continue
                v = _num(row, field)
                proof.append(f"{FIELD_SOURCE[field]}:{field}:{cid}:{year}={_fmt(v)}")
                if field in PRIOR_FIELDS.get(code, set()) and (cid, year - 1) in history:
                    pv = _num(history[(cid, year - 1)], field)
                    proof.append(f"{FIELD_SOURCE[field]}:{field}:{cid}:{year-1}={_fmt(pv)}")
            flags.append({"company_id": cid, "fiscal_year": year, "rule_id": code,
                          "severity_weight": RULE_CONTRIBUTION, "rule_contribution": RULE_CONTRIBUTION, "reason": explanation,
                          "evidence_fields": ";".join(proof),
                          "evidence_metrics": ";".join(f"{k}={_fmt(_num(row,k))}" for k in metrics)})

        cfo = _num(row, "cfo_vnd_mn"); ni = _num(row, "net_income_vnd_mn")
        cfo_ratio = _num(row, "cfo_to_net_income_x"); cfo_margin = _num(row, "cfo_margin_pct")
        cur = _num(row, "current_ratio_x"); quick = _num(row, "quick_ratio_x")
        dso = _num(row, "dso_days"); inv = _num(row, "inventory_days")
        revgr = _num(row, "revenue_growth_pct"); argr = _num(row, "accounts_receivable_growth_pct"); invgr = _num(row, "inventory_growth_pct")
        leverage = _num(row, "debt_to_assets_pct"); coverage = _num(row, "interest_coverage_x")
        mgchg = _num(row, "gross_margin_change_pp"); netmargin = _num(row, "net_margin_pct"); opmargin = _num(row, "operating_margin_pct")
        debtgr = _num(row, "total_debt_growth_pct"); fcf = _num(row, "free_cash_flow_vnd_mn")
        credit = _num(row, "average_customer_credit_terms_days"); inv_target = _num(row, "inventory_policy_days_target")
        borrow_rate = _num(row, "average_borrowing_rate_pct"); debt_due = _num(row, "debt_maturing_within_12m_pct")
        p_dso = _num(row, "peer_percentile__dso_days"); p_inv = _num(row, "peer_percentile__inventory_days")
        p_lev = _num(row, "peer_percentile__debt_to_assets_pct"); p_opm = _num(row, "peer_percentile__operating_margin_pct")
        p_cfo = _num(row, "peer_percentile__cfo_margin_pct")

        if cfo is not None and cfo < 0:
            add("CFO_NEGATIVE", f"CFO âm ({_fmt(cfo)} triệu VND).", ["net_cash_from_operating_activities_vnd_mn"], ["cfo_vnd_mn", "cfo_margin_pct"])
        if ni is not None and ni > 0 and cfo_ratio is not None and cfo_ratio < 0.65:
            add("PROFIT_CASH_DIVERGENCE", f"Lợi nhuận dương nhưng CFO/Net Income chỉ {_fmt(cfo_ratio)} lần.", ["net_income_vnd_mn", "net_cash_from_operating_activities_vnd_mn"], ["cfo_to_net_income_x"])
        if (cfo_ratio is not None and ni is not None and ni > 0 and 0 <= cfo_ratio < 0.80) or (p_cfo is not None and p_cfo <= 20):
            add("CFO_WEAKNESS", "Khả năng chuyển lợi nhuận thành tiền yếu hoặc CFO Margin thuộc nhóm thấp của ngành.", ["net_income_vnd_mn", "net_cash_from_operating_activities_vnd_mn"], ["cfo_to_net_income_x", "cfo_margin_pct", "peer_percentile__cfo_margin_pct"])
        if (cur is not None and cur < 1.5) or (quick is not None and quick < 1.15) or (debt_due is not None and debt_due >= 45 and cfo_margin is not None and cfo_margin < 5):
            add("LIQUIDITY_PRESSURE", "Thanh khoản ngắn hạn/dòng tiền chưa tạo đệm an toàn so với nghĩa vụ đáo hạn.", ["total_current_assets_vnd_mn", "total_current_liabilities_vnd_mn", "debt_maturing_within_12m_pct", "net_cash_from_operating_activities_vnd_mn"], ["current_ratio_x", "quick_ratio_x", "cfo_margin_pct"])
        if cfo_ratio is not None and cfo_ratio < 0.7 and ((dso or 0) > 60 or (inv or 0) > 90):
            add("WORKING_CAPITAL_PRESSURE", "CFO conversion thấp đồng thời vốn bị giữ ở phải thu/tồn kho.", ["accounts_receivable_vnd_mn", "inventory_vnd_mn", "net_cash_from_operating_activities_vnd_mn"], ["cfo_to_net_income_x", "dso_days", "inventory_days"])
        if dso is not None and ((credit is not None and dso > credit + 12) or (argr is not None and revgr is not None and argr > revgr + 10 and dso > 60) or (p_dso is not None and p_dso >= 85)):
            add("RECEIVABLES_RISK", f"DSO {_fmt(dso)} ngày / phải thu tăng nhanh hơn doanh thu hoặc thuộc nhóm cao trong peer.", ["accounts_receivable_vnd_mn", "revenue_vnd_mn", "average_customer_credit_terms_days"], ["dso_days", "accounts_receivable_growth_pct", "revenue_growth_pct", "peer_percentile__dso_days"])
        if inv is not None and ((inv_target is not None and inv > inv_target + 12) or (invgr is not None and revgr is not None and invgr > revgr + 10 and inv > 85) or (p_inv is not None and p_inv >= 85)):
            add("INVENTORY_RISK", f"Inventory Days {_fmt(inv)} ngày / tồn kho tăng nhanh hoặc thuộc nhóm cao trong peer.", ["inventory_vnd_mn", "revenue_vnd_mn", "inventory_policy_days_target"], ["inventory_days", "inventory_growth_pct", "revenue_growth_pct", "peer_percentile__inventory_days"])
        if leverage is not None and (leverage > 35 or (p_lev is not None and p_lev >= 85)):
            add("LEVERAGE_RISK", f"Debt/Assets {_fmt(leverage)}% ở mức cao tuyệt đối hoặc tương đối.", ["short_term_debt_vnd_mn", "long_term_debt_vnd_mn", "total_assets_vnd_mn"], ["debt_to_assets_pct", "peer_percentile__debt_to_assets_pct"])
        if debtgr is not None and debtgr > 20 and ((leverage or 0) > 25 or (borrow_rate or 0) >= 8):
            add("DEBT_EXPANSION", f"Nợ vay tăng {_fmt(debtgr)}% trong khi đòn bẩy/chi phí vay đáng chú ý.", ["short_term_debt_vnd_mn", "long_term_debt_vnd_mn", "average_borrowing_rate_pct"], ["total_debt_growth_pct", "debt_to_assets_pct"])
        if coverage is not None and (coverage < 4 or ((borrow_rate or 0) >= 10 and coverage < 6)):
            add("INTEREST_BURDEN", f"Interest Coverage {_fmt(coverage)} lần và/hoặc lãi suất vay cao.", ["operating_profit_vnd_mn", "interest_expense_vnd_mn", "average_borrowing_rate_pct"], ["interest_coverage_x"])
        if mgchg is not None and mgchg <= -2.5:
            add("GROSS_MARGIN_DECLINE", f"Gross Margin giảm {_fmt(abs(mgchg))} điểm % so với năm trước.", ["gross_profit_vnd_mn", "revenue_vnd_mn"], ["gross_margin_change_pp"])
        if (netmargin is not None and netmargin < 5) or (p_opm is not None and p_opm <= 15 and (opmargin or 0) < 10):
            add("PROFITABILITY_PRESSURE", "Biên lợi nhuận thấp tuyệt đối hoặc thuộc nhóm yếu của peer.", ["operating_profit_vnd_mn", "net_income_vnd_mn", "revenue_vnd_mn"], ["operating_margin_pct", "net_margin_pct", "peer_percentile__operating_margin_pct"])
        if fcf is not None and fcf < 0:
            add("NEGATIVE_FCF", f"Free Cash Flow âm ({_fmt(fcf)} triệu VND).", ["net_cash_from_operating_activities_vnd_mn", "capital_expenditure_vnd_mn"], ["free_cash_flow_vnd_mn"])
        if netmargin is not None and netmargin < 0:
            add("DISTRESS_LOSS", f"Net Margin âm ({_fmt(netmargin)}%).", ["net_income_vnd_mn", "revenue_vnd_mn"], ["net_margin_pct"])

        rule_score = len(flags) / RULE_COUNT
        anomaly = _num(row, "anomaly_score") or 0.0
        # Anomaly is supporting evidence, not the main decision-maker.
        raw_risk_score = min(1.0, 0.88 * rule_score + 0.12 * anomaly)
        risk_score = round(raw_risk_score, 4)
        # Unrounded score governs threshold decisions (avoids 0.67995 -> 0.6800 issue).
        severity, health, escalation_reason = _escalation(row, raw_risk_score, len(flags))
        recovering, recovery_checks = recovery_status(row)
        codes = [x["rule_id"] for x in flags]
        scenario = _primary_scenario(codes, row)
        independent = len(codes)
        verification_hint = 1.0  # finalized by verification module in pipeline
        confidence = min(0.98, 0.58 + 0.06 * min(independent, 5) + 0.10 * min(anomaly, 1.0))
        if not flags:
            confidence = 0.72
        allrows.append({
            "company_id": cid, "fiscal_year": year, "risk_score": risk_score,
            "rule_risk_score": round(rule_score, 4), "activated_rule_count": len(flags),
            "total_rule_count": RULE_COUNT, "anomaly_score": round(anomaly, 4),
            "recovery_conditions_met": sum(recovery_checks.values()),
            "recovery_conditions_total": len(recovery_checks),
            "recovery_eligible": recovering,
            "recovery_condition_checks": ";".join(f"{name}={int(passed)}" for name, passed in recovery_checks.items()),
            "predicted_primary_scenario": scenario, "predicted_severity": severity,
            "predicted_overall_health": health, "alert_tags": ";".join(codes),
            "alert_reason": " | ".join(x["reason"] for x in flags) if flags else "Chưa phát hiện tín hiệu bất lợi vượt ngưỡng theo bộ quy tắc Gold.",
            "escalation_reason": escalation_reason,
            "evidence_fields": " | ".join(x["evidence_fields"] for x in flags),
            "confidence": round(confidence, 3), "model_name": MODEL_NAME,
            "processing_time_ms": round((time.perf_counter() - t0) * 1000, 3),
        })
        details.extend(flags)

    summary = pd.DataFrame(allrows)
    summary["priority_rank"] = summary.groupby("fiscal_year")["risk_score"].rank(ascending=False, method="first").astype(int)
    detail_cols = ["company_id", "fiscal_year", "rule_id", "severity_weight", "rule_contribution", "reason", "evidence_fields", "evidence_metrics"]
    return summary, pd.DataFrame(details, columns=detail_cols)
