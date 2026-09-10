from __future__ import annotations

import inspect
from collections.abc import Callable
from datetime import date
from functools import wraps
from typing import Any

from agent.policies.authorization import PolicyContext, authorize
from agent.session import current_session
from domain.clock import ensure_tz
from domain.ids import new_id
from domain.models import AuditRecord


def ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def fail(error_code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error_code": error_code, "message": message}


def parse_date(value: str | None) -> date | None:
    if value is None or value == "":
        return None
    return date.fromisoformat(value)


def dump(model: Any) -> Any:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model


ToolFn = Callable[..., dict[str, Any]]


def safe_tool(name: str) -> Callable[[ToolFn], ToolFn]:
    """Catch repository failures and write an audit row. Never raise file errors to the model."""

    def decorator(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            session = current_session()
            session.record_tool(name)
            bound = inspect.signature(fn).bind_partial(*args, **kwargs)
            try:
                result = fn(*args, **kwargs)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                result = fail("SOURCE_UNAVAILABLE", f"{name} unavailable: {exc}")
            status = "success" if result.get("ok") else "error"
            session.record_audit(
                AuditRecord(
                    id=new_id("aud"),
                    timestamp=ensure_tz(session.world.clock.now),
                    actor="agent",
                    tool=name,
                    arguments=dict(bound.arguments),
                    result_status=status,
                    authorization="allow",
                )
            )
            return result

        wrapper.__signature__ = inspect.signature(fn)
        return wrapper

    return decorator


def write_tool(name: str) -> Callable[[ToolFn], ToolFn]:
    """Policy-gated write. Nothing is persisted unless authorize() returns allow."""

    def decorator(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            session = current_session()
            session.record_tool(name)
            bound = inspect.signature(fn).bind_partial(*args, **kwargs)
            arguments = dict(bound.arguments)
            context = PolicyContext(
                now=ensure_tz(session.world.clock.now),
                decisions=list(session.decisions.values()),
                commitments=session.commitments(),
            )
            permission = authorize(name, arguments, context)
            if permission != "allow":
                session.record_audit(
                    AuditRecord(
                        id=new_id("aud"),
                        timestamp=ensure_tz(session.world.clock.now),
                        actor="agent",
                        tool=name,
                        arguments=arguments,
                        result_status="denied",
                        authorization=permission,
                    )
                )
                session.persist()
                return fail("DENIED", f"{name} is {permission}")
            try:
                result = fn(*args, **kwargs)
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                result = fail("SOURCE_UNAVAILABLE", f"{name} unavailable: {exc}")
            status = "success" if result.get("ok") else "error"
            session.record_audit(
                AuditRecord(
                    id=new_id("aud"),
                    timestamp=ensure_tz(session.world.clock.now),
                    actor="agent",
                    tool=name,
                    arguments=arguments,
                    result_status=status,
                    authorization="allow",
                    commitment_id=arguments.get("commitment_id") or result.get("commitment_id"),
                    request_id=arguments.get("request_id"),
                )
            )
            session.persist()
            return result

        wrapper.__signature__ = inspect.signature(fn)
        return wrapper

    return decorator


def match_text(query: str, *parts: str) -> bool:
    tokens = [token.lower() for token in query.split() if token]
    haystack = " ".join(parts).lower()
    return all(token in haystack for token in tokens)


def snippet(text: str, length: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= length:
        return compact
    return compact[: length - 1] + "…"
