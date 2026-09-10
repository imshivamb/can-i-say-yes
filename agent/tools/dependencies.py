from __future__ import annotations

from strands import tool

from agent.session import current_session
from agent.tools.common import dump, ok, safe_tool


@tool
@safe_tool("get_dependencies")
def get_dependencies(
    client_id: str | None = None,
    work_item_ids: list[str] | None = None,
) -> dict:
    """Return required assets, received status, promised dates, and project DAG edges.

    Args:
        client_id: Optional client id.
        work_item_ids: Optional work item ids from the parsed request.
    """
    session = current_session()
    world = session.world
    required_asset_ids: set[str] = set()
    if work_item_ids:
        for request in session.requests.values():
            for item in request.work_items:
                if item.id in work_item_ids:
                    required_asset_ids.update(item.required_asset_ids)
        for project in world.projects:
            for item in project.work_items:
                if item.id in work_item_ids:
                    required_asset_ids.update(item.required_asset_ids)

    assets = []
    for asset in world.assets:
        if client_id and asset.client_id != client_id:
            continue
        if required_asset_ids and asset.id not in required_asset_ids:
            continue
        assets.append(dump(asset))

    edges = []
    for project in world.projects:
        if client_id and project.client_id != client_id:
            continue
        for dep in project.dependencies:
            edges.append({"project_id": project.id, "depends_on": dep})
        for item in project.work_items:
            for parent in item.depends_on:
                edges.append({"work_item_id": item.id, "depends_on": parent})
            for asset_id in item.required_asset_ids:
                edges.append({"work_item_id": item.id, "depends_on": asset_id})

    for request in session.requests.values():
        if client_id and request.customer_id != client_id:
            continue
        for item in request.work_items:
            if work_item_ids and item.id not in work_item_ids:
                continue
            for asset_id in item.required_asset_ids:
                edges.append({"work_item_id": item.id, "depends_on": asset_id})

    return ok(assets=assets, edges=edges)
