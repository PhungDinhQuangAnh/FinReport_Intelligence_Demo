"""Gold orchestration: Load → Validate → Calculate → Benchmark/Anomaly → Alert → Verify → Explain → QA → Audit."""
from __future__ import annotations
import json
import time
from pathlib import Path
import pandas as pd
from .config import OUTPUTS, TEMPLATES, KEY
from .data import load_validated
from .metrics import calculate_metrics
from .benchmark import add_benchmarks
from .anomaly import add_anomaly_scores
from .health import add_health_scores
from .alerts import detect_alerts
from .verification import verify_calculations, verify_alert_evidence
from .explain import add_explanations
from .qa import answer_questions
from .evaluation import (evaluate_metrics, evaluate_qa, evaluate_alert_severity,
                         verify_evidence_references, evaluate_public_severity_matrix)
from .audit import make_audit_log, write_jsonl, run_id, input_fingerprint


def build(save: bool = True, output_dir: Path = OUTPUTS) -> dict:
    t0 = time.perf_counter()
    source, validation = load_validated()
    metrics = calculate_metrics(source)
    benchmark = add_benchmarks(metrics)
    enriched = add_anomaly_scores(benchmark)
    enriched = add_health_scores(enriched)

    alerts, details = detect_alerts(enriched)
    analysis = enriched.merge(alerts, on=KEY, how="left", validate="one_to_one", suffixes=("", "_alert"))
    if "anomaly_score_alert" in analysis:
        analysis = analysis.drop(columns=["anomaly_score_alert"])

    # Gold Verify phase: independently recompute core formulas before explanation.
    verification = verify_calculations(analysis)
    evidence_verification = verify_alert_evidence(details)
    analysis = analysis.merge(verification, on=KEY, how="left", validate="one_to_one")
    analysis = analysis.merge(evidence_verification, on=KEY, how="left", validate="one_to_one")
    analysis["evidence_complete"] = analysis["evidence_complete"].where(analysis["evidence_complete"].notna(), True).astype(bool)
    analysis["evidence_issue_count"] = analysis["evidence_issue_count"].fillna(0).astype(int)
    analysis["confidence"] = (analysis["confidence"] * analysis["verification_score"] * analysis["evidence_complete"].map({True: 1.0, False: 0.75})).clip(0, 0.99).round(3)
    analysis = add_explanations(analysis)

    qa = answer_questions(metrics)
    evaluation = {
        **evaluate_metrics(metrics),
        **evaluate_qa(qa),
        **evaluate_alert_severity(alerts),
        **evaluate_public_severity_matrix(alerts),
        **verify_evidence_references(details),
        "calculation_verification_pass": int((verification.verification_status == "PASS").sum()),
        "calculation_verification_total": int(len(verification)),
        "calculation_verification_rate": round(float((verification.verification_status == "PASS").mean()), 6),
        "alert_evidence_complete_records": int(analysis.evidence_complete.sum()),
        "alert_evidence_records": int(len(analysis)),
        "alerts_triggered": int(len(details)),
        "records": int(len(analysis)),
        "run_id": run_id(),
        "input_fingerprint": input_fingerprint(),
        "pipeline_runtime_ms": round((time.perf_counter() - t0) * 1000, 3),
    }

    template = pd.read_csv(TEMPLATES / "submission_output_template_Case3.csv")
    cols = template.columns.tolist()
    missing_cols = set(cols) - set(analysis.columns)
    if missing_cols:
        raise ValueError(f"Thiếu cột mẫu BTC: {missing_cols}")
    submission = analysis[cols].copy()
    qa_cols = pd.read_csv(TEMPLATES / "qa_submission_template_Case3.csv").columns.tolist()
    qa_submission = qa[qa_cols].copy()

    audit = make_audit_log({
        "LOAD_VALIDATE": len(source),
        "CALCULATE": len(metrics),
        "BENCHMARK_ANOMALY": len(enriched),
        "ALERT": len(alerts),
        "VERIFY": len(verification),
        "EXPLAIN": len(analysis),
        "QA": len(qa),
    }, {"records": len(analysis), "status": validation["status"]})

    if save:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        analysis.to_csv(output_dir / "analysis_full_gold.csv", index=False, encoding="utf-8-sig", float_format="%.6f")
        metrics[KEY + [c for c in metrics.columns if c.endswith("_pct") or c.endswith("_days") or c.endswith("_x") or c.endswith("_vnd_mn")]].to_csv(
            output_dir / "financial_metrics_gold.csv", index=False, encoding="utf-8-sig", float_format="%.6f")
        details.to_csv(output_dir / "alerts_detail_gold.csv", index=False, encoding="utf-8-sig")
        verification.to_csv(output_dir / "verification_detail.csv", index=False, encoding="utf-8-sig")
        audit.to_csv(output_dir / "audit_trail.csv", index=False, encoding="utf-8-sig")
        write_jsonl(audit, output_dir / "audit_trail.jsonl")
        submission.to_csv(output_dir / "submission_output_Case3.csv", index=False, encoding="utf-8-sig", float_format="%.6f")
        qa_submission.to_csv(output_dir / "qa_submission_Case3.csv", index=False, encoding="utf-8-sig")
        (output_dir / "validation_report.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / "kpi_report_gold.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
        review_path = output_dir / "human_reviews.csv"
        if not review_path.exists():
            pd.DataFrame(columns=["company_id","fiscal_year","decision","reviewer","comment","reviewed_at_utc"]).to_csv(review_path, index=False, encoding="utf-8-sig")
    return {
        "analysis": analysis, "metrics": metrics, "alerts": alerts, "alerts_detail": details,
        "verification": verification, "audit": audit, "submission": submission,
        "qa": qa, "validation": validation, "kpi": evaluation,
    }
