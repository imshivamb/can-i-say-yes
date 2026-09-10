from agent.tools.calendar import get_calendar
from agent.tools.capacity import get_capacity
from agent.tools.commitments import get_commitments
from agent.tools.dependencies import get_dependencies
from agent.tools.documents import search_documents
from agent.tools.email import search_email
from agent.tools.projects import get_project_state
from agent.tools.schedule import calculate_schedule, check_conflicts, find_alternatives
from agent.tools.suppliers import get_supplier_status
from agent.tools.writes import (
    create_commitment,
    monitor_commitment,
    request_human_decision,
    send_customer_message,
)

READ_TOOLS = [
    search_email,
    search_documents,
    get_project_state,
    get_capacity,
    get_commitments,
    get_supplier_status,
    get_calendar,
    get_dependencies,
]

DOMAIN_TOOLS = [
    calculate_schedule,
    check_conflicts,
    find_alternatives,
]

WRITE_TOOLS = [
    request_human_decision,
    create_commitment,
    send_customer_message,
    monitor_commitment,
]

P0_TOOLS = READ_TOOLS + DOMAIN_TOOLS

__all__ = [
    "DOMAIN_TOOLS",
    "P0_TOOLS",
    "READ_TOOLS",
    "WRITE_TOOLS",
    "calculate_schedule",
    "check_conflicts",
    "create_commitment",
    "find_alternatives",
    "get_calendar",
    "get_capacity",
    "get_commitments",
    "get_dependencies",
    "get_project_state",
    "get_supplier_status",
    "monitor_commitment",
    "request_human_decision",
    "search_documents",
    "search_email",
    "send_customer_message",
]
