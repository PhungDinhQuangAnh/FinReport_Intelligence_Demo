from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from finreport.config import TEMPLATES, OUTPUTS
from finreport.pipeline import build
from finreport.data import load_validated, load_sources, validate_sources
from finreport.scenario import scenario_metrics
from finreport.assistant import answer_user_query
from finreport.audit import run_id, input_fingerprint
from finreport.review import save_review, load_reviews


@pytest.fixture(scope="module")
def context():
    return build(save=False)


def test_source_integrity():
    data, report = load_validated()
    assert report["status"] == "PASS"
    assert len(data) == 60
    assert data.company_id.nunique() == 12
    assert data.fiscal_year.nunique() == 5
    assert report["checks"]["manifest_files_verified"] == 5


def test_validation_detects_corruption():
    tables = load_sources()
    tables["balance_sheet"].loc[0, "total_assets_vnd_mn"] += 1
    report = validate_sources(tables, check_manifest=False)
    assert report["status"] == "FAIL"


def test_calculation_accuracy_and_qa(context):
    k = context["kpi"]
    assert k["calculation_accuracy"] >= 0.95
    assert k["numerical_qa_accuracy"] >= 0.85
    assert k["qa_correct"] == 30


def test_2021_not_imputed(context):
    d = context["metrics"].query("fiscal_year == 2021")
    for col in ["revenue_growth_pct","roa_pct","roe_pct","dso_days","inventory_days","dpo_days","total_debt_growth_pct"]:
        assert d[col].isna().all(), col


def test_gold_verification_before_explain(context):
    v = context["verification"]
    assert len(v) == 60
    assert (v.verification_status == "PASS").all()
    a = context["analysis"]
    assert a.gold_explanation.notna().all()
    assert (a.verification_score == 1.0).all()


def test_health_and_anomaly_ranges(context):
    a = context["analysis"]
    assert a.financial_health_score.dropna().between(0, 100).all()
    assert a.anomaly_score.between(0, 1).all()
    assert a.risk_score.between(0, 1).all()


def test_peer_benchmark_same_year(context):
    a = context["analysis"]
    for year, subset in a.groupby("fiscal_year"):
        assert len(subset) == 12
        assert np.allclose(subset.peer_median__gross_margin_pct, subset.gross_margin_pct.median())


def test_alert_traceability_and_public_recall(context):
    k = context["kpi"]
    assert k["evidence_traceability_rate"] == 1.0
    assert k["calculation_verification_rate"] == 1.0
    assert k["high_risk_recall"] >= 0.75
    detail = context["alerts_detail"]
    assert detail.evidence_fields.astype(str).str.contains(".csv:", regex=False).all()


def test_expected_demo_cases(context):
    a = context["analysis"].set_index(["company_id","fiscal_year"])
    assert a.loc[("C007", 2025), "predicted_severity"] == "CRITICAL"
    assert a.loc[("C010", 2025), "predicted_severity"] == "LOW"
    assert a.loc[("C007", 2025), "confidence"] > 0.7


def test_scenario_engine_changes_metrics(context):
    base = context["analysis"].set_index(["company_id","fiscal_year"]).loc[("C007",2025)]
    improved = scenario_metrics(base, {"cfo_pct": -60, "accounts_receivable_pct": -20, "inventory_pct": -15})
    stressed = scenario_metrics(base, {"cfo_pct": 40, "interest_expense_pct": 30, "short_term_debt_pct": 25})
    assert improved["cfo_vnd_mn"] > base.cfo_vnd_mn
    assert stressed["debt_to_assets_pct"] > base.debt_to_assets_pct
    assert 0 <= improved["scenario_risk_proxy"] <= 1
    assert 0 <= stressed["scenario_risk_proxy"] <= 1


def test_assistant_grounded(context):
    ans = answer_user_query("giải thích rủi ro C007 2025", context["analysis"])
    assert "CRITICAL" in ans["answer"]
    assert "csv" in ans["evidence"]
    assert ans["confidence"] > 0.5
    top = answer_user_query("top 3 rủi ro 2025", context["analysis"])
    assert "Top 3" in top["answer"]


