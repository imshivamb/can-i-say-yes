from __future__ import annotations

from strands import tool

from agent.session import UNTRUSTED_PREFIX, current_session
from agent.tools.common import dump, ok, safe_tool, snippet


@tool
@safe_tool("get_supplier_status")
def get_supplier_status(
    supplier_id: str | None = None,
    kind: str | None = None,
) -> dict:
    """Return current supplier availability, rates, and the latest related email snippet.

    Args:
        supplier_id: Optional supplier id such as sup_frame_grain.
        kind: Optional kind such as video_editor or photographer.
    """
    world = current_session().world
    suppliers = []
    for supplier in world.suppliers:
        if supplier_id and supplier.id != supplier_id:
            continue
        if kind and supplier.kind != kind:
            continue
        latest = _latest_related_email(world, supplier.name)
        payload = dump(supplier)
        payload["latest_email_snippet"] = latest
        suppliers.append(payload)
    return ok(suppliers=suppliers)


def _latest_related_email(world, name: str) -> str | None:
    needle = name.lower()
    matches = [
        email
        for email in world.emails
        if needle in email.subject.lower()
        or needle in email.body.lower()
        or needle.split()[0] in email.from_addr.lower()
    ]
    if not matches:
        return None
    latest = max(matches, key=lambda email: email.sent_at)
    return UNTRUSTED_PREFIX + snippet(latest.body)
