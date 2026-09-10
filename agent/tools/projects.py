from __future__ import annotations

from strands import tool

from agent.session import current_session
from agent.tools.common import dump, ok, safe_tool


@tool
@safe_tool("get_project_state")
def get_project_state(
    client_id: str | None = None,
    project_id: str | None = None,
    active_only: bool = True,
) -> dict:
    """Return matching projects with assigned people and deadlines.

    Args:
        client_id: Optional client id.
        project_id: Optional project id.
        active_only: If true (default), only active projects.
    """
    world = current_session().world
    projects = []
    for project in world.projects:
        if active_only and project.status != "active":
            continue
        if client_id and project.client_id != client_id:
            continue
        if project_id and project.id != project_id:
            continue
        assigned = [
            {"id": person.id, "name": person.name, "role": person.role}
            for person in world.people
            if person.id in project.assigned_person_ids
        ]
        payload = dump(project)
        payload["assigned_people"] = assigned
        projects.append(payload)
    return ok(projects=projects)