def test_audit_identifiers_are_stable():
    assert len(run_id()) == 16
    assert len(input_fingerprint()) == 64
    assert run_id() == run_id()


def test_output_schema(context):
    expected = pd.read_csv(TEMPLATES / "submission_output_template_Case3.csv").columns.tolist()
    assert context["submission"].columns.tolist() == expected
    qexpected = pd.read_csv(TEMPLATES / "qa_submission_template_Case3.csv").columns.tolist()
    assert context["qa"].columns.tolist() == qexpected


def test_human_review_roundtrip(tmp_path):
    p = tmp_path / "reviews.csv"
    rec = save_review("C007", 2025, "NEEDS_REVIEW", "tester", "check cash flow", p)
    assert rec["decision"] == "NEEDS_REVIEW"
    loaded = load_reviews(p)
    assert len(loaded) == 1
    assert loaded.iloc[0].company_id == "C007"


def test_free_form_cfo_matches_public_numerical_qa_q002(context):
    """Regression: public Q002 was correct in QA but unsupported in chat UI."""
    question = ("CFO (lưu chuyển tiền thuần từ hoạt động kinh doanh) "
                "của C007 năm 2025 là bao nhiêu triệu VND?")
    answer = answer_user_query(question, context["analysis"])
    reference = context["qa"].set_index("question_id").loc["Q002", "answer"]
    assert answer["status"] == "answered"
    assert float(reference) == -20564
    assert "-20.564" in answer["answer"]
    assert "cashflow.csv:net_cash_from_operating_activities_vnd_mn:C007:2025" in answer["evidence"]
    assert answer["confidence"] > 0


def test_assistant_common_metrics_are_grounded(context):
    a = context["analysis"].set_index(["company_id", "fiscal_year"])
    for query, metric in [
        ("Doanh thu của C006 năm 2025 là bao nhiêu?", "revenue_vnd_mn"),
        ("Current Ratio của C007 năm 2025 bằng bao nhiêu?", "current_ratio_x"),
        ("Free Cash Flow của C004 năm 2025 là bao nhiêu?", "free_cash_flow_vnd_mn"),
        ("Tổng nợ phải trả của C012 năm 2025?", "total_liabilities_vnd_mn"),
    ]:
        result = answer_user_query(query, context["analysis"])
        assert result["status"] == "answered", query
        assert result["evidence"], query
    assert a.loc[("C004", 2025), "free_cash_flow_vnd_mn"] == -12630


def test_assistant_unsupported_must_not_claim_confidence(context):
    for query in ["CFO C007 2020", "Phân tích cạnh tranh C007 2025"]:
        result = answer_user_query(query, context["analysis"])
        assert result["status"] == "unsupported"
        assert result["evidence"] == ""
        assert result["confidence"] == 0


def test_assistant_two_metric_questions_not_silently_reduced(context):
    result = answer_user_query(
        "Mô tả xu hướng doanh thu và CFO của C002 trong giai đoạn 2023-2025",
        context["analysis"],
    )
    assert result["status"] == "answered"
    assert "doanh thu" in result["answer"] and "CFO" in result["answer"]
    assert "cashflow.csv" in result["evidence"]


def test_assistant_recognizes_public_question_phrasings(context):
    """Smoketest free-text routing; does not replace Numerical QA answer-key accuracy."""
    from finreport.config import SAMPLES
    questions = pd.read_csv(SAMPLES / "questions_sample.csv", encoding="utf-8-sig")
    for sample in questions.itertuples(index=False):
        response = answer_user_query(sample.question_text_vi, context["analysis"])
        assert response["status"] == "answered", sample.question_id
        assert response["evidence"], sample.question_id


# ─── Equal RuleScore / 0.68 Severity decision table (v1.1) ───────────────
from finreport.alerts import (
    RULES, RULE_COUNT, RULE_CONTRIBUTION, RECOVERY_CRITERIA,
    recovery_status, _escalation,
)
from finreport.config import GOLD_CRITICAL_THRESHOLD


