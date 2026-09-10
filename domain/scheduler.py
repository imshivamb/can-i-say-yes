from __future__ import annotations

from datetime import date, timedelta
from math import ceil

from domain.capacity import (
    capacity_snapshot,
    remaining_skill_hours_until,
)
from domain.clock import add_working_days, is_working_day, working_days_between
from domain.dependencies import earliest_item_start, missing_assets
from domain.enums import Skill
from domain.models import ItemForecast, ParsedRequest, ScheduleResult, Supplier, WorkItem
from domain.world import World

SKILL_TO_SUPPLIER = {
    "video": "video_editor",
    "photography": "photographer",
}


def _supplier_for_item(world: World, item: WorkItem) -> Supplier | None:
    kind = SKILL_TO_SUPPLIER.get(item.skill)
    if not kind:
        return None
    matches = world.suppliers_of_kind(kind)
    if not matches:
        return None
    # Prefer an already-open window, otherwise the earliest future window.
    open_now = [s for s in matches if s.available_from is None]
    if open_now:
        return open_now[0]
    dated = [s for s in matches if s.available_from is not None]
    dated.sort(key=lambda s: s.available_from or date.max)
    return dated[0] if dated else matches[0]


def _hours_per_day_for_skill(world: World, skill: Skill) -> float:
    people = world.people_with_skill(skill)
    if not people:
        return 6.0
    return sum(p.weekly_hours for p in people) / (6.0 * len(people))


def _place_item(
    world: World,
    item: WorkItem,
    today: date,
    remaining_by_skill: dict[str, float],
) -> ItemForecast:
    supplier = _supplier_for_item(world, item)
    supplier_from = supplier.available_from if supplier else None
    start = earliest_item_start(world, item, today, supplier_from)
    blocked_by: list[str] = []
    for asset_id in item.required_asset_ids:
        asset = world.asset(asset_id)
        if asset.required and not asset.received:
            blocked_by.append(asset_id)

    daily = _hours_per_day_for_skill(world, item.skill)
    # New work can only consume leftover hours until existing deadlines clear.
    leftover = remaining_by_skill.get(item.skill, 0.0)
    if leftover <= 0:
        days_needed = ceil(item.estimated_hours / daily) if daily else 99
        start = max(start, today)
        # Wait until the next week-ish if the skill is fully booked this week.
        start = add_working_days(start, 2)
        end = add_working_days(start, max(days_needed, 1))
        return ItemForecast(
            work_item_id=item.id,
            start=start,
            end=end,
            blocked_by=blocked_by,
        )

    if leftover >= item.estimated_hours:
        days_needed = max(1, ceil(item.estimated_hours / daily))
        end = add_working_days(start, days_needed)
        remaining_by_skill[item.skill] = leftover - item.estimated_hours
        return ItemForecast(
            work_item_id=item.id,
            start=start,
            end=end,
            blocked_by=blocked_by,
        )

    # Partial progress now, remainder after leftover is exhausted.
    days_now = max(1, ceil(leftover / daily)) if leftover > 0 else 0
    remainder = item.estimated_hours - leftover
    days_after = max(1, ceil(remainder / daily))
    remaining_by_skill[item.skill] = 0.0
    mid = add_working_days(start, days_now)
    end = add_working_days(mid + timedelta(days=1), days_after)
    if not is_working_day(end):
        end = add_working_days(end, 1)
    return ItemForecast(
        work_item_id=item.id,
        start=start,
        end=end,
        blocked_by=blocked_by,
    )


def calculate_schedule(world: World, request: ParsedRequest) -> ScheduleResult:
    today = world.clock.now.date()
    deadline = request.deadline
    skills = sorted({item.skill for item in request.work_items})
    utilization = {
        skill: snapshot["utilization"]
        for skill, snapshot in capacity_snapshot(world, skills).items()
    }
    remaining = {
        skill: remaining_skill_hours_until(world, skill, today, deadline) for skill in skills
    }

    forecasts: list[ItemForecast] = []
    remaining_mutable = dict(remaining)
    for item in request.work_items:
        forecasts.append(_place_item(world, item, today, remaining_mutable))

    ends = [f.end for f in forecasts if f.end is not None]
    forecast_end = max(ends) if ends else None
    slack = 0
    if forecast_end is not None:
        slack = (
            working_days_between(forecast_end, deadline) - 1
            if forecast_end <= deadline
            else (-working_days_between(deadline, forecast_end))
        )

    critical_path: list[str] = []
    for asset in missing_assets(world, request.work_items):
        critical_path.append(asset.id)
    late_items = [f.work_item_id for f in forecasts if f.end and f.end > deadline]
    critical_path.extend(late_items)

    feasible = (
        forecast_end is not None
        and forecast_end <= deadline
        and slack >= 1
        and not missing_assets(world, request.work_items)
    )

    return ScheduleResult(
        feasible_for_deadline=feasible,
        forecast_end=forecast_end,
        slack_days=slack,
        critical_path=critical_path,
        utilization_by_skill=utilization,
        item_forecasts=forecasts,
    )
