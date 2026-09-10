from strands.hooks.events import BeforeToolCallEvent

from adapters.files.world import load_world
from agent.hooks import AuthorityAndTraceHooks
from agent.session import AgentSession, use_session


def test_strands_hook_blocks_consequential_write_without_human_decision() -> None:
    session = AgentSession(world=load_world())
    event = BeforeToolCallEvent(
        agent=None,  # type: ignore[arg-type]
        selected_tool=None,
        tool_use={
            "name": "create_commitment",
            "toolUseId": "tool-1",
            "input": {
                "request_id": "req_acme_001",
                "alternative_id": "alt_a",
            },
        },
        invocation_state={},
    )

    with use_session(session):
        AuthorityAndTraceHooks().before_tool_call(event)

    assert event.cancel_tool
    assert session.audit[-1].authorization == "require_human"
    assert session.audit[-1].result_status == "denied"

