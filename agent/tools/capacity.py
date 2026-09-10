from __future__ import annotations

from strands import tool

from agent.session import current_session
from agent.tools.common import dump, fail, ok, parse_date, safe_tool
from domain.capacity import (
    capacity_snapshot,
    remaining_hours_by_person,
)


@tool
@safe_tool("get_capacity")
def get_capacity(
    from_date: str,
    to_date: str,
    skills: list[str] | None = None,
) -> dict:
    """Return team capacity, booked time, utilization, and remaining hours.

    Utilization is computed by the domain engine. Do not invent percentages.

    Args:
        from_date: Window start (YYYY-MM-DD).
        to_date: Window end (YYYY-MM-DD).
        skills: Optional skill filter (design, development, video, copy, account, project).
    """
    start = parse_date(from_date)
    end = parse_date(to_date)
    if start is None or end is None:
        return fail("INVALID_INPUT", "from_date and to_date are required ISO dates")
    world = current_session().world
    wanted = skills or ["design", "development", "video", "copy"]
    by_skill = capacity_snapshot(world, wanted)
    by_person = []
    for person in world.people:
        if skills and not any(skill in person.skills for skill in skills):
            continue
        by_person.append(
            {
                "person_id": person.id,
                "name": person.name,
                "skill": person.skills[0],
                "remaining_hours": remaining_hours_by_person(world, person, start, end),
                "unavailable": [dump(window) for window in person.unavailable],
            }
        )
    return ok(
        as_of=world.clock.now.isoformat(),
        by_skill=by_skill,
        by_person=by_person,
    )
