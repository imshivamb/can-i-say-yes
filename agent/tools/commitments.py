from __future__ import annotations

from strands import tool

from agent.session import current_session
from agent.tools.common import dump, ok, safe_tool

_DEFAULT_STATUSES = ["COMMITTED", "MONITORING"]


@tool
@safe_tool("get_commitments")
def get_commitments(
    status_in: list[str] | None = None,
    client_id: str | None = None,
) -> dict:
    """Return existing customer commitments with deadlines and health.

    Use this before deciding whether a new promise is safe.

    Args:
        status_in: Status filter. Defaults to COMMITTED and MONITORING.
        client_id: Optional client id.
    """
    statuses = set(status_in or _DEFAULT_STATUSES)
    world = current_session().world
    items = []
    for commitment in world.commitments:
        if commitment.status not in statuses:
            continue
        if client_id and commitment.customer_id != client_id:
            continue
        items.append(dump(commitment))
    return ok(commitments=items)
