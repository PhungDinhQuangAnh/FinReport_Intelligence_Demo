"""FinReport Intelligence | Streamlit dashboard.

Presentation-only redesign: all calculations, alerts, benchmarks, verification,
scenario modelling and exports are still produced by the existing finreport modules.
Run from the project folder with: streamlit run app.py
"""

from __future__ import annotations

from html import escape
import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from finreport.assistant import answer_user_query
from finreport.config import SAMPLES
from finreport.benchmark import BENCHMARK_METRICS
from finreport.pipeline import build
from finreport.provenance import evidence_for_metric
from finreport.review import load_reviews, save_review
from finreport.scenario import scenario_metrics

st.set_page_config(
    page_title="FinReport Intelligence | Financial Command Center",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────── DESIGN SYSTEM ─────────────────────
NAVY = "#142846"
BLUE = "#2873EB"
TEAL = "#0C9F91"
AMBER = "#E9A23B"
RED = "#E65363"
SLATE = "#64748B"
SOFT = "#F4F7FC"
SEVERITY_COLOR = {"LOW": TEAL, "MEDIUM": AMBER, "HIGH": "#F07F43", "CRITICAL": RED}
SEVERITY_VI = {
    "LOW": "Thấp",
    "MEDIUM": "Trung bình",
    "HIGH": "Cao",
    "CRITICAL": "Nghiêm trọng",
}
METRIC_LABELS = {
    "revenue_growth_pct": "Tăng trưởng doanh thu (%)",
    "gross_margin_pct": "Biên lợi nhuận gộp (%)",
    "operating_margin_pct": "Biên lợi nhuận HĐKD (%)",
    "net_margin_pct": "Biên lợi nhuận ròng (%)",
    "current_ratio_x": "Thanh toán hiện hành (lần)",
    "quick_ratio_x": "Thanh toán nhanh (lần)",
    "debt_to_assets_pct": "Nợ / Tổng tài sản (%)",
    "debt_to_equity_x": "Nợ / Vốn chủ (lần)",
    "roa_pct": "ROA (%)",
    "roe_pct": "ROE (%)",
    "cfo_margin_pct": "CFO / Doanh thu (%)",
    "cfo_to_net_income_x": "CFO / Lợi nhuận ròng (lần)",
    "dso_days": "Số ngày phải thu (DSO)",
    "inventory_days": "Số ngày tồn kho",
    "interest_coverage_x": "Khả năng trả lãi (lần)",
    "free_cash_flow_vnd_mn": "Dòng tiền tự do (triệu VND)",
    "financial_health_score": "Điểm sức khỏe (0–100)",
    "risk_score": "Điểm rủi ro (0–1)",
}
METRIC_SECTIONS = {
    "Lợi nhuận": [
        "revenue_growth_pct",
        "gross_margin_pct",
        "operating_margin_pct",
        "net_margin_pct",
        "roa_pct",
        "roe_pct",
    ],
    "Thanh khoản & đòn bẩy": [
        "current_ratio_x",
        "quick_ratio_x",
        "debt_to_assets_pct",
        "debt_to_equity_x",
        "interest_coverage_x",
    ],
    "Dòng tiền & vận hành": [
        "cfo_margin_pct",
        "cfo_to_net_income_x",
        "free_cash_flow_vnd_mn",
        "dso_days",
        "inventory_days",
    ],
}
NAV_ITEMS = [
    "Tổng quan điều hành",
    "Hồ sơ doanh nghiệp",
    "So sánh cùng ngành",
    "Cảnh báo & truy vết",
    "Mô phỏng & trợ lý",
    "Chất lượng & xuất dữ liệu",
]
NAV_ICONS = ["◈", "▣", "◎", "⚑", "◇", "☑"]

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
[data-testid="stAppViewContainer"] {background: #F4F7FC;}
[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1.45rem; padding-bottom: 2.8rem; max-width: 1520px;}
[data-testid="stSidebar"] {background: #FFFFFF; border-right: 1px solid #E6ECF3;}
[data-testid="stSidebar"] .block-container {padding-top: 1.3rem;}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {color: #394D68;}
h1, h2, h3, h4 {color: #142846; letter-spacing: -.035em;}
h1 {font-size: 2rem !important; font-weight: 800 !important;}
h2 {font-size: 1.38rem !important; font-weight: 760 !important;}
h3 {font-size: 1.1rem !important; font-weight: 700 !important;}
[data-testid="stMetric"] {background: white; border: 1px solid #E6EBF3; border-radius: 16px; padding: 16px 19px; min-height: 108px;}
[data-testid="stMetricLabel"] {font-size: .87rem !important; color: #64748B;}
[data-testid="stMetricValue"] {font-weight: 800; color: #142846;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 16px;}
.stTabs [data-baseweb="tab-list"] {gap: 8px; border-bottom: 1px solid #E4EAF3;}
.stTabs [data-baseweb="tab"] {height: 45px; border-radius: 9px 9px 0 0; font-weight: 600;}
.stTabs [aria-selected="true"] {color: #2873EB !important;}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: #2873EB; border: 1px solid #2873EB; border-radius: 9px; font-weight: 700;
}
.stButton > button, .stDownloadButton > button {border-radius: 9px;}
[data-testid="stDataFrame"] {border: 1px solid #E8EDF5; border-radius: 12px; overflow: hidden;}
[data-testid="stExpander"] {background: white; border: 1px solid #E8EDF4; border-radius: 12px;}
div[data-testid="stAlert"] {border-radius: 12px;}
.brand-box {background: linear-gradient(135deg,#142846,#254A7C); color: white;
    padding: 18px; border-radius: 15px; margin-bottom: 16px;}
.brand-kicker {font-size: .63rem; font-weight: 800; color: #7DC9F9; letter-spacing: 2px;}
.brand-title {font-size: 1.12rem; font-weight: 800; line-height: 1.2; margin: 7px 0 5px;}
.brand-caption {font-size: .75rem; color: #C9D7EB;}
.side-heading {font-size: .69rem; font-weight: 800; color: #91A0B5;
    letter-spacing: 1.6px; margin: 16px 0 9px;}
.hero {background: linear-gradient(112deg,#142846 0%,#234778 55%,#2B67A7 100%);
  padding: 27px 32px; border-radius: 19px; color: white; margin-bottom: 21px;
  position: relative; overflow: hidden; box-shadow: 0 10px 32px rgba(20,40,70,.11);}
.hero:after {content: ''; position: absolute; width: 240px; height: 240px;
  right: -55px; top: -125px; border: 1px solid rgba(255,255,255,.16);
  border-radius: 50%; box-shadow: 0 0 0 30px rgba(255,255,255,.025), 0 0 0 75px rgba(255,255,255,.02);}
.hero-kicker {font-size: .72rem; letter-spacing: 1.5px; color: #9BC7FD; font-weight: 800;}
.hero-title {font-weight: 800; letter-spacing: -.55px; font-size: 1.87rem; margin: 6px 0 7px; line-height: 1.28;}
.hero-desc {font-size: .92rem; color: #D4E3F6; margin: 0; max-width: 850px;}
.hero-context {margin-top: 16px; color: #E5F1FF; font-size: .79rem;}
.hero-context span {display: inline-block; border: 1px solid rgba(255,255,255,.27);
  background: rgba(255,255,255,.075); padding: 5px 10px; border-radius: 7px; margin-right: 7px; margin-top: 4px;}
.section-heading {font-weight: 800; font-size: 1.1rem; color: #142846; margin: 17px 0 3px;}
.section-note {font-size: .82rem; color: #71829B; margin: 0 0 13px;}
.kpi-card {min-height: 121px; border-radius: 15px; background: white; padding: 19px 18px;
  border: 1px solid #E6EBF3; box-shadow: 0 3px 15px rgba(30,55,90,.025); margin-bottom: 8px;}
.kpi-label {color: #73839A; font-size: .81rem; font-weight: 650; margin-bottom: 10px;}
.kpi-value {color: #142846; font-weight: 800; font-size: 1.62rem; letter-spacing: -.6px; line-height: 1.22;}
.kpi-note {color: #8391A4; font-size: .72rem; margin-top: 8px;}
.kpi-marker {width: 6px; height: 6px; border-radius: 50%; display: inline-block;
  margin-right: 6px; position: relative; bottom: 2px;}
.insight-card {background: white; border: 1px solid #E4EBF4; border-radius: 14px;
  padding: 17px 20px; margin: 9px 0;}
.insight-top {font-size: .75rem; color: #8290A5; text-transform: uppercase; font-weight: 800; letter-spacing: 1px;}
.insight-title {font-size: 1.03rem; font-weight: 750; color: #172D4C; margin: 6px 0 5px;}
.insight-body {color: #546780; font-size: .87rem; line-height: 1.65;}
.status-chip {display: inline-block; padding: 5px 10px; border-radius: 7px;
  font-size: .77rem; font-weight: 800;}
.rule-box {border-left: 3px solid #E65363; background: #FFF9F8; border-radius: 0 12px 12px 0;
  padding: 12px 16px; margin-bottom: 10px; color: #41516A; font-size: .88rem; line-height: 1.6;}
.footer-note {margin-top: 28px; border-top: 1px solid #DEE6F0; padding-top: 16px;
  color: #8692A3; font-size: .76rem;}
.mini-help {color: #75869D; font-size: .79rem;}
/* Navigation: wide, tactile radio selections */
[data-testid="stSidebar"] [role="radiogroup"] {gap: 4px;}
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding: 9px 10px; border-radius: 9px; background: transparent; transition: background .15s;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: #EAF2FF; color: #1C57AF; font-weight: 750;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background: #F1F5FA;}
@media(max-width: 950px) {.hero {padding: 22px;} .hero-title {font-size: 1.4rem;} .block-container {padding-top: 1rem;}}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Đang xử lý dữ liệu tài chính…")
def load_project():
    return build(save=False)


def num(value, digits=1, suffix="", fallback="N/A") -> str:
    if value is None or pd.isna(value) or not np.isfinite(float(value)):
        return fallback
    return f"{float(value):,.{digits}f}{suffix}"


def pretty_name(name: str) -> str:
    return METRIC_LABELS.get(name, name.replace("_", " ").title())


def card(label, value, note="", accent=BLUE):
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label"><span class="kpi-marker" '
        f'style="background:{accent}"></span>{escape(str(label))}</div>'
        f'<div class="kpi-value">{escape(str(value))}</div>'
        f'<div class="kpi-note">{escape(str(note))}</div></div>',
        unsafe_allow_html=True,
    )


def section(title, note=""):
    st.markdown(
        f'<div class="section-heading">{escape(title)}</div>', unsafe_allow_html=True
    )
    if note:
        st.markdown(
            f'<div class="section-note">{escape(note)}</div>', unsafe_allow_html=True
        )


def callout(title, body, kicker="PHÂN TÍCH TỰ ĐỘNG"):
    st.markdown(
        f'<div class="insight-card"><div class="insight-top">{escape(kicker)}</div>'
        f'<div class="insight-title">{escape(str(title))}</div>'
        f'<div class="insight-body">{escape(str(body))}</div></div>',
        unsafe_allow_html=True,
    )


def format_table(frame: pd.DataFrame, digits=2) -> pd.DataFrame:
    result = frame.copy()
    for col in result.select_dtypes(include="number").columns:
        if col != "fiscal_year":
            result[col] = result[col].map(lambda value: num(value, digits=digits))
    return result


def chart_style(fig, height=330, legend=True):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=9, r=17, t=24, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#52647B"),
        title_font=dict(color=NAVY, size=15),
        hoverlabel=dict(bgcolor="white", font_color=NAVY),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False, linecolor="#E3EAF4", tickfont=dict(size=11))
    fig.update_yaxes(
        gridcolor="#EDF1F7", zerolinecolor="#E3EAF4", tickfont=dict(size=11)
    )
    return fig


def plot(fig, height=330, legend=True):
    st.plotly_chart(
        chart_style(fig, height=height, legend=legend), use_container_width=True
    )


def status_chip(level):
    color = SEVERITY_COLOR.get(str(level), SLATE)
    label = SEVERITY_VI.get(str(level), str(level))
    return (
        f'<span class="status-chip" style="background:{color}16;'
        f'color:{color}; border:1px solid {color}35">{escape(label)}</span>'
    )


def dataframe(frame, **kwargs):
    st.dataframe(frame, use_container_width=True, hide_index=True, **kwargs)


try:
    out = load_project()
except Exception as exc:
    st.error(
        "Không thể khởi tạo pipeline tài chính. Kiểm tra thư mục dữ liệu và dependencies."
    )
    st.exception(exc)
    st.stop()

analysis = out["analysis"]
details = out["alerts_detail"]
kpi = out["kpi"]
companies = (
    analysis[["company_id", "company_name"]]
    .drop_duplicates()
    .set_index("company_id")["company_name"]
    .to_dict()
)
years = sorted(analysis.fiscal_year.unique().tolist(), reverse=True)
company_ids = sorted(companies)

# ───────────────────── NAVIGATION & GLOBAL FILTERS ─────────────────────
with st.sidebar:
    st.markdown(
        '<div class="brand-box"><div class="brand-kicker">FINANCIAL ANALYTICS</div>'
        '<div class="brand-title">FINREPORT<br>INTELLIGENCE</div>'
        '<div class="brand-caption">Gold Edition · Decision Support</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-heading">ĐIỀU HƯỚNG</div>', unsafe_allow_html=True)
    page = st.radio(
        "Chọn màn hình", NAV_ITEMS, label_visibility="collapsed", key="nav_page"
    )
    st.divider()
    st.markdown(
        '<div class="side-heading">BỘ LỌC TOÀN CỤC</div>', unsafe_allow_html=True
    )
    year = int(st.selectbox("Năm tài chính", years, key="filter_year"))
    company = st.selectbox(
        "Doanh nghiệp phân tích",
        company_ids,
        format_func=lambda code: f"{code} · {companies[code]}",
        key="filter_company",
    )
    st.caption(
        "Benchmark luôn dùng toàn bộ doanh nghiệp trong cùng ngành và năm, không chỉ doanh nghiệp đang chọn."
    )
    st.divider()
    st.markdown(
        '<div class="side-heading">TRẠNG THÁI HỆ THỐNG</div>', unsafe_allow_html=True
    )
    st.markdown("🟢 **Data pipeline** · " + escape(str(out["validation"]["status"])))
    st.markdown("🔎 **Calculate → Verify → Explain**")
    st.caption(f"Run ID: {kpi['run_id']}")

current = analysis.loc[
    (analysis.company_id == company) & (analysis.fiscal_year == year)
].iloc[0]
company_data = analysis.loc[analysis.company_id == company].sort_values("fiscal_year")
year_data = analysis.loc[analysis.fiscal_year == year].copy()
company_label = f"{company} · {companies[company]}"

PAGE_META = {
    NAV_ITEMS[0]: (
        "TỔNG QUAN NGÀNH",
        "Financial Command Center",
        "Theo dõi sức khỏe tài chính, phát hiện doanh nghiệp cần ưu tiên phân tích.",
    ),
    NAV_ITEMS[1]: (
        "COMPANY 360°",
        "Hồ sơ tài chính doanh nghiệp",
        "Khám phá tỷ số, xu hướng 5 năm và chất lượng dòng tiền của doanh nghiệp.",
    ),
    NAV_ITEMS[2]: (
        "PEER INTELLIGENCE",
        "So sánh cùng ngành",
        "Đặt chỉ tiêu của doanh nghiệp cạnh trung vị, phân vị và bất thường cùng ngành.",
    ),
    NAV_ITEMS[3]: (
        "CALCULATE → VERIFY → EXPLAIN",
        "Trung tâm cảnh báo & truy vết",
        "Giải thích từng dấu hiệu rủi ro cùng bằng chứng và xác nhận của chuyên viên.",
    ),
    NAV_ITEMS[4]: (
        "DECISION LAB",
        "Mô phỏng & trợ lý phân tích",
        "Thử giả định What-if và đặt câu hỏi tài chính có trích xuất bằng chứng.",
    ),
    NAV_ITEMS[5]: (
        "TRUST & GOVERNANCE",
        "Chất lượng hệ thống & dữ liệu",
        "Kiểm tra tính đúng đắn, minh bạch quy trình và tải kết quả báo cáo.",
    ),
}
kicker, page_title, page_desc = PAGE_META[page]
st.markdown(
    f'<div class="hero"><div class="hero-kicker">{escape(kicker)} · GOLD MVP</div>'
    f'<div class="hero-title">{escape(page_title)}</div>'
    f'<p class="hero-desc">{escape(page_desc)}</p>'
    f'<div class="hero-context"><span>◷ Năm {year}</span><span>▣ {escape(company)}</span>'
    f"<span>12 doanh nghiệp giả lập · 2021–2025</span></div></div>",
    unsafe_allow_html=True,
)

# ───────────────────── 1. EXECUTIVE OVERVIEW ─────────────────────
if page == NAV_ITEMS[0]:
    critical_count = int((year_data.predicted_severity == "CRITICAL").sum())
    high_count = int((year_data.predicted_severity == "HIGH").sum())
    with st.container():
        cols = st.columns(4, gap="medium")
        with cols[0]:
            card("Doanh nghiệp được phân tích", len(year_data), f"Toàn ngành · {year}")
        with cols[1]:
            card(
                "Rủi ro cao / nghiêm trọng",
                high_count + critical_count,
                f"{critical_count} nghiêm trọng",
                RED,
            )
        with cols[2]:
            card(
                "Điểm sức khỏe trung vị",
                num(year_data.financial_health_score.median(), 1),
                "Thang điểm 0–100",
                TEAL,
            )
        with cols[3]:
            card(
                "Doanh nghiệp có CFO âm",
                int((year_data.cfo_vnd_mn < 0).sum()),
                "Dòng tiền kinh doanh < 0",
                AMBER,
            )

    section(
        "Bức tranh rủi ro toàn ngành",
        "Đối chiếu mức độ rủi ro và phân bố cảnh báo trong năm đang chọn",
    )
    left, right = st.columns([1.64, 1], gap="large")
    with left:
        risk = year_data.sort_values("risk_score", ascending=True).copy()
        risk["Mức độ"] = risk.predicted_severity.map(SEVERITY_VI)
        fig = px.bar(
            risk,
            x="risk_score",
            y="company_id",
            orientation="h",
            color="predicted_severity",
            color_discrete_map=SEVERITY_COLOR,
            category_orders={
                "predicted_severity": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            },
            hover_data={
                "company_name": True,
                "financial_health_score": ":.1f",
                "predicted_severity": False,
            },
            labels={
                "risk_score": "Điểm rủi ro",
                "company_id": "Doanh nghiệp",
                "predicted_severity": "Mức độ",
            },
        )
        fig.update_layout(bargap=0.3, xaxis_range=[0, 1.05])
        plot(fig, height=400)
    with right:
        severity_data = (
            year_data.predicted_severity.value_counts()
            .reindex(["LOW", "MEDIUM", "HIGH", "CRITICAL"], fill_value=0)
            .rename_axis("severity")
            .reset_index(name="count")
        )
        fig = go.Figure(
            go.Pie(
                labels=[SEVERITY_VI[x] for x in severity_data.severity],
                values=severity_data["count"],
                hole=0.7,
                marker=dict(colors=[SEVERITY_COLOR[x] for x in severity_data.severity]),
                textinfo="label+percent",
                textposition="outside",
            )
        )
        fig.add_annotation(
            text=f"<b>{len(year_data)}</b><br>doanh nghiệp",
            showarrow=False,
            font=dict(size=18, color=NAVY),
        )
        plot(fig, height=400, legend=False)

    section(
        "Danh sách ưu tiên theo dõi",
        "Xếp hạng do pipeline tạo ra; chọn doanh nghiệp trong thanh bên để xem chi tiết",
    )
    ranking = year_data.sort_values("priority_rank")[
        [
            "priority_rank",
            "company_id",
            "company_name",
            "financial_health_score",
            "risk_score",
            "confidence",
            "predicted_severity",
            "predicted_primary_scenario",
        ]
    ].copy()
    ranking.columns = [
        "Ưu tiên",
        "Mã",
        "Doanh nghiệp",
        "Health Score",
        "Risk Score",
        "Confidence",
        "Mức cảnh báo",
        "Kịch bản chính",
    ]
    ranking["Mức cảnh báo"] = ranking["Mức cảnh báo"].map(SEVERITY_VI)
    ranking["Confidence"] = ranking["Confidence"].map(lambda v: num(v * 100, 1, "%"))
    ranking["Health Score"] = ranking["Health Score"].map(lambda v: num(v, 1))
    ranking["Risk Score"] = ranking["Risk Score"].map(lambda v: num(v, 3))
    dataframe(ranking, height=370)
    focus = year_data.sort_values("priority_rank").iloc[0]
    callout(
        f"Ưu tiên số 1: {focus.company_id} – {focus.company_name}",
        f"Mức cảnh báo {SEVERITY_VI.get(focus.predicted_severity, focus.predicted_severity)}; "
        f"risk score {num(focus.risk_score, 2)}, health score {num(focus.financial_health_score, 1)}/100. "
        "Đến mục Cảnh báo & truy vết để xem rule, công thức và bằng chứng nguồn.",
        "GỢI Ý HÀNH ĐỘNG",
    )

# ───────────────────── 2. COMPANY 360 ─────────────────────
elif page == NAV_ITEMS[1]:
    st.markdown(f"### {company_label}")
    st.markdown(
        f"**Mức độ cảnh báo:** {SEVERITY_VI.get(current.predicted_severity, current.predicted_severity)} &nbsp; "
        f"· **Kỳ:** {year} &nbsp; · **Độ tin cậy heuristic:** {num(current.confidence*100, 1, '%')}",
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    with cols[0]:
        card(
            "Health Score",
            num(current.financial_health_score, 1, "/100"),
            "Điểm tổng hợp",
            TEAL,
        )
    with cols[1]:
        card("Doanh thu", num(current.revenue_vnd_mn, 0), "Triệu VND", BLUE)
    with cols[2]:
        card("Biên LN ròng", num(current.net_margin_pct, 2, "%"), "Net margin", TEAL)
    with cols[3]:
        card(
            "Dòng tiền HĐKD (CFO)",
            num(current.cfo_vnd_mn, 0),
            "Triệu VND",
            RED if current.cfo_vnd_mn < 0 else TEAL,
        )

    tab1, tab2, tab3 = st.tabs(
        ["Xu hướng tài chính", "Cấu trúc sức khỏe", "Bảng chỉ tiêu & nguồn"]
    )
    with tab1:
        group = st.selectbox("Nhóm chỉ tiêu", list(METRIC_SECTIONS), key="trend_group")
        metric = st.selectbox(
            "Chỉ tiêu theo dõi",
            METRIC_SECTIONS[group],
            format_func=pretty_name,
            key="trend_metric",
        )
        trend = company_data[["fiscal_year", metric]].copy()
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=trend.fiscal_year,
                y=trend[metric],
                name="Doanh nghiệp",
                mode="lines+markers",
                line=dict(color=BLUE, width=3.2),
                marker=dict(size=8),
            )
        )
        peer_col = f"peer_median__{metric}"
        if peer_col in company_data:
            fig.add_trace(
                go.Scatter(
                    x=company_data.fiscal_year,
                    y=company_data[peer_col],
                    name="Trung vị ngành",
                    mode="lines+markers",
                    line=dict(color=AMBER, width=2.4, dash="dash"),
                )
            )
        fig.update_xaxes(dtick=1, title_text="Năm tài chính")
        fig.update_yaxes(title_text=pretty_name(metric))
        plot(fig, height=390)
        section("Điểm đáng chú ý", "Nhận xét tự động trên company-year đã chọn")
        callout("Tóm tắt tài chính", current.gold_explanation)
        with st.expander("Xem nguồn dữ liệu của chỉ tiêu đang chọn"):
            st.code(
                evidence_for_metric(company, year, metric)
                or "Chỉ tiêu phái sinh / chưa có ánh xạ nguồn trực tiếp.",
                language="text",
            )

    with tab2:
        dimensions = pd.DataFrame(
            {
                "Nhóm": [
                    "Khả năng sinh lời",
                    "Thanh khoản",
                    "Chất lượng dòng tiền",
                    "Đòn bẩy tài chính",
                    "Vốn lưu động",
                ],
                "Điểm": [
                    current.health__profitability,
                    current.health__liquidity,
                    current.health__cash_quality,
                    current.health__leverage,
                    current.health__working_capital,
                ],
            }
        )
        left, right = st.columns([1.35, 1], gap="large")
        with left:
            fig = px.bar(
                dimensions.sort_values("Điểm"),
                x="Điểm",
                y="Nhóm",
                orientation="h",
                color="Điểm",
                color_continuous_scale=[RED, AMBER, TEAL],
                range_color=[0, 100],
                range_x=[0, 105],
                text="Điểm",
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(coloraxis_showscale=False)
            plot(fig, height=340, legend=False)
        with right:
            st.markdown("#### 5 chiều sức khỏe tài chính")
            for row in dimensions.itertuples(index=False):
                st.caption(f"{row[0]} · {num(row[1], 1)}/100")
                st.progress(min(1.0, max(0.0, float(row[1]) / 100)))
        section(
            "Lợi nhuận so với dòng tiền",
            "Dòng tiền kinh doanh giúp đánh giá chất lượng lợi nhuận",
        )
        cash = company_data[["fiscal_year", "net_income_vnd_mn", "cfo_vnd_mn"]].melt(
            id_vars="fiscal_year", var_name="Chỉ tiêu", value_name="Triệu VND"
        )
        cash["Chỉ tiêu"] = cash["Chỉ tiêu"].map(
            {"net_income_vnd_mn": "Lợi nhuận ròng", "cfo_vnd_mn": "CFO"}
        )
        fig = px.bar(
            cash,
            x="fiscal_year",
            y="Triệu VND",
            color="Chỉ tiêu",
            barmode="group",
            color_discrete_map={"Lợi nhuận ròng": BLUE, "CFO": TEAL},
        )
        fig.update_xaxes(dtick=1, title_text="Năm")
        plot(fig, height=320)

    with tab3:
        row_fields = (
            ["fiscal_year"]
            + [item for group in METRIC_SECTIONS.values() for item in group]
            + ["financial_health_score"]
        )
        table = company_data[row_fields].rename(
            columns={"fiscal_year": "Năm", **METRIC_LABELS}
        )
        dataframe(format_table(table), height=300)
        st.caption(
            "Giá trị đầu kỳ thiếu dữ liệu được giữ N/A; không tự tạo số liệu năm 2020."
        )
        metric_evidence = st.selectbox(
            "Truy vết chỉ tiêu",
            [item for g in METRIC_SECTIONS.values() for item in g],
            format_func=pretty_name,
            key="source_metric",
        )
        st.code(
            evidence_for_metric(company, year, metric_evidence)
            or "Chỉ tiêu phái sinh / chưa có ánh xạ nguồn trực tiếp.",
            language="text",
        )

# ───────────────────── 3. PEER BENCHMARK ─────────────────────
elif page == NAV_ITEMS[2]:
    section(
        "Phân tích đối sánh",
        "Các thống kê lấy từ cùng phân ngành và cùng năm tài chính; phân vị cao không luôn đồng nghĩa tốt",
    )
    metric = st.selectbox(
        "Chỉ tiêu benchmark",
        BENCHMARK_METRICS,
        index=BENCHMARK_METRICS.index("gross_margin_pct"),
        format_func=pretty_name,
        key="benchmark_metric",
    )
    med_col = f"peer_median__{metric}"
    pct_col = f"peer_percentile__{metric}"
    median = current[med_col]
    delta = (
        current[metric] - median
        if pd.notna(current[metric]) and pd.notna(median)
        else np.nan
    )
    cols = st.columns(4)
    with cols[0]:
        card("Doanh nghiệp", num(current[metric], 2), pretty_name(metric))
    with cols[1]:
        card(
            "Trung vị cùng ngành",
            num(median, 2),
            f"{year} · N={int(current.peer_size)}",
            TEAL,
        )
    with cols[2]:
        card("Chênh lệch so trung vị", num(delta, 2), "Cùng đơn vị với chỉ tiêu", AMBER)
    with cols[3]:
        card(
            "Phân vị", num(current[pct_col], 1, "%"), "Vị trí trong nhóm so sánh", BLUE
        )

    ordered = (
        year_data[["company_id", "company_name", metric, pct_col]]
        .dropna(subset=[metric])
        .sort_values(metric)
    )
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ordered[metric],
            y=ordered.company_id,
            orientation="h",
            marker_color=[
                BLUE if c == company else "#B7CCEA" for c in ordered.company_id
            ],
            name=pretty_name(metric),
            customdata=ordered[["company_name", pct_col]].to_numpy(),
            hovertemplate="<b>%{y}</b> · %{customdata[0]}<br>Giá trị: %{x:,.2f}<br>Phân vị: %{customdata[1]:.1f}%<extra></extra>",
        )
    )
    if pd.notna(median):
        fig.add_vline(
            x=float(median),
            line_dash="dash",
            line_color=AMBER,
            annotation_text="Trung vị ngành",
            annotation_position="top",
        )
    fig.update_xaxes(title_text=pretty_name(metric))
    plot(fig, height=410, legend=False)
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        section(
            "Bảng xếp hạng", "Cột giá trị có thể tăng hoặc giảm tùy bản chất chỉ tiêu"
        )
        comparison = ordered.sort_values(metric, ascending=False).copy()
        comparison.columns = ["Mã", "Doanh nghiệp", "Giá trị", "Phân vị (%)"]
        dataframe(format_table(comparison), height=355)
    with right:
        section(
            "Tín hiệu bất thường",
            "Robust anomaly dựa trên median + MAD, không sử dụng nhãn mẫu để tạo điểm",
        )
        with st.container():
            cols2 = st.columns(2)
            with cols2[0]:
                card(
                    "Anomaly Score",
                    num(current.anomaly_score, 3),
                    "Điểm bất thường",
                    AMBER,
                )
            with cols2[1]:
                card(
                    "Số dấu hiệu",
                    int(current.anomaly_count),
                    "Nhóm chỉ tiêu bất thường",
                    RED,
                )
        tags = current.anomaly_tags
        callout(
            "Các biến cần kiểm tra",
            (
                str(tags)
                if pd.notna(tags) and str(tags).strip()
                else "Không có dấu hiệu bất thường được gắn nhãn trong kỳ."
            ),
            "ROBUST ANOMALY",
        )
        st.caption(
            "Benchmark mô tả vị trí tương đối, không tự chứng minh rủi ro hoặc nguyên nhân."
        )

# ───────────────────── 4. ALERTS / EVIDENCE / REVIEW ─────────────────────
elif page == NAV_ITEMS[3]:
    section("Phân loại rủi ro & kiểm chứng", f"{company_label} · kỳ {year}")
    a, b, c, d = st.columns(4)
    with a:
        card(
            "Cấp độ rủi ro",
            SEVERITY_VI.get(current.predicted_severity, current.predicted_severity),
            "Tổng hợp tín hiệu",
            SEVERITY_COLOR.get(current.predicted_severity, SLATE),
        )
    with b:
        card(
            "Risk Score",
            num(current.risk_score, 3),
            "R = 0,88 × RuleScore + 0,12 × Anomaly",
            RED,
        )
    with c:
        card(
            "Kiểm tra phép tính",
            str(current.verification_status),
            "Independent verification",
            TEAL,
        )
    with d:
        card(
            "Confidence heuristic",
            num(current.confidence * 100, 1, "%"),
            "Không phải xác suất dự báo",
            BLUE,
        )
    st.caption(
        f"RuleScore = {int(current.activated_rule_count)}/14 = {num(current.rule_risk_score, 4)} "
        f"· Anomaly = {num(current.anomaly_score, 4)} "
        "· CRITICAL khi R ≥ 0,68 hoặc có tổ hợp khủng hoảng."
    )
    if str(current.predicted_overall_health) == "RECOVERING":
        st.success(
            f"Phục hồi: {int(current.recovery_conditions_met)}/8 điều kiện đạt. "
            "Severity = LOW; Overall Health = RECOVERING."
        )
    else:
        with st.expander(
            f"Điều kiện phục hồi: {int(current.recovery_conditions_met)}/8 đạt"
        ):
            for check in str(current.recovery_condition_checks).split(";"):
                st.write(("✅ " if check.endswith("=1") else "⬜ ") + check)
    callout("Kết luận có căn cứ", current.gold_explanation, "EXECUTIVE EXPLANATION")
    if (
        str(current.escalation_reason).strip()
        and str(current.escalation_reason).lower() != "nan"
    ):
        st.markdown(
            f'<div class="rule-box"><b>Nguyên nhân nâng mức ưu tiên:</b> '
            f"{escape(str(current.escalation_reason))}</div>",
            unsafe_allow_html=True,
        )

    left, right = st.columns([1.6, 1], gap="large")
    selected = details[
        (details.company_id == company) & (details.fiscal_year == year)
    ].copy()
    with left:
        section(
            f"Chi tiết {len(selected)} luật cảnh báo",
            "Mở từng cảnh báo để xem lý do, chỉ tiêu và nguồn dữ liệu gốc",
        )
        if selected.empty:
            st.success("Không có luật cảnh báo bất lợi vượt ngưỡng cho kỳ này.")
        else:
            selected = selected.sort_values("rule_id")
            for r in selected.itertuples(index=False):
                with st.expander(f"⚑  {r.rule_id}   ·   Đóng góp 1/14"):
                    st.markdown(f"**Lý do:** {r.reason}")
                    st.caption("CHỈ TIÊU TÍNH TOÁN")
                    st.code(str(r.evidence_metrics), language="text")
                    st.caption("TRUY VẾT FILE / TRƯỜNG / DOANH NGHIỆP / NĂM / GIÁ TRỊ")
                    st.code(str(r.evidence_fields), language="text")
    with right:
        section(
            "Độ tin cậy của bằng chứng",
            "Chỉ nhận xét sau bước Verify và kiểm tra evidence",
        )
        card(
            "Bằng chứng đầy đủ",
            "CÓ" if bool(current.evidence_complete) else "CHƯA",
            "Evidence completeness",
            TEAL if bool(current.evidence_complete) else RED,
        )
        st.caption(f"Số phép kiểm tra độc lập: {int(current.verification_checks)}")
        if str(current.verification_status) == "PASS":
            st.success("Independent verification: PASS")
        else:
            st.error("Có phép kiểm tra không đạt. Cần xem kết quả chi tiết.")
        section(
            "Human-in-the-loop",
            "Phê duyệt hoặc yêu cầu kiểm tra lại kết luận của hệ thống",
        )
        with st.form("review_form", clear_on_submit=False):
            decision = st.selectbox(
                "Quyết định",
                ["NEEDS_REVIEW", "ACCEPT", "REJECT"],
                format_func=lambda x: {
                    "ACCEPT": "Chấp nhận",
                    "REJECT": "Bác bỏ",
                    "NEEDS_REVIEW": "Cần xem xét thêm",
                }[x],
            )
            reviewer = st.text_input(
                "Người đánh giá", placeholder="Tên người phụ trách"
            )
            comment = st.text_area(
                "Ghi chú", placeholder="Căn cứ / hành động tiếp theo", height=90
            )
            submitted = st.form_submit_button(
                "Lưu kết quả đánh giá", type="primary", use_container_width=True
            )
        if submitted:
            if not reviewer.strip():
                st.warning("Vui lòng nhập tên người đánh giá trước khi lưu.")
            else:
                try:
                    save_review(company, int(year), decision, reviewer.strip(), comment)
                    st.success("Đã ghi nhận đánh giá và lưu vào audit review.")
                except Exception as exc:
                    st.error(f"Không lưu được review: {exc}")
    reviews = load_reviews()
    if not reviews.empty:
        subset = reviews[
            (reviews.company_id == company) & (reviews.fiscal_year == year)
        ]
        with st.expander(f"Lịch sử đánh giá · {len(subset)} mục"):
            if subset.empty:
                st.info("Chưa có đánh giá thủ công cho doanh nghiệp và kỳ này.")
            else:
                dataframe(subset.sort_values("reviewed_at_utc", ascending=False))

# ───────────────────── 5. DECISION LAB ─────────────────────
elif page == NAV_ITEMS[4]:
    sim_tab, helper_tab = st.tabs(["What-if Scenario", "Financial Analyst Assistant"])
    with sim_tab:
        section(
            "Điều chỉnh các giả định",
            "Các thanh trượt thay đổi dữ liệu của doanh nghiệp đã chọn; không ghi đè dữ liệu BTC",
        )
        l, r, c = st.columns(3)
        with l:
            revenue_pct = st.slider("Doanh thu (%)", -30, 30, 0, key="sim_rev")
        with r:
            cogs_pct = st.slider("Giá vốn hàng bán (%)", -30, 30, 0, key="sim_cogs")
        with c:
            cfo_pct = st.slider("Dòng tiền CFO (%)", -60, 60, 0, key="sim_cfo")
        with st.expander("Các giả định nâng cao · phải thu, tồn kho, nợ vay, lãi vay"):
            t1, t2 = st.columns(2)
            with t1:
                ar_pct = st.slider("Phải thu (%)", -40, 60, 0, key="sim_ar")
                inv_pct = st.slider("Tồn kho (%)", -40, 60, 0, key="sim_inv")
                std_pct = st.slider("Nợ ngắn hạn (%)", -40, 60, 0, key="sim_std")
            with t2:
                ltd_pct = st.slider("Nợ dài hạn (%)", -40, 60, 0, key="sim_ltd")
                int_pct = st.slider(
                    "Chi phí lãi vay (%)", -40, 60, 0, key="sim_interest"
                )
        scenario = scenario_metrics(
            current,
            {
                "revenue_pct": revenue_pct,
                "cogs_pct": cogs_pct,
                "cfo_pct": cfo_pct,
                "accounts_receivable_pct": ar_pct,
                "inventory_pct": inv_pct,
                "short_term_debt_pct": std_pct,
                "long_term_debt_pct": ltd_pct,
                "interest_expense_pct": int_pct,
            },
        )
        compare_fields = [
            ("Biên lợi nhuận gộp (%)", "gross_margin_pct"),
            ("Biên lợi nhuận HĐKD (%)", "operating_margin_pct"),
            ("Biên lợi nhuận ròng (%)", "net_margin_pct"),
            ("Nợ / Tổng tài sản (%)", "debt_to_assets_pct"),
            ("Khả năng trả lãi (lần)", "interest_coverage_x"),
            ("CFO / Lợi nhuận (lần)", "cfo_to_net_income_x"),
            ("FCF (triệu VND)", "free_cash_flow_vnd_mn"),
        ]
        compare = pd.DataFrame(
            [
                {"Chỉ tiêu": label, "Gốc": current[key], "Mô phỏng": scenario[key]}
                for label, key in compare_fields
            ]
        )
        compare["Thay đổi"] = compare["Mô phỏng"] - compare["Gốc"]
        section(
            "Tác động lên các chỉ tiêu",
            "So sánh trước / sau trên cùng một bộ công thức mô phỏng",
        )
        left, right = st.columns([1.55, 1], gap="large")
        with left:
            dataframe(format_table(compare), height=335)
        with right:
            card(
                "Scenario risk proxy",
                num(scenario["scenario_risk_proxy"], 3),
                "Proxy 7 tín hiệu / 14 · không so trực tiếp với Risk Score Gold",
                AMBER,
            )
            focus = compare.head(4).melt(
                id_vars="Chỉ tiêu",
                value_vars=["Gốc", "Mô phỏng"],
                var_name="Kịch bản",
                value_name="Giá trị",
            )
            fig = px.bar(
                focus,
                x="Chỉ tiêu",
                y="Giá trị",
                color="Kịch bản",
                barmode="group",
                color_discrete_map={"Gốc": "#B6C8E6", "Mô phỏng": BLUE},
            )
            fig.update_xaxes(tickangle=-24)
            plot(fig, height=280)
        st.info(
            "**Lưu ý:** Scenario risk proxy dùng luật rút gọn để so sánh chiều hướng tác động; "
            "không phải dự báo xác suất và không thay thế pipeline Gold hoàn chỉnh."
        )

    with helper_tab:
        section(
            "Hỏi đáp dữ liệu tài chính",
            "Hai chức năng riêng: hỏi tự do và bộ 30 câu Numerical QA công khai",
        )
        st.info(
            "**Lưu ý cách đọc KPI:** Numerical QA Accuracy 100% = đúng 30/30 câu mẫu BTC bằng bộ tính toán QA. "
            "Chỉ số này **không đo** khả năng hiểu mọi câu hỏi tự do của trợ lý dựa trên luật."
        )
        ask_tab, sample_tab = st.tabs(["Hỏi tự do (rule-based)", "30 câu QA mẫu BTC"])
        with ask_tab:
            st.caption(
                "Trợ lý không sử dụng LLM/API. Phản hồi ngoài phạm vi sẽ được đánh dấu 'Chưa hỗ trợ' thay vì suy đoán."
            )
            suggested_questions = [
                f"CFO của {company} năm {year} là bao nhiêu triệu VND?",
                "CFO (lưu chuyển tiền thuần từ hoạt động kinh doanh) của C007 năm 2025 là bao nhiêu triệu VND?",
                f"doanh thu {company} {year}",
                f"Current Ratio của {company} năm {year} là bao nhiêu?",
                f"giải thích rủi ro {company} {year}",
                f"so sánh {company} {year} với ngành",
                f"top 5 rủi ro {year}",
            ]
            chosen_example = st.selectbox(
                "Gợi ý câu hỏi", suggested_questions, key="assistant_example"
            )
            with st.form("analyst_form"):
                question = st.text_input(
                    "Câu hỏi phân tích",
                    value=chosen_example,
                    placeholder="Ví dụ: CFO của C007 năm 2025 là bao nhiêu?",
                )
                ask = st.form_submit_button("Phân tích câu hỏi", type="primary")
            if ask:
                if question.strip():
                    try:
                        st.session_state["answer_payload"] = answer_user_query(
                            question.strip(), analysis
                        )
                        st.session_state["answer_question"] = question.strip()
                    except Exception as exc:
                        st.error(f"Không phân tích được câu hỏi: {exc}")
                else:
                    st.warning("Vui lòng nhập câu hỏi.")
            if "answer_payload" in st.session_state:
                answer = st.session_state["answer_payload"]
                section("Kết quả trả lời")
                st.caption(f"Câu hỏi: {st.session_state.get('answer_question', '')}")
                if answer.get("status") == "unsupported":
                    st.warning(
                        "**Chưa hỗ trợ / không đủ dữ liệu:** "
                        + str(answer.get("answer", ""))
                    )
                    st.caption(
                        "Không có đáp án, bằng chứng hay confidence hợp lệ cho yêu cầu này."
                    )
                else:
                    callout(
                        "Phân tích của hệ thống",
                        str(answer.get("answer", "")),
                        "RULE-BASED ASSISTANT",
                    )
                    confidence = float(answer.get("confidence") or 0)
                    st.progress(
                        max(0.0, min(confidence, 1.0)),
                        text=f"Confidence heuristic: {confidence:.0%}",
                    )
                    with st.expander("Bằng chứng đi kèm", expanded=True):
                        st.code(
                            str(
                                answer.get("evidence") or "Không có bằng chứng phù hợp"
                            ),
                            language="text",
                        )
                    st.caption(
                        "Confidence chỉ là điểm heuristic cho câu trả lời được hỗ trợ, "
                        "không phải xác suất thống kê được hiệu chuẩn."
                    )
        with sample_tab:
            st.caption(
                "Đây là đúng bộ 30 câu hỏi công khai đã dùng để tính Numerical QA Accuracy; "
                "kết quả tính từ pipeline, không đọc answer key để trả lời."
            )
            questions_sample = pd.read_csv(
                SAMPLES / "questions_sample.csv", encoding="utf-8-sig"
            )
            question_lookup = questions_sample.set_index("question_id")
            selected_id = st.selectbox(
                "Chọn câu hỏi BTC",
                questions_sample["question_id"].tolist(),
                format_func=lambda qid: f"{qid} · {question_lookup.loc[qid, 'question_text_vi']}",
                index=1,
                key="qa_sample_choice",
            )
            qa_hit = out["qa"].loc[out["qa"].question_id == selected_id]
            if qa_hit.empty:
                st.error("Chưa tìm thấy câu hỏi trong kết quả chạy pipeline.")
            else:
                qa_response = qa_hit.iloc[0]
                question_meta = question_lookup.loc[selected_id]
                answer_text = str(qa_response["answer"]).strip()
                if not answer_text:
                    st.warning("Bộ Numerical QA chưa trả lời được câu này.")
                else:
                    answer_type = str(question_meta["expected_answer_type"])
                    units = {
                        "numeric_vnd_mn": "triệu VND",
                        "numeric_percentage": "%",
                        "numeric_ratio": "lần",
                        "numeric_days": "ngày",
                    }
                    unit = units.get(answer_type, "")
                    callout(
                        "Đáp án từ bộ Numerical QA",
                        f"{answer_text} {unit}".strip(),
                        f"{selected_id} · {question_meta['question_type']}",
                    )
                    st.write(
                        "**Phương pháp / diễn giải:**", str(qa_response["explanation"])
                    )
                    source_files = str(
                        qa_response.get("evidence_source_files", "")
                    ).strip()
                    if not source_files or source_files.lower() == "nan":
                        source_files = str(question_meta["source_files"])
                    st.code(
                        f"File nguồn: {source_files}\nTrường nguồn: {qa_response['evidence_source_fields']}\n"
                        f"Doanh nghiệp: {question_meta['target_company_id']}\nNăm: {question_meta['target_fiscal_year']}",
                        language="text",
                    )
                    st.caption(
                        "Đáp án thuộc 30 câu hỏi mẫu công khai. Độ chính xác trên dữ liệu ẩn và "
                        "câu hỏi tự do cần được đánh giá riêng."
                    )

# ───────────────────── 6. QA, AUDIT, EXPORT ─────────────────────
elif page == NAV_ITEMS[5]:
    validation_pass = out["validation"].get("status") == "PASS"
    if validation_pass:
        st.success(
            "Data Validation: PASS · Dữ liệu, khóa liên kết và đối chiếu theo quy trình hiện tại đạt."
        )
    else:
        st.error(
            "Data Validation: FAIL · Cần xem báo cáo validation trước khi sử dụng."
        )
    cols = st.columns(4)
    with cols[0]:
        card(
            "Calculation Accuracy",
            num(kpi.get("calculation_accuracy", 0) * 100, 2, "%"),
            f"{kpi.get('metric_correct',0)}/{kpi.get('metric_tested',0)} chỉ tiêu",
            TEAL,
        )
    with cols[1]:
        card(
            "Numerical QA · 30 câu mẫu BTC",
            num(kpi.get("numerical_qa_accuracy", 0) * 100, 1, "%"),
            f"{kpi.get('qa_correct',0)}/{kpi.get('qa_tested',0)} câu mẫu · không đo hỏi tự do",
            BLUE,
        )
    with cols[2]:
        card(
            "High/Critical Recall",
            num(kpi.get("high_risk_recall", 0) * 100, 2, "%"),
            "Trên 18 nhãn mẫu công khai",
            AMBER,
        )
    with cols[3]:
        card(
            "Evidence Traceability",
            num(kpi.get("evidence_traceability_rate", 0) * 100, 1, "%"),
            "Truy vết bằng chứng nguồn",
            TEAL,
        )
    st.warning(
        "KPI mẫu chỉ phản ánh hiệu quả trên các mẫu công khai; không đại diện cho hiệu quả trên dữ liệu ẩn. "
        "Numerical QA Accuracy không phản ánh độ chính xác của trợ lý hỏi tự do. "
        "Confidence cũng không phải xác suất được hiệu chuẩn."
    )
    quality_tab, audit_tab, export_tab = st.tabs(
        ["Verification & KPI", "Audit trail", "↓ Tải dữ liệu"]
    )
    with quality_tab:
        section(
            "Independent Verification",
            "Đối chiếu 6 công thức lõi theo từng company-year",
        )
        verification = out["verification"]
        vcol1, vcol2 = st.columns(2)
        with vcol1:
            card(
                "Bản ghi kiểm tra đạt",
                f"{int((verification.verification_status == 'PASS').sum())}/{len(verification)}",
                "Trên 60 company-year",
                TEAL,
            )
        with vcol2:
            card(
                "Thời gian xử lý pipeline",
                num(kpi.get("pipeline_runtime_ms"), 1, " ms"),
                "Thời gian nội bộ theo run",
                BLUE,
            )
        dataframe(verification, height=320)
        with st.expander("Báo cáo KPI đầy đủ"):
            st.json(kpi)
        with st.expander("Báo cáo kiểm tra dữ liệu đầu vào"):
            st.json(out["validation"])
    with audit_tab:
        section(
            "Audit Trail", "Các bước xử lý và dấu vết đầu vào được ghi nhận theo run"
        )
        dataframe(out["audit"], height=375)
        st.caption(f"Run ID: {kpi['run_id']}")
        st.caption(f"Input fingerprint (SHA-256): {kpi['input_fingerprint']}")
        st.caption("Việc tải dữ liệu không thay đổi lịch sử audit của pipeline.")
    with export_tab:
        section(
            "Tải kết quả phục vụ hồ sơ / demo",
            "Dữ liệu giữ đúng định dạng cột CSV và mã hóa UTF-8-SIG để mở bằng Excel",
        )
        export_items = [
            (
                "Đầu ra theo biểu mẫu BTC",
                "submission_output_Case3.csv",
                out["submission"],
            ),
            ("Đáp án Numerical QA", "qa_submission_Case3.csv", out["qa"]),
            ("Dữ liệu phân tích đầy đủ", "analysis_full_gold.csv", analysis),
            ("Chi tiết luật cảnh báo", "alerts_detail_gold.csv", details),
            ("Kết quả verification", "verification_detail.csv", out["verification"]),
            ("Audit trail", "audit_trail.csv", out["audit"]),
        ]
        for i in range(0, len(export_items), 2):
            c1, c2 = st.columns(2)
            for col, item in zip((c1, c2), export_items[i : i + 2]):
                title, name, frame = item
                with col:
                    st.download_button(
                        f"↓ {title}",
                        data=frame.to_csv(index=False).encode("utf-8-sig"),
                        file_name=name,
                        mime="text/csv",
                        use_container_width=True,
                        key=f"export_{name}",
                    )
        st.caption(
            "Bảng đầu ra BTC và QA chỉ sử dụng dữ liệu thực sự được tính từ Data Pack giả lập."
        )

st.markdown(
    '<div class="footer-note">FINREPORT INTELLIGENCE · Festival Chuyển đổi số 2026 · Bảng C · '
    "Dữ liệu của BTC là giả lập. Hệ thống chỉ hỗ trợ phân tích; không phải kết luận kiểm toán, "
    "kết luận gian lận hoặc khuyến nghị đầu tư.</div>",
    unsafe_allow_html=True,
)
