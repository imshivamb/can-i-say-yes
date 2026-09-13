from __future__ import annotations

from typing import Any

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent, HookProvider, HookRegistry

from agent.policies.authorization import PolicyContext, authorize
from agent.session import current_session
from domain.clock import ensure_tz
from domain.ids import new_id
from domain.models import ActivityItem, AuditRecord

STRUCTURED_OUTPUT_TOOLS = frozenset(
    {"ParsedRequest", "FeasibilityAssessment", "CustomerMessageDraft"}
)


class AuthorityAndTraceHooks(HookProvider):
    """Make tool activity visible and enforce policy before Strands executes writes."""

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        del kwargs
        registry.add_callback(BeforeToolCallEvent, self.before_tool_call)
        registry.add_callback(AfterToolCallEvent, self.after_tool_call)

    def before_tool_call(self, event: BeforeToolCallEvent) -> None:
        session = current_session()
        name = event.tool_use.get("name", "unknown")
        if name in STRUCTURED_OUTPUT_TOOLS:
            return
        arguments = event.tool_use.get("input", {})
        if not isinstance(arguments, dict):
            arguments = {}
        session.record_tool(name)
        session.activity.append(
            ActivityItem(
                id=new_id("aud"),
                timestamp=session.world.clock.now,
                text=f"{name} started",
                commitment_id=arguments.get("commitment_id"),
            )
        )

        context = PolicyContext(
            now=ensure_tz(session.world.clock.now),
            decisions=list(session.decisions.values()),
            commitments=session.commitments(),
        )
        permission = authorize(name, arguments, context)
        if permission != "allow":
            event.cancel_tool = f"{name} blocked by policy: {permission}"
            session.record_audit(
                AuditRecord(
                    id=new_id("aud"),
                    timestamp=ensure_tz(session.world.clock.now),
                    actor="strands_hook",
                    tool=name,
                    arguments=arguments,
                    result_status="denied",
                    authorization=permission,
                    commitment_id=arguments.get("commitment_id"),
                    request_id=arguments.get("request_id"),
                )
            )
            session.activity.append(
                ActivityItem(
                    id=new_id("aud"),
                    timestamp=session.world.clock.now,
                    text=f"{name} blocked before execution: {permission}",
                    commitment_id=arguments.get("commitment_id"),
                )
            )

    def after_tool_call(self, event: AfterToolCallEvent) -> None:
        session = current_session()
        name = event.tool_use.get("name", "unknown")
        if name in STRUCTURED_OUTPUT_TOOLS:
            return
        session.activity.append(
            ActivityItem(
                id=new_id("aud"),
                timestamp=session.world.clock.now,
                text=f"{name} completed",
                commitment_id=event.tool_use.get("input", {}).get("commitment_id")
                if isinstance(event.tool_use.get("input"), dict)
                else None,
            )
        )

