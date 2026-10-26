"""One-command acceptance check for the Gold MVP."""
from finreport.pipeline import build

if __name__ == "__main__":
    r = build(save=False)
    k = r["kpi"]
    checks = {
        "Data validation": r["validation"]["status"] == "PASS",
        "Calculation accuracy >= 95%": k["calculation_accuracy"] >= 0.95,
        "Numerical QA >= 85%": k["numerical_qa_accuracy"] >= 0.85,
        "Independent verification = 100%": k["calculation_verification_rate"] == 1.0,
        "Evidence traceability = 100%": k["evidence_traceability_rate"] == 1.0,
        "Public high-risk recall >= 75%": k["high_risk_recall"] >= 0.75,
        "60 company-year": k["records"] == 60,
    }
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not all(checks.values()):
        raise SystemExit(1)
    print(f"Gold acceptance PASS · run_id={k['run_id']}")
