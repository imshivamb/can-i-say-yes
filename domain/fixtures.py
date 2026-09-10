from __future__ import annotations

from datetime import date

from domain.clock import DEMO_START
from domain.models import Money, ParsedRequest, WorkItem

ACME_REQUEST_TEXT = (
    "We'd like 12 social creatives, a landing page and three short videos "
    "for our September campaign. Can you have everything ready by September 18 "
    "for ₹4.2 lakh?"
)


def acme_campaign_request() -> ParsedRequest:
    return ParsedRequest(
        id="req_acme_001",
        customer_name="Acme Foods",
        customer_id="cli_acme",
        raw_text=ACME_REQUEST_TEXT,
        scope_summary="September campaign package",
        work_items=[
            WorkItem(
                id="wi_creatives",
                kind="social_creative",
                name="Social creatives",
                quantity=12,
                estimated_hours=36,
                skill="design",
            ),
            WorkItem(
                id="wi_landing",
                kind="landing_page",
                name="Landing page",
                quantity=1,
                estimated_hours=24,
                skill="development",
            ),
            WorkItem(
                id="wi_videos",
                kind="video",
                name="Short videos",
                quantity=3,
                estimated_hours=30,
                skill="video",
                required_asset_ids=["ast_acme_product_photos"],
            ),
        ],
        deadline=date(2026, 9, 18),
        budget=Money(amount=420000),
        source="demo",
        received_at=DEMO_START,
    )


def nova_launch_request() -> ParsedRequest:
    return ParsedRequest(
        id="req_nova_intake",
        customer_name="Nova Health",
        customer_id="cli_nova",
        raw_text=(
            "Can Northstar build our product launch site with six pages by "
            "October 9 for ₹5.2 lakh?"
        ),
        scope_summary="Nova product launch site",
        work_items=[
            WorkItem(
                id="wi_nova_intake_site",
                kind="landing_page",
                name="Product launch site",
                quantity=1,
                estimated_hours=60,
                skill="development",
            )
        ],
        deadline=date(2026, 10, 9),
        budget=Money(amount=520000),
        source="demo",
        received_at=DEMO_START,
    )
