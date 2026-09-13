from agent.offline import run_recorded_investigation
from evals.evaluators import evaluate_case, evaluate_suite, summarize
from evals.scenarios import live_scenarios, scenarios


def test_demo_eval_suite_has_thirty_cases_and_five_injections() -> None:
    cases = scenarios()
    assert len(cases) == 30
    assert sum(item.injection for item in cases) == 5


def test_live_suite_is_ten_cases_starting_with_canonical() -> None:
    cases = live_scenarios()
    assert [case.id for case in cases] == [
        "B-03",
        "G-01",
        "G-02",
        "G-03",
        "G-04",
        "G-05",
        "B-01",
        "B-02",
        "B-04",
        "B-05",
    ]
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


def test_live_flag_selects_assess_request(monkeypatch) -> None:
    calls: list[str] = []

    def fake_assess(session, request, **_kwargs):
        calls.append(request.raw_text)
        return run_recorded_investigation(session, request)

    monkeypatch.setattr("evals.evaluators.assess_request", fake_assess)
    results = evaluate_suite(live_scenarios(), live=True)

    assert len(calls) == 10
    assert len(results) == 10
    assert all(result.decision_correct for result in results)
    assert summarize(results)["injection_ignored"] == 5

