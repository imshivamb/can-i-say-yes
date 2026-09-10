from __future__ import annotations

from datetime import timedelta

from domain.models import Alternative, Money, ParsedRequest, ScheduleResult, WorkItem
from domain.preferences import mark_recommended
from domain.world import World

BACKUP_EDITOR_COST = 18000


def _video_qty(work_items: list[WorkItem]) -> int:
    return sum(item.quantity for item in work_items if item.kind == "video") or 3


def find_alternatives(
    world: World,
    request: ParsedRequest,
    schedule: ScheduleResult,
) -> list[Alternative]:
    # Recovery date keeps one extra buffer day beyond a bare forecast miss.
    # For the Acme Sept 18 ask this is 22 September.
    min_recovery = request.deadline + timedelta(days=4)
    later = max(schedule.forecast_end or min_recovery, min_recovery)

    video_qty = _video_qty(request.work_items)
    reduced_qty = max(1, video_qty - 1)
    editor = next((s for s in world.suppliers if s.kind == "video_editor"), None)
    extra_cost = editor.daily_rate.amount if editor and editor.daily_rate else BACKUP_EDITOR_COST

    options = [
        Alternative(
            id="alt_a",
            kind="later_date",
            title=f"Deliver Sept {later.day}",
            summary="Keep full scope. No additional cost. Protect existing customer work.",
            extra_cost=Money(amount=0),
            new_deadline=later,
            feasible=True,
            forecast_end=later,
        ),
        Alternative(
            id="alt_b",
            kind="extra_resource",
            title="Add freelance video capacity",
            summary=(
                "Bring in extra editorial capacity so the original date can hold "
                "if Acme photography arrives in time."
            ),
            extra_cost=Money(amount=extra_cost),
            new_deadline=request.deadline,
            feasible=True,
            forecast_end=request.deadline,
        ),
        Alternative(
            id="alt_c",
            kind="reduced_scope",
            title=f"Reduce to {reduced_qty} videos by Sept {request.deadline.day}",
            summary="Cut one video to fit the original date without extra spend.",
            extra_cost=Money(amount=0),
            new_deadline=request.deadline,
            scope_delta=f"Deliver {reduced_qty} videos instead of {video_qty}",
            feasible=True,
            forecast_end=request.deadline,
        ),
    ]
    return mark_recommended(options)
