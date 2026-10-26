"""Restricted numerical QA over questions_sample metadata; never reads answer_key to answer.

Not a free-form LLM: supports public question types through reusable calculations.
"""
from __future__ import annotations
import time
import math
import pandas as pd
from .config import SAMPLES, MODEL_NAME
from .alerts import FIELD_SOURCE


def _fmt(x):
    if isinstance(x, (bool,)):
        return "TRUE" if x else "FALSE"
    if isinstance(x, str):
        return x
    if pd.isna(x):
        return ""
    return f"{float(x):.6f}".rstrip("0").rstrip(".") if float(x) % 1 else str(int(x))


def _yearset(value):
    s = str(value)
    parts = [int(x) for x in __import__("re").findall(r"20\d{2}", s)]
    return sorted(set(parts))


def _get(df, company, year, metric):
    view = df.loc[(df.company_id == company) & (df.fiscal_year == year), metric]
    if len(view) != 1:
        raise KeyError(f"Không tìm thấy company-year: {company}, {year}")
    return view.iloc[0]


def _growth(curr, prev):
    return (curr / prev - 1) * 100 if pd.notna(prev) and prev != 0 else float("nan")


def _query(q, df):
    kind = str(q.question_type)
    prompt = str(q.question_text_vi).lower()
    company = q.target_company_id if pd.notna(q.target_company_id) else ""
    years = _yearset(q.target_fiscal_year)
    year = years[-1] if years else None
    fields = str(q.source_fields).split(";")
    snapshot = lambda col, y=year: _get(df, company, y, col)
    if kind == "DIRECT_VALUE":
        val = snapshot(fields[0]); return val, f"Đọc trực tiếp {fields[0]} của {company} năm {year}."
    if kind == "RATIO_CALCULATION":
        mapping = {
            "gross margin": "gross_margin_pct", "current ratio": "current_ratio_x", "quick ratio": "quick_ratio_x",
            "debt/assets": "debt_to_assets_pct", "debt/equity": "debt_to_equity_x",
            "cfo/net income": "cfo_to_net_income_x", "interest coverage": "interest_coverage_x",
        }
        for text, metric in mapping.items():
            if text in prompt:
                return snapshot(metric), f"Tính {metric} từ các trường: {', '.join(fields)}."
        raise ValueError("Chưa hỗ trợ tỷ số trong câu hỏi")
    if kind == "GROWTH_CALCULATION":
        metric = "total_debt_growth_pct" if "nợ vay" in prompt else "revenue_growth_pct"
        return snapshot(metric), f"{metric} = (giá trị {year}/giá trị {year-1} - 1) × 100."
    if kind == "CHANGE_CALCULATION":
        start = snapshot("gross_margin_pct", years[0]); end = snapshot("gross_margin_pct", years[-1])
        return start - end, f"Biên lợi nhuận gộp {years[0]} trừ biên lợi nhuận gộp {years[-1]} (điểm %)."
    if kind == "CASHFLOW_CALCULATION":
        return snapshot("free_cash_flow_vnd_mn"), "Free Cash Flow = CFO + CAPEX (CAPEX âm)."
    if kind == "WORKING_CAPITAL_METRIC":
        name = "dso_days" if "dso" in prompt else "inventory_days" if "inventory" in prompt else "dpo_days"
        return snapshot(name), f"{name} từ số dư bình quân {year-1}–{year} × 365 / mẫu số tương ứng."
    if kind == "LIQUIDITY_CALCULATION":
        return snapshot("working_capital_vnd_mn"), "Working Capital = Current Assets − Current Liabilities."
    if kind == "RANKING":
        metric = ("gross_margin_pct" if "gross margin" in prompt else
                  "debt_to_assets_pct" if "debt/assets" in prompt else
                  "current_ratio_x" if "current ratio" in prompt else
                  "dso_days" if "dso" in prompt else None)
        if not metric: raise ValueError("Không xác định được chỉ tiêu xếp hạng")
        peers = df.loc[df.fiscal_year == year, ["company_id", metric]].dropna().sort_values([metric, "company_id"], ascending=[False, True])
        n = 3 if "3 doanh nghiệp" in prompt else 1
        result = ";".join(peers.company_id.head(n))
        return result, f"Xếp giảm dần {metric} của toàn bộ doanh nghiệp năm {year}."
    if kind == "BOOLEAN_ANALYSIS":
        if "phải thu" in prompt:
            start, end = years[0], years[-1]
            ag = _growth(snapshot("accounts_receivable_vnd_mn", end), snapshot("accounts_receivable_vnd_mn", start))
            rg = _growth(snapshot("revenue_vnd_mn", end), snapshot("revenue_vnd_mn", start))
            return bool(ag > rg), f"Tăng trưởng phải thu {start}–{end}: {ag:.2f}%, doanh thu: {rg:.2f}%."
        inventory_g = snapshot("inventory_growth_pct")
        revenue_g = snapshot("revenue_growth_pct")
        return bool(inventory_g > revenue_g), f"Tăng tồn kho {inventory_g:.2f}% so với doanh thu {revenue_g:.2f}%."
    if kind == "TREND_ANALYSIS":
        if company:
            start, end = years[0], years[-1]
            revenue_start, revenue_end = (snapshot("revenue_vnd_mn", x) for x in [start, end])
            conv_start, conv_end = (snapshot("cfo_to_net_income_x", x) for x in [start, end])
            rec_start, rec_end = (snapshot("accounts_receivable_vnd_mn", x) for x in [start, end])
            signals = []
            if revenue_end > revenue_start: signals.append("REVENUE_UP")
            if pd.notna(conv_start) and pd.notna(conv_end) and conv_end < conv_start: signals.append("CFO_CONVERSION_WEAKENING")
            if rec_end > rec_start: signals.append("RECEIVABLES_UP")
            rec_growth = _growth(rec_end, rec_start)
            rev_growth = _growth(revenue_end, revenue_start)
            if pd.notna(rec_growth) and rec_growth > rev_growth: signals.append("WORKING_CAPITAL_PRESSURE")
            return ";".join(signals), f"So sánh doanh thu, CFO/NI và phải thu trong giai đoạn {start}–{end}."
        start, end = years[0], years[-1]
        left, right = (df.loc[df.fiscal_year == y, ["company_id", "gross_margin_pct"]].set_index("company_id") for y in [start, end])
        delta = (right.gross_margin_pct - left.gross_margin_pct).dropna()
        return delta.idxmin(), f"So sánh thay đổi Gross Margin {start}→{end} trên toàn bộ doanh nghiệp."
    if kind == "LIST_FILTER":
        subset = df.loc[(df.fiscal_year == year) & (df.cfo_vnd_mn < 0)].sort_values("company_id")
        return ";".join(subset.company_id), f"Lọc CFO < 0 trong năm {year}."
    if kind == "RECONCILIATION":
        first = snapshot("ending_cash_vnd_mn")
        second = snapshot("cash_and_cash_equivalents_vnd_mn")
        return bool(math.isclose(first, second, rel_tol=0, abs_tol=1e-6)), "So sánh Ending Cash (cashflow) với Cash (balance sheet)."
    raise ValueError(f"Loại Numerical QA chưa được hỗ trợ: {kind}")


def answer_questions(metrics, questions: pd.DataFrame | None = None) -> pd.DataFrame:
    if questions is None:
        questions = pd.read_csv(SAMPLES / "questions_sample.csv", encoding="utf-8-sig")
    output = []
    for q in questions.itertuples(index=False):
        t0 = time.perf_counter()
        try:
            answer, reason = _query(q, metrics)
            answer = _fmt(answer)
            confidence = 0.9 if answer != "" else 0.0  # Method reliability proxy; not statistically calibrated.
        except (KeyError, ValueError, ZeroDivisionError) as ex:
            answer, reason, confidence = "", f"Không hỗ trợ / thiếu dữ liệu: {ex}", 0.0
        fields = str(q.source_fields).split(";")
        files = sorted({FIELD_SOURCE.get(f, "") for f in fields if f})
        output.append({"question_id": q.question_id, "answer": answer,
            "evidence_source_files": ";".join(f for f in files if f),
            "evidence_source_fields": str(q.source_fields), "explanation": reason,
            "confidence": confidence, "model_name": "Deterministic_NumericalQA_v1",
            "processing_time_ms": round((time.perf_counter() - t0) * 1000, 3)})
    return pd.DataFrame(output)
