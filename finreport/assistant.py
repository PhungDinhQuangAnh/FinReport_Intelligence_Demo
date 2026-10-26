"""Deterministic, source-grounded financial analyst assistant.

This is a rule-based query interface, not a general LLM. The Numerical QA public
sample accuracy is calculated separately by finreport.qa / evaluation.evaluate_qa.
Unsupported free-form requests never receive a fabricated result or confidence.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from .alerts import FIELD_SOURCE
from .provenance import METRIC_INPUTS


def _normalized(text: str) -> str:
    """Simplify accent/case variations without changing numeric/company tokens."""
    text = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _company(text: str) -> str | None:
    match = re.search(r"\bC0?\d{2}\b", text.upper())
    return match.group(0) if match else None


def _years(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"\b20\d{2}\b", text)]


def _matches(text: str, aliases: tuple[str, ...]) -> bool:
    return any(alias in text for alias in aliases)


# Most specific patterns first: "CFO/Net Income" must not match plain "CFO".
METRIC_PATTERNS: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("cfo_to_net_income_x", ("cfo/net income", "cfo/ni", "cfo tren loi nhuan", "cfo / net income", "chat luong loi nhuan"), "CFO / Lợi nhuận ròng", "lần"),
    ("free_cash_flow_vnd_mn", ("free cash flow", "fcf", "dong tien tu do"), "Dòng tiền tự do (FCF)", "triệu VND"),
    ("capex_intensity_pct", ("capex intensity", "cuong do dau tu"), "CAPEX intensity", "%"),
    ("debt_maturing_within_12m_pct", ("no dao han", "debt maturing", "dao han trong vong 12"), "Nợ đáo hạn trong vòng 12 tháng", "%"),
    ("gross_margin_pct", ("bien loi nhuan gop", "gross margin"), "Biên lợi nhuận gộp", "%"),
    ("net_margin_pct", ("bien loi nhuan rong", "net margin"), "Biên lợi nhuận ròng", "%"),
    ("operating_margin_pct", ("bien loi nhuan hoat dong", "operating margin"), "Biên lợi nhuận hoạt động", "%"),
    ("debt_to_assets_pct", ("debt/assets", "debt / assets", "no vay/tong tai san", "no vay tren tong tai san"), "Nợ vay / Tổng tài sản", "%"),
    ("debt_to_equity_x", ("debt/equity", "debt / equity", "no vay/von chu"), "Nợ vay / Vốn chủ", "lần"),
    ("interest_coverage_x", ("interest coverage", "kha nang tra lai"), "Khả năng trả lãi", "lần"),
    ("current_ratio_x", ("current ratio", "he so thanh toan hien hanh", "thanh toan hien hanh"), "Current Ratio", "lần"),
    ("quick_ratio_x", ("quick ratio", "he so thanh toan nhanh", "thanh toan nhanh"), "Quick Ratio", "lần"),
    ("revenue_growth_pct", ("tang truong doanh thu", "toc do tang doanh thu", "revenue growth"), "Tăng trưởng doanh thu", "%"),
    ("total_debt_growth_pct", ("tang truong tong no vay", "toc do tang tong no vay", "tong no vay tang"), "Tăng trưởng tổng nợ vay", "%"),
    ("dso_days", ("dso", "so ngay phai thu"), "DSO", "ngày"),
    ("inventory_days", ("inventory days", "so ngay ton kho"), "Inventory Days", "ngày"),
    ("dpo_days", ("dpo", "so ngay phai tra"), "DPO", "ngày"),
    ("working_capital_vnd_mn", ("working capital", "von luu dong rong"), "Vốn lưu động ròng", "triệu VND"),
    ("cfo_vnd_mn", ("cfo", "luu chuyen tien thuan tu hoat dong kinh doanh", "dong tien tu hoat dong kinh doanh", "dong tien kinh doanh"), "CFO – Lưu chuyển tiền từ hoạt động kinh doanh", "triệu VND"),
    ("capital_expenditure_vnd_mn", ("capex", "capital expenditure", "chi dau tu tai san"), "CAPEX", "triệu VND"),
    ("total_liabilities_vnd_mn", ("tong no phai tra", "total liabilities"), "Tổng nợ phải trả", "triệu VND"),
    ("total_debt_vnd_mn", ("tong no vay", "total debt"), "Tổng nợ vay", "triệu VND"),
    ("accounts_receivable_vnd_mn", ("khoan phai thu", "accounts receivable"), "Khoản phải thu", "triệu VND"),
    ("inventory_vnd_mn", ("hang ton kho", "ton kho", "inventory"), "Hàng tồn kho", "triệu VND"),
    ("net_income_vnd_mn", ("loi nhuan rong", "loi nhuan sau thue", "net income"), "Lợi nhuận ròng", "triệu VND"),
    ("revenue_vnd_mn", ("doanh thu", "revenue"), "Doanh thu", "triệu VND"),
    ("ending_cash_vnd_mn", ("ending cash", "tien cuoi ky"), "Tiền cuối kỳ", "triệu VND"),
    ("financial_health_score", ("health score", "diem suc khoe", "suc khoe tai chinh"), "Điểm sức khỏe tài chính", "điểm"),
)

ADDITIONAL_SOURCE = {
    "total_liabilities_vnd_mn": "balance_sheet.csv",
    "total_equity_vnd_mn": "balance_sheet.csv",
    "total_debt_vnd_mn": "balance_sheet.csv",  # Derived from short-term + long-term debt; handled below.
}


def _metric(text: str) -> tuple[str, str, str] | None:
    for key, aliases, name, unit in METRIC_PATTERNS:
        if _matches(text, aliases):
            return key, name, unit
    return None


def _number(value: float, unit: str) -> str:
    """Vietnamese numeric notation: thousands '.' and decimal ','."""
    places = 0 if unit == "triệu VND" and float(value).is_integer() else 2
    return f"{float(value):,.{places}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def _unsupported(reason: str) -> dict:
    return {"status": "unsupported", "answer": reason, "evidence": "", "confidence": 0.0}


def _evidence(company: str, year: int, metric: str, value: float) -> str:
    if metric == "cfo_vnd_mn":
        field = "net_cash_from_operating_activities_vnd_mn"
        return f"cashflow.csv:{field}:{company}:{year} = {value:g}"
    if metric == "total_debt_vnd_mn":
        return (f"balance_sheet.csv:short_term_debt_vnd_mn:{company}:{year}; "
                f"balance_sheet.csv:long_term_debt_vnd_mn:{company}:{year}")
    if metric in FIELD_SOURCE or metric in ADDITIONAL_SOURCE:
        source = FIELD_SOURCE.get(metric, ADDITIONAL_SOURCE.get(metric))
        raw_value = f"{value:.10f}".rstrip("0").rstrip(".")
        return f"{source}:{metric}:{company}:{year} = {raw_value}"
    fields = METRIC_INPUTS.get(metric, [])
    years = [year-1, year] if metric in {"revenue_growth_pct", "roa_pct", "roe_pct",
                                         "dso_days", "inventory_days", "dpo_days"} else [year]
    parts = []
    for y in years:
        for field in fields:
            source = FIELD_SOURCE.get(field, ADDITIONAL_SOURCE.get(field))
            if source:
                parts.append(f"{source}:{field}:{company}:{y}")
    if parts:
        return "; ".join(parts)
    # When source mapping is not declared, cite calculated output instead.
    return f"analysis_full_gold.csv:{metric}:{company}:{year} = {value:.10f}"


def answer_user_query(text: str, analysis: pd.DataFrame) -> dict:
    question = (text or "").strip()
    if not question:
        return _unsupported("Vui lòng nhập câu hỏi tài chính.")
    low = _normalized(question)
    company = _company(question)
    years = _years(question)
    year = years[0] if years else None

    if "top" in low and _matches(low, ("rui ro", "risk")):
        year = year or int(analysis.fiscal_year.max())
        match = re.search(r"top\s*(\d+)", low)
        count = min(max(int(match.group(1)), 1), 10) if match else 5
        peers = analysis.loc[analysis.fiscal_year == year].sort_values(
            ["risk_score", "company_id"], ascending=[False, True]
        ).head(count)
        if peers.empty:
            return _unsupported(f"Không tìm thấy dữ liệu năm {year}.")
        lines = [f"{r.company_id}: {r.predicted_severity}, risk={r.risk_score:.2f}, health={r.financial_health_score:.1f}" for r in peers.itertuples()]
        return {"status": "answered", "answer": f"Top {len(peers)} rủi ro năm {year}: " + " | ".join(lines),
                "evidence": f"analysis_full_gold.csv:fiscal_year={year}:risk_score", "confidence": 0.95}

    selected_metric = _metric(low)
    if not company and year and _matches(low, ("cfo am", "cfo < 0", "dong tien kinh doanh am")):
        found = analysis.loc[(analysis.fiscal_year == year) & (analysis.cfo_vnd_mn < 0)].sort_values("company_id")
        names = "; ".join(found.company_id) if not found.empty else "Không có doanh nghiệp nào"
        return {"status": "answered", "answer": f"Doanh nghiệp có CFO âm năm {year}: {names}.",
                "evidence": f"cashflow.csv:net_cash_from_operating_activities_vnd_mn:fiscal_year={year}",
                "confidence": 0.93}
    if not company and len(years) >= 2 and selected_metric and selected_metric[0] == "gross_margin_pct" and \
            _matches(low, ("suy giam", "giam manh nhat")):
        start, end = min(years), max(years)
        initial = analysis.loc[analysis.fiscal_year == start, ["company_id", "gross_margin_pct"]].set_index("company_id")
        final = analysis.loc[analysis.fiscal_year == end, ["company_id", "gross_margin_pct"]].set_index("company_id")
        delta = (final.gross_margin_pct - initial.gross_margin_pct).dropna()
        if delta.empty:
            return _unsupported("Không đủ dữ liệu biên lợi nhuận gộp để xếp hạng mức suy giảm.")
        firm = delta.idxmin()
        return {"status": "answered", "answer": f"Doanh nghiệp có Gross Margin suy giảm mạnh nhất {start}–{end}: "
                f"{firm} (thay đổi {_number(delta.loc[firm], '%')} điểm %).",
                "evidence": f"income_statement.csv:gross_profit_vnd_mn;revenue_vnd_mn:{firm}:{start},{end}",
                "confidence": 0.93}
    if not company and year and selected_metric and _matches(low, ("cao nhat", "thap nhat", "lon nhat")):
        key, name, unit = selected_metric
        if key not in analysis.columns:
            return _unsupported("Chưa có chỉ tiêu tương ứng trong dữ liệu.")
        peers = analysis.loc[analysis.fiscal_year == year, ["company_id", key]].dropna()
        if peers.empty:
            return _unsupported(f"Không có dữ liệu {name} cho năm {year}.")
        ascending = "thap nhat" in low
        n = 3 if re.search(r"\b3\s+doanh nghiep\b", low) else 1
        top = peers.sort_values([key, "company_id"], ascending=[ascending, True]).head(n)
        return {"status": "answered", "answer": f"{name} {'thấp' if ascending else 'cao'} nhất năm {year}: " +
                "; ".join(f"{r.company_id} ({_number(getattr(r, key), unit)} {unit})" for r in top.itertuples()),
                "evidence": f"analysis_full_gold.csv:{key}:fiscal_year={year}", "confidence": 0.93}

    if not company or year is None:
        return _unsupported("Câu hỏi cần nêu rõ doanh nghiệp (ví dụ C007) và năm (ví dụ 2025), "
                            "hoặc dùng 'top 5 rủi ro 2025'.")
    matching = analysis.loc[(analysis.company_id == company) & (analysis.fiscal_year == year)]
    if matching.empty:
        return _unsupported(f"Không có số liệu {company} năm {year} trong Data Pack 2021–2025.")
    row = matching.iloc[0]

    # Compound requests must be answered with both referenced quantities,
    # never with a misleading single-value match.
    if len(years) >= 2 and selected_metric and selected_metric[0] == "gross_margin_pct" and \
            _matches(low, ("diem phan tram", "thay doi")):
        start, end = min(years), max(years)
        subset = analysis.loc[(analysis.company_id == company) & (analysis.fiscal_year.isin([start, end]))]
        if len(subset) != 2:
            return _unsupported("Không đủ dữ liệu hai mốc năm để tính thay đổi biên lợi nhuận gộp.")
        v1 = float(subset.loc[subset.fiscal_year == start, "gross_margin_pct"].iloc[0])
        v2 = float(subset.loc[subset.fiscal_year == end, "gross_margin_pct"].iloc[0])
        delta = v2 - v1
        direction = "giảm" if delta < 0 else "tăng" if delta > 0 else "không đổi"
        return {"status": "answered", "answer": f"Gross Margin {company} từ {start} đến {end} "
                f"{direction} {_number(abs(delta), '%')} điểm phần trăm "
                f"({_number(v1, '%')}% → {_number(v2, '%')}%).",
                "evidence": _evidence(company, start, "gross_margin_pct", v1) + "; " +
                _evidence(company, end, "gross_margin_pct", v2), "confidence": 0.94}

    if _matches(low, ("bang nhau", "co bang", "doi chieu")) and _matches(low, ("ending cash", "tien cuoi ky")):
        left, right = row.get("ending_cash_vnd_mn"), row.get("cash_and_cash_equivalents_vnd_mn")
        if pd.isna(left) or pd.isna(right):
            return _unsupported("Không đủ hai số dư tiền để đối chiếu.")
        same = abs(float(left) - float(right)) <= 1e-6
        return {"status": "answered", "answer": ("Có" if same else "Không") +
                f". Ending Cash = {_number(left, 'triệu VND')} và Cash & Cash Equivalents = {_number(right, 'triệu VND')} triệu VND ({company}/{year}).",
                "evidence": _evidence(company, year, "ending_cash_vnd_mn", left) + "; " +
                _evidence(company, year, "cash_and_cash_equivalents_vnd_mn", right), "confidence": 0.95}

    has_revenue = _matches(low, ("doanh thu", "revenue"))
    has_cfo = _matches(low, ("cfo", "dong tien kinh doanh", "luu chuyen tien thuan"))
    if has_revenue and has_cfo and _matches(low, ("xu huong", "giai doan")):
        start, end = (min(years), max(years)) if len(years) >= 2 else (year-1, year)
        subset = analysis.loc[(analysis.company_id == company) & (analysis.fiscal_year.isin([start, end]))]
        if len(subset) != 2:
            return _unsupported("Không đủ hai năm dữ liệu để phân tích xu hướng doanh thu và CFO.")
        a = subset.set_index("fiscal_year").loc[start]
        b = subset.set_index("fiscal_year").loc[end]
        comment = ("Doanh thu tăng nhưng CFO giảm: dòng tiền hoạt động không theo kịp tăng trưởng doanh thu, "
                   "cần xem xét phải thu và tồn kho." if b.revenue_vnd_mn > a.revenue_vnd_mn and b.cfo_vnd_mn < a.cfo_vnd_mn
                   else "Cần phân tích thêm biến động phải thu, tồn kho và chất lượng dòng tiền.")
        answer = (f"{company} giai đoạn {start}–{end}: doanh thu "
                  f"{_number(a.revenue_vnd_mn, 'triệu VND')} → {_number(b.revenue_vnd_mn, 'triệu VND')} triệu VND; "
                  f"CFO {_number(a.cfo_vnd_mn, 'triệu VND')} → {_number(b.cfo_vnd_mn, 'triệu VND')} triệu VND. "
                  + comment)
        evidence = "; ".join(_evidence(company, y, metric, float(r[metric]))
                              for y, r in [(start, a), (end, b)] for metric in ["revenue_vnd_mn", "cfo_vnd_mn"])
        return {"status": "answered", "answer": answer, "evidence": evidence, "confidence": 0.9}

    if _matches(low, ("tang nhanh hon", "cao hon toc do tang")) and has_revenue:
        other = ("accounts_receivable_vnd_mn", "Phải thu") if _matches(low, ("phai thu",)) else (
            ("inventory_vnd_mn", "Tồn kho") if _matches(low, ("ton kho",)) else (None, ""))
        field, name = other
        start, end = (min(years), max(years)) if len(years) >= 2 else (year-1, year)
        if field:
            left = analysis.loc[(analysis.company_id == company) & (analysis.fiscal_year == start)]
            right = analysis.loc[(analysis.company_id == company) & (analysis.fiscal_year == end)]
            if len(left) != 1 or len(right) != 1:
                return _unsupported("Không đủ dữ liệu năm trước để so sánh tốc độ tăng.")
            a, b = left.iloc[0], right.iloc[0]
            if a[field] == 0 or a.revenue_vnd_mn == 0:
                return _unsupported("Mẫu số bằng 0, không thể tính tăng trưởng.")
            g1 = (b[field] / a[field] - 1) * 100
            g2 = (b.revenue_vnd_mn / a.revenue_vnd_mn - 1) * 100
            yes = g1 > g2
            return {"status": "answered", "answer":
                    f"{'Có' if yes else 'Không'}. {name} tăng {_number(g1, '%')}%, "
                    f"doanh thu tăng {_number(g2, '%')}% giai đoạn {start}–{end} ({company}).",
                    "evidence": "; ".join(_evidence(company, y, m, float(r[m]))
                                         for y, r in [(start, a), (end, b)]
                                         for m in (field, "revenue_vnd_mn")), "confidence": 0.93}

    if _matches(low, ("giai thich", "canh bao", "rui ro")) and not _matches(low, ("top ",)):
        return {"status": "answered", "answer": str(row.gold_explanation) + " " + str(row.alert_reason),
                "evidence": str(row.evidence_fields), "confidence": float(row.confidence)}

    if _matches(low, ("so sanh", "benchmark", "so voi nganh")) and not _matches(low, ("so voi 20",)):
        key, name, unit = selected_metric or ("gross_margin_pct", "Biên lợi nhuận gộp", "%")
        benchmark_key = f"peer_median__{key}"
        if key not in row.index or benchmark_key not in row.index or pd.isna(row[benchmark_key]):
            return _unsupported(f"Chỉ tiêu {name} chưa có benchmark cùng ngành.")
        answer = (f"{company}/{year}: {name} {_number(row[key], unit)} {unit}; "
                  f"trung vị cùng ngành {_number(row[benchmark_key], unit)} {unit}.")
        return {"status": "answered", "answer": answer, "evidence": _evidence(company, year, key, row[key]) +
                f"; analysis_full_gold.csv:{benchmark_key}:fiscal_year={year}", "confidence": 0.94}

    if _matches(low, ("suc khoe", "health score")) and not selected_metric:
        selected_metric = ("financial_health_score", "Điểm sức khỏe tài chính", "điểm")

    if len(set(years)) > 1 and (not selected_metric or selected_metric[0] not in
                                 {"revenue_growth_pct", "total_debt_growth_pct"}):
        return _unsupported("Câu hỏi đề cập nhiều năm nhưng chưa rõ phép so sánh. "
                            "Hãy hỏi xu hướng doanh thu và CFO, hoặc nêu rõ 'giảm bao nhiêu điểm phần trăm'.")

    if has_revenue and has_cfo:
        return _unsupported("Câu hỏi chứa cả doanh thu và CFO. Hãy yêu cầu 'xu hướng doanh thu và CFO "
                            "của C007 giai đoạn 2023–2025' hoặc hỏi riêng từng chỉ tiêu.")

    # Arithmetic values come from the same calculated dataset that feeds QA and dashboard.
    if selected_metric:
        key, name, unit = selected_metric
        if key not in row.index or pd.isna(row[key]):
            return _unsupported(f"{name} của {company} năm {year} chưa thể tính từ dữ liệu hiện có "
                                "(có thể thiếu số dư năm trước hoặc mẫu số bằng 0).")
        value = float(row[key])
        return {"status": "answered", "answer": f"{name} của {company} năm {year}: {_number(value, unit)} {unit}.",
                "evidence": _evidence(company, year, key, value), "confidence": 0.95}

    return _unsupported("Trợ lý chưa hỗ trợ dạng câu hỏi này. Bạn có thể hỏi CFO, doanh thu, lợi nhuận, "
                        "Current Ratio, Gross Margin, DSO, FCF, so sánh cùng ngành hoặc giải thích rủi ro "
                        "cho một doanh nghiệp/năm. 30 câu mẫu BTC được đánh giá riêng trong mục 'QA mẫu'.")
