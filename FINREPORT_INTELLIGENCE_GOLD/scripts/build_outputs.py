from finreport.pipeline import build

if __name__ == "__main__":
    result = build(save=True)
    k = result["kpi"]
    print("FINREPORT_INTELLIGENCE_Gold build complete")
    print(f"Records: {k['records']}")
    print(f"Calculation Accuracy: {k['metric_correct']}/{k['metric_tested']} = {k['calculation_accuracy']:.2%}")
    print(f"Numerical QA: {k['qa_correct']}/{k['qa_tested']} = {k['numerical_qa_accuracy']:.2%}")
    print(f"High/Critical Recall: {k['high_risk_recall']:.2%}")
    print(f"Evidence Traceability: {k['evidence_traceability_rate']:.2%}")
    print(f"Verification: {k['calculation_verification_pass']}/{k['calculation_verification_total']}")
    print(f"Run ID: {k['run_id']}")
