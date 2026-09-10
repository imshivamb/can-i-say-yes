from evals.evaluators import evaluate_case, summarize
from evals.scenarios import scenarios


def test_demo_eval_suite_has_thirty_cases_and_five_injections() -> None:
    cases = scenarios()
    assert len(cases) == 30
    assert sum(item.injection for item in cases) == 5


def test_canonical_case_is_grounded_and_unsafe() -> None:
    result = evaluate_case(scenarios()[0])

    assert result.decision_correct
    assert result.evidence_grounded
    assert not result.unsupported_safe


def test_eval_summary_reports_no_unsupported_safe_result() -> None:
    results = [evaluate_case(case) for case in scenarios()]
    summary = summarize(results)

    assert summary["scenarios"] == 30
    assert summary["unsupported_safe"] == 0
    assert summary["injection_cases"] == 5
    assert summary["injection_ignored"] == 5

