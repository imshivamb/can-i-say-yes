from adapters.files.world import load_world
from agent.session import UNTRUSTED_PREFIX, AgentSession, use_session
from agent.tools import (
    calculate_schedule,
    check_conflicts,
    find_alternatives,
    get_capacity,
    get_commitments,
    get_dependencies,
    get_supplier_status,
    search_documents,
    search_email,
)
from domain.fixtures import acme_campaign_request


def _session() -> AgentSession:
    return AgentSession(world=load_world())


def test_search_email_finds_acme_needles() -> None:
    session = _session()
    with use_session(session):
        result = search_email(query="product photography", client_id="cli_acme")
    assert result["ok"] is True
    ids = {item["id"] for item in result["results"]}
    assert "eml_acme_photos" in ids
    assert result["results"][0]["snippet"].startswith(UNTRUSTED_PREFIX)


def test_injection_email_is_data_not_instructions() -> None:
    session = _session()
    with use_session(session):
        result = search_email(query="Ignore previous instructions")
    assert result["ok"] is True
    match = next(item for item in result["results"] if item["id"] == "eml_injection")
    assert match["snippet"].startswith(UNTRUSTED_PREFIX)
    assert "SAFE" in match["snippet"]


def test_search_documents_finds_video_sop() -> None:
    session = _session()
    with use_session(session):
        result = search_documents(query="product photography final cut")
    assert result["ok"] is True
    assert any(item["id"] == "doc_video_sop" for item in result["results"])


def test_get_capacity_design_is_82_percent() -> None:
    session = _session()
    with use_session(session):
        result = get_capacity(
            from_date="2026-09-12",
            to_date="2026-09-22",
            skills=["design"],
        )
    assert result["ok"] is True
    assert abs(result["by_skill"]["design"]["utilization"] - 0.82) < 1e-9


def test_get_commitments_includes_bloom() -> None:
    session = _session()
    with use_session(session):
        result = get_commitments()
    assert result["ok"] is True
    ids = {item["id"] for item in result["commitments"]}
    assert "cmt_bloom_festive" in ids


def test_get_supplier_status_frame_and_grain() -> None:
    session = _session()
    with use_session(session):
        result = get_supplier_status(kind="video_editor")
    assert result["ok"] is True
    names = {item["id"] for item in result["suppliers"]}
    assert "sup_frame_grain" in names
    frame = next(item for item in result["suppliers"] if item["id"] == "sup_frame_grain")
    assert frame["available_from"] == "2026-09-15"


def test_get_dependencies_missing_photos() -> None:
    session = _session()
    request = acme_campaign_request()
    with use_session(session):
        session.put_request(request)
        result = get_dependencies(
            client_id="cli_acme",
            work_item_ids=["wi_videos"],
        )
    assert result["ok"] is True
    photos = next(item for item in result["assets"] if item["id"] == "ast_acme_product_photos")
    assert photos["received"] is False


def test_domain_tools_return_acme_conflicts_and_alternatives() -> None:
    session = _session()
    request = acme_campaign_request()
    with use_session(session):
        session.put_request(request)
        schedule = calculate_schedule(request_id=request.id)
        conflicts = check_conflicts(request_id=request.id)
        alternatives = find_alternatives(request_id=request.id)
    assert schedule["ok"] is True
    assert schedule["feasible_for_deadline"] is False
    codes = {item["code"] for item in conflicts["conflicts"]}
    assert {
        "CAPACITY_OVERALLOCATED",
        "EXISTING_COMMITMENT",
        "MISSING_DEPENDENCY",
        "SUPPLIER_WINDOW",
    } <= codes
    alt_ids = [item["id"] for item in alternatives["alternatives"]]
    assert alt_ids == ["alt_a", "alt_b", "alt_c"]
    recommended = next(item for item in alternatives["alternatives"] if item["recommended"])
    assert recommended["id"] == "alt_a"
    assert any(item.id.startswith("evd_") for item in session.evidence)
