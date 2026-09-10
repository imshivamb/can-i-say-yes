from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from domain.clock import is_working_day, working_days_between
from domain.models import Person
from domain.world import World

WORKING_DAYS_PER_WEEK = 6.0


def hours_per_working_day(person: Person) -> float:
    return person.weekly_hours / WORKING_DAYS_PER_WEEK


def person_is_ooo(world: World, person_id: str, day: date) -> bool:
    person = world.person(person_id)
    for window in person.unavailable:
        if window.start.date() <= day <= window.end.date():
            return True
    for event in world.calendar:
        if event.person_id != person_id or event.kind != "ooo":
            continue
        if event.start.date() <= day <= event.end.date():
            return True
    return False


def booked_hours_for_skill(world: World, skill: str) -> float:
    total = 0.0
    skill_people = {p.id for p in world.people_with_skill(skill)}
    for project in world.active_projects():
        for person_id, hours in project.booked_hours_by_person.items():
            if person_id in skill_people:
                total += hours
    return total


def weekly_hours_for_skill(world: World, skill: str) -> float:
    return sum(p.weekly_hours for p in world.people_with_skill(skill))


def utilization_for_skill(world: World, skill: str) -> float:
    weekly = weekly_hours_for_skill(world, skill)
    if weekly == 0:
        return 0.0
    return booked_hours_for_skill(world, skill) / weekly


def remaining_hours_for_skill(world: World, skill: str) -> float:
    return weekly_hours_for_skill(world, skill) - booked_hours_for_skill(world, skill)


def capacity_snapshot(world: World, skills: list[str]) -> dict[str, dict[str, float]]:
    snapshot: dict[str, dict[str, float]] = {}
    for skill in skills:
        weekly = weekly_hours_for_skill(world, skill)
        booked = booked_hours_for_skill(world, skill)
        snapshot[skill] = {
            "weekly_hours": weekly,
            "booked_hours": booked,
            "utilization": (booked / weekly) if weekly else 0.0,
            "remaining_hours": weekly - booked,
        }
    return snapshot


def remaining_hours_by_person(
    world: World,
    person: Person,
    from_date: date,
    to_date: date,
) -> float:
    """Hours this person can still take between from_date and to_date after bookings."""
    daily = hours_per_working_day(person)
    available = 0.0
    current = from_date
    while current <= to_date:
        if is_working_day(current) and not person_is_ooo(world, person.id, current):
            booked = _booked_hours_on_day(world, person.id, current, from_date)
            available += max(0.0, daily - booked)
        current += timedelta(days=1)
    return available


def _booked_hours_on_day(world: World, person_id: str, day: date, window_start: date) -> float:
    daily = hours_per_working_day(world.person(person_id))
    booked = 0.0
    for project in world.active_projects():
        hours = project.booked_hours_by_person.get(person_id)
        if not hours:
            continue
        if day > project.deadline:
            continue
        span_start = window_start
        span_end = project.deadline
        days = working_days_between(span_start, span_end)
        if days == 0:
            continue
        # Spread remaining booked hours uniformly across working days until deadline.
        per_day = hours / days
        booked += min(daily, per_day)
    return booked


def remaining_skill_hours_until(
    world: World,
    skill: str,
    from_date: date,
    to_date: date,
) -> float:
    return sum(
        remaining_hours_by_person(world, person, from_date, to_date)
        for person in world.people_with_skill(skill)
    )


def person_remaining_map(world: World, from_date: date, to_date: date) -> dict[str, float]:
    remaining: dict[str, float] = defaultdict(float)
    for person in world.people:
        remaining[person.id] = remaining_hours_by_person(world, person, from_date, to_date)
    return dict(remaining)
