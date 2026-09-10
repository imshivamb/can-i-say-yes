from __future__ import annotations

from datetime import datetime, time

from strands import tool

from adapters.integrations import GoogleCalendarAdapter, live_integrations_enabled
from agent.session import current_session
from agent.tools.common import dump, fail, ok, parse_date, safe_tool


@tool
@safe_tool("get_calendar")
def get_calendar(
    from_date: str,
    to_date: str,
    person_id: str | None = None,
) -> dict:
    """Return calendar events and out-of-office windows.

    Args:
        from_date: Window start (YYYY-MM-DD).
        to_date: Window end (YYYY-MM-DD).
        person_id: Optional person id such as per_priya.
    """
    start = parse_date(from_date)
    end = parse_date(to_date)
    if start is None or end is None:
        return fail("INVALID_INPUT", "from_date and to_date are required ISO dates")
    world = current_session().world
    if live_integrations_enabled():
        live_events = GoogleCalendarAdapter().events(
            datetime.combine(start, time.min, tzinfo=world.clock.now.tzinfo),
            datetime.combine(end, time.max, tzinfo=world.clock.now.tzinfo),
        )
        known = {event.id for event in world.calendar}
        world.calendar.extend(event for event in live_events if event.id not in known)
    events = []
    for event in world.calendar:
        if person_id and event.person_id != person_id:
            continue
        if event.end.date() < start or event.start.date() > end:
            continue
        events.append(dump(event))
    ooo = []
    for person in world.people:
        if person_id and person.id != person_id:
            continue
        for window in person.unavailable:
            if window.end.date() < start or window.start.date() > end:
                continue
            ooo.append({"person_id": person.id, "name": person.name, **dump(window)})
    return ok(events=events, ooo=ooo)
