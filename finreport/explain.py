"""Generate concise, evidence-grounded explanations from deterministic outputs."""
from __future__ import annotations
import pandas as pd


def _fmt(v, digits=2):
    if pd.isna(v):
        return "N/A"
    return f"{float(v):,.{digits}f}"


def explain_row(row: pd.Series) -> str:
    parts = []
    sev = str(row.get("predicted_severity", "LOW"))
    score = row.get("risk_score", 0)
    health = row.get("financial_health_score", float("nan"))
    parts.append(f"Mức cảnh báo {sev}, risk score {_fmt(score, 2)}, health score {_fmt(health, 1)}/100.")
    tags = [x for x in str(row.get("alert_tags", "")).split(";") if x]
    if tags:
        parts.append("Tín hiệu chính: " + ", ".join(tags[:4]) + ".")
    anomaly = str(row.get("anomaly_tags", ""))
    if anomaly:
        top = ", ".join(x.split(":")[0] for x in anomaly.split(";")[:3])
        parts.append("So với doanh nghiệp cùng ngành/cùng năm, bất thường đáng chú ý nằm ở: " + top + ".")
    if pd.notna(row.get("cfo_to_net_income_x")):
        parts.append(f"CFO/Net Income = {_fmt(row.get('cfo_to_net_income_x'))} lần; DSO = {_fmt(row.get('dso_days'))} ngày; tồn kho = {_fmt(row.get('inventory_days'))} ngày.")
    return " ".join(parts)


def add_explanations(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["gold_explanation"] = d.apply(explain_row, axis=1)
    return d
