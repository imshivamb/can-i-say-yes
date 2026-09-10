from __future__ import annotations

from domain.capacity import utilization_for_skill
from domain.freshness import freshness_for
from domain.ids import new_id
from domain.models import Evidence, ParsedRequest, ScheduleResult
from domain.world import World


def _evidence(
    world: World,
    *,
    source_type: str,
    source_name: str,
    source_reference: str,
    content: str,
    reliability: str,
    timestamp=None,
) -> Evidence:
    now = world.clock.now
    ts = timestamp or now
    return Evidence(
        id=new_id("evd"),
        source_type=source_type,  # type: ignore[arg-type]
        source_name=source_name,
        source_reference=source_reference,
        timestamp=ts,
        as_of=now,
        content=content,
        freshness=freshness_for(ts, now),
        reliability=reliability,  # type: ignore[arg-type]
    )


def gather_assessment_evidence(
    world: World,
    request: ParsedRequest,
    schedule: ScheduleResult,
) -> list[Evidence]:
    items: list[Evidence] = []
    now = world.clock.now

    design_util = utilization_for_skill(world, "design")
    items.append(
        _evidence(
            world,
            source_type="capacity_ledger",
            source_name="Capacity ledger",
            source_reference="doc_capacity_0912",
            content=f"Design utilization is {design_util:.0%} as of {now.date().isoformat()}.",
            reliability="inferred",
        )
    )

    bloom = next((c for c in world.commitments if c.id == "cmt_bloom_festive"), None)
    if bloom:
        items.append(
            _evidence(
                world,
                source_type="commitment",
                source_name="Existing commitment",
                source_reference="cmt_bloom_festive",
                content=(
                    f"{bloom.customer_name} festive campaign is committed for "
                    f"{bloom.committed_deadline.isoformat()}."
                ),
                reliability="confirmed",
            )
        )

    bloom_mail = next((e for e in world.emails if e.id == "eml_bloom_priority"), None)
    if bloom_mail:
        items.append(
            _evidence(
                world,
                source_type="email",
                source_name="Bloom Hotels email",
                source_reference="eml_bloom_priority",
                content=bloom_mail.body.strip().splitlines()[0],
                reliability="confirmed",
                timestamp=bloom_mail.sent_at,
            )
        )

    bloom_plan = next((d for d in world.documents if d.id == "doc_bloom_plan"), None)
    if bloom_plan:
        items.append(
            _evidence(
                world,
                source_type="project_plan",
                source_name="Bloom project plan",
                source_reference="prj_bloom_festive",
                content="Bloom festive assets are locked for 17 September.",
                reliability="confirmed",
                timestamp=bloom_plan.created_at,
            )
        )

    photo_mail = next((e for e in world.emails if e.id == "eml_acme_photos"), None)
    if photo_mail:
        items.append(
            _evidence(
                world,
                source_type="email",
                source_name="Acme Foods email",
                source_reference="eml_acme_photos",
                content=photo_mail.body.strip(),
                reliability="stated",
                timestamp=photo_mail.sent_at,
            )
        )

    photos = next((a for a in world.assets if a.id == "ast_acme_product_photos"), None)
    if photos:
        items.append(
            _evidence(
                world,
                source_type="customer_asset",
                source_name="Customer assets",
                source_reference="ast_acme_product_photos",
                content=(
                    f"{photos.name} received={photos.received}; promised_on={photos.promised_on}."
                ),
                reliability="confirmed",
            )
        )

    sop = next((d for d in world.documents if d.id == "doc_video_sop"), None)
    if sop:
        items.append(
            _evidence(
                world,
                source_type="document",
                source_name="Video SOP",
                source_reference="doc_video_sop",
                content="Final cut requires approved product photography.",
                reliability="confirmed",
                timestamp=sop.created_at,
            )
        )

    editor_mail = next((e for e in world.emails if e.id == "eml_editor_window"), None)
    if editor_mail:
        items.append(
            _evidence(
                world,
                source_type="email",
                source_name="Supplier email",
                source_reference="eml_editor_window",
                content=editor_mail.body.strip(),
                reliability="confirmed",
                timestamp=editor_mail.sent_at,
            )
        )

    delay_mail = next((e for e in world.emails if e.id == "eml_editor_delay"), None)
    if delay_mail and delay_mail.sent_at <= now:
        items.append(
            _evidence(
                world,
                source_type="email",
                source_name="Supplier email",
                source_reference="eml_editor_delay",
                content=delay_mail.body.strip(),
                reliability="confirmed",
                timestamp=delay_mail.sent_at,
            )
        )

    editor = next((s for s in world.suppliers if s.id == "sup_frame_grain"), None)
    if editor:
        items.append(
            _evidence(
                world,
                source_type="supplier_record",
                source_name=editor.name,
                source_reference="sup_frame_grain",
                content=f"{editor.name} available from {editor.available_from}.",
                reliability="confirmed",
            )
        )

    items.append(
        _evidence(
            world,
            source_type="domain_calculation",
            source_name="Schedule engine",
            source_reference="domain_schedule",
            content=(
                f"Forecast end {schedule.forecast_end}; "
                f"slack {schedule.slack_days} working days vs {request.deadline}."
            ),
            reliability="inferred",
        )
    )

    priya_ooo = next((e for e in world.calendar if e.id == "cal_priya_ooo"), None)
    if priya_ooo:
        items.append(
            _evidence(
                world,
                source_type="calendar",
                source_name="Calendar",
                source_reference="cal_priya_ooo",
                content="Priya Nair is unavailable 12–13 September.",
                reliability="confirmed",
                timestamp=priya_ooo.start,
            )
        )

    return items
