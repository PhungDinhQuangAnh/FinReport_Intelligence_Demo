"""Independent validation against public reference samples (not used to make predictions)."""
from __future__ import annotations
import math
import pandas as pd
from .config import KEY, SAMPLES, RAW
from .metrics import METRICS_SAMPLE_COLS


def evaluate_metrics(metrics: pd.DataFrame, samples=None) -> dict:
    if samples is None:
        samples = pd.read_csv(SAMPLES / "financial_metrics_sample.csv", encoding="utf-8-sig")
    compared = metrics.merge(samples, on=KEY, how="inner", suffixes=("_actual", "_sample"), validate="one_to_one")
    total = correct = 0
    wrong = []
    for _, r in compared.iterrows():
        for m in METRICS_SAMPLE_COLS:
            exp = r[f"{m}_sample"]
            act = r[f"{m}_actual"]
            if pd.isna(exp):
                continue
            # Sample is rounded to different precisions. Compare against the last quoted decimal digit.
            raw_sample = samples.loc[(samples.company_id == r.company_id) & (samples.fiscal_year == r.fiscal_year), m]
            precision = 0 if float(exp).is_integer() and m.endswith("_vnd_mn") else (
                3 if m in {"current_ratio_x", "quick_ratio_x", "debt_to_equity_x", "cfo_to_net_income_x", "interest_coverage_x"} else
                1 if m in {"dso_days", "inventory_days", "dpo_days"} else 2)
            tolerance = (0.5 * (10 ** -precision)) + 1e-7
            total += 1
            if pd.notna(act) and abs(float(act) - float(exp)) <= tolerance:
                correct += 1
            else:
                wrong.append({"company_id": r.company_id, "fiscal_year": int(r.fiscal_year), "metric": m,
                    "actual": None if pd.isna(act) else float(act), "reference": float(exp), "tolerance": tolerance})
    return {"metric_tested": total, "metric_correct": correct,
        "calculation_accuracy": round(correct / total, 6) if total else None,
        "metric_mismatches": wrong}


def evaluate_qa(qa: pd.DataFrame, answers=None) -> dict:
    if answers is None:
        answers = pd.read_csv(SAMPLES / "answer_key_sample.csv", encoding="utf-8-sig", dtype={"normalized_answer": str})
    d = answers.merge(qa, on="question_id", validate="one_to_one")
    wrong = []
    for row in d.itertuples(index=False):
        prediction = str(row.answer).strip()
        expectation = str(row.normalized_answer).strip()
        try:
            actual_num, expected_num = float(prediction), float(expectation)
            tol = float(row.numeric_tolerance) if pd.notna(row.numeric_tolerance) else 0.
            ok = math.isclose(actual_num, expected_num, rel_tol=0, abs_tol=max(tol, 1e-6))
        except (ValueError, TypeError):
            ok = prediction.upper() == expectation.upper()
        if not ok:
            wrong.append({"question_id": row.question_id, "actual": prediction, "reference": expectation})
    return {"qa_tested": len(d), "qa_correct": len(d) - len(wrong),
        "numerical_qa_accuracy": round((len(d) - len(wrong)) / len(d), 6) if len(d) else None,
        "qa_mismatches": wrong}


def evaluate_alert_severity(alerts: pd.DataFrame, samples=None) -> dict:
    """An illustrative public-sample HIGH/CRITICAL binary check, not universal alert accuracy."""
    if samples is None:
        samples = pd.read_csv(SAMPLES / "financial_scenarios_sample.csv", encoding="utf-8-sig")
    merged = samples.merge(alerts, on=KEY, validate="one_to_one")
    truth = merged.severity.isin(["HIGH", "CRITICAL"])
    pred = merged.predicted_severity.isin(["HIGH", "CRITICAL"])
    tp, fp, fn = int((truth & pred).sum()), int((~truth & pred).sum()), int((truth & ~pred).sum())
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and (precision + recall) else None
    return {"alert_public_samples": len(merged), "alert_tp": tp, "alert_fp": fp, "alert_fn": fn,
        "high_risk_precision": round(precision, 4) if precision is not None else None,
        "high_risk_recall": round(recall, 4) if recall is not None else None,
        "high_risk_f1": round(f1, 4) if f1 is not None else None,
        "note": "Đo riêng nhãn HIGH/CRITICAL trên 18 mẫu công khai; không đại diện ground truth toàn bộ, không được dùng để huấn luyện ngưỡng."}


def verify_evidence_references(details: pd.DataFrame) -> dict:
    """Verify each rule-evidence pointer resolves to a real row, field and rounded value."""
    references = {}
    for path in sorted(RAW.glob("*.csv")):
        df = pd.read_csv(path, encoding="utf-8-sig")
        if "fiscal_year" in df.columns:
            references[path.name] = df.set_index(KEY)
    total = correct = 0
    invalid = []
    for record in details.itertuples(index=False):
        for raw in str(record.evidence_fields).split(";"):
            if not raw:
                continue
            total += 1
            try:
                lhs, rhs = raw.split("=", 1)
                file_name, field, company, year = lhs.split(":")
                tab = references[file_name]
                value = float(tab.loc[(company, int(year)), field])
                expected = float(rhs.replace(",", ""))
                ok = abs(value - expected) <= 0.00501
            except (ValueError, KeyError, TypeError):
                ok = False
            if ok:
                correct += 1
            else:
                invalid.append(raw)
    return {"evidence_reference_count": total, "evidence_references_verified": correct,
            "evidence_traceability_rate": round(correct / total, 6) if total else None,
            "evidence_invalid": invalid}


def evaluate_public_severity_matrix(alerts: pd.DataFrame, samples=None) -> dict:
    """Extra Gold diagnostic: exact 4-level severity match on public samples.

    Public labels are used only after prediction, never inside alert/anomaly modules.
    """
    if samples is None:
        samples = pd.read_csv(SAMPLES / "financial_scenarios_sample.csv", encoding="utf-8-sig")
    merged = samples.merge(alerts[KEY + ["predicted_severity", "predicted_primary_scenario"]], on=KEY, validate="one_to_one")
    merged["severity_match"] = merged["severity"].astype(str) == merged["predicted_severity"].astype(str)
    return {
        "severity_exact_correct": int(merged.severity_match.sum()),
        "severity_exact_tested": int(len(merged)),
        "severity_exact_accuracy": round(float(merged.severity_match.mean()), 6) if len(merged) else None,
        "severity_mismatches": merged.loc[~merged.severity_match, KEY + ["severity", "predicted_severity", "primary_scenario", "predicted_primary_scenario"]].to_dict("records"),
    }