def _healthy_case(**overrides):
    """Synthetic metrics for logic tests; not fitted to public labels."""
    d = {
        "revenue_growth_pct": 3.0,
        "gross_margin_change_pp": 1.0,
        "net_margin_pct": 12.0,
        "cfo_vnd_mn": 1000.0,
        "cfo_to_net_income_x": 1.10,
        "current_ratio_x": 2.0,
        "interest_coverage_x": 6.0,
        "total_debt_growth_pct": -2.0,
        "debt_to_assets_pct": 15.0,
        "dso_days": 40.0,
        "inventory_days": 50.0,
        "anomaly_score": 0.0,
    }
    d.update(overrides)
    return d


def test_equal_weight_fourteen_binary_rules(context):
    assert RULE_COUNT == 14
    assert len(set(RULES)) == 14
    assert RULE_CONTRIBUTION == pytest.approx(1 / 14)
    assert 5 * RULE_CONTRIBUTION == pytest.approx(5 / 14)
    a = context["analysis"]
    d = context["alerts_detail"]
    assert np.allclose(d.rule_contribution, 1 / 14)
    assert np.allclose(d.severity_weight, 1 / 14)  # backwards-compatible alias
    assert np.array_equal(a.activated_rule_count.to_numpy(),
                          a.alert_tags.map(lambda x: len(x.split(";")) if isinstance(x,str) and x else 0).to_numpy())
    assert np.allclose(a.rule_risk_score, (a.activated_rule_count / 14).round(4))
    assert np.allclose(a.risk_score, (0.88 * a.activated_rule_count/14 + 0.12 * a.anomaly_score).round(4), atol=0.0001)


def test_eight_recovery_conditions_all_required():
    assert len(RECOVERY_CRITERIA) == 8
    good = _healthy_case()
    assert recovery_status(good)[0]
    for _, _, metric, _, _ in RECOVERY_CRITERIA:
        broken = dict(good)
        broken[metric] = None
        eligible, checks = recovery_status(broken)
        assert not eligible and sum(checks.values()) == 7, metric


def test_severity_decision_order_and_boundaries():
    good = _healthy_case()
    assert GOLD_CRITICAL_THRESHOLD == 0.68
    assert _escalation(good, 0.68, 0)[:2] == ("CRITICAL", "HIGH_RISK")
    assert _escalation(good, 0.67999, 0)[:2] == ("LOW", "RECOVERING")
    # Non-score crisis combination must take precedence over RECOVERING and HIGH.
    distressed = _healthy_case(net_margin_pct=-1.0, cfo_vnd_mn=-100, interest_coverage_x=0.9)
    assert _escalation(distressed, 0.1, 1)[0] == "CRITICAL"
    # Recovery must override regular HIGH, regardless of anomalous peer score.
    assert _escalation(_healthy_case(anomaly_score=0.8), 0.40, 5)[:2] == ("LOW", "RECOVERING")
    # Gross Margin -3pp with Net Margin <8%, even if score <0.25.
    g = _healthy_case(gross_margin_change_pp=-3, net_margin_pct=7.99)
    assert _escalation(g, 0.0, 0)[0] == "HIGH"
    assert _escalation(_healthy_case(gross_margin_change_pp=-3, net_margin_pct=8), 0.0, 0)[0] == "LOW"
    not_recover = _healthy_case(revenue_growth_pct=-1)
    assert _escalation(not_recover, 0.25, 0)[0] == "HIGH"
    assert _escalation(_healthy_case(revenue_growth_pct=-1, anomaly_score=0.5), 0.0, 0)[0] == "HIGH"
    assert _escalation(_healthy_case(revenue_growth_pct=-1, anomaly_score=0.28), 0.0, 0)[0] == "MEDIUM"
    assert _escalation(not_recover, 0.01, 1)[0] == "MEDIUM"
    assert _escalation(not_recover, 0.0, 0)[:2] == ("LOW", "HEALTHY")


def test_recovery_data_and_public_kpi_are_recomputed(context):
    a = context["analysis"]
    assert a.recovery_conditions_total.eq(8).all()
    assert a.recovery_conditions_met.between(0, 8).all()
    assert ((a.predicted_overall_health == "RECOVERING") <= (a.predicted_severity == "LOW")).all()
    assert context["kpi"]["evidence_traceability_rate"] == 1.0
