from domain.fixtures import ACME_REQUEST_TEXT, acme_campaign_request
from domain.ids import has_prefix, new_id


def test_acme_request_validates() -> None:
    request = acme_campaign_request()
    assert request.customer_id == "cli_acme"
    assert request.deadline.isoformat() == "2026-09-18"
    assert request.budget is not None
    assert request.budget.amount == 420000
    assert request.raw_text == ACME_REQUEST_TEXT
    assert {item.id for item in request.work_items} == {
        "wi_creatives",
        "wi_landing",
        "wi_videos",
    }


def test_new_id_uses_prefix() -> None:
    value = new_id("cmt")
    assert has_prefix(value, "cmt")
    assert value.startswith("cmt_")
