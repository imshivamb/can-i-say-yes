"""CLI: python -m agent.cli "Can we deliver this by September 18?" """

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from adapters.files.runtime import reset_runtime
from adapters.files.store import read_seed_commitment_ids
from adapters.files.world import DATA_ROOT, load_world
from agent.agent import invoke, pretty_assessment
from agent.clock import advance_clock
from agent.human import approve_decision, fulfill_approved_option, open_decision
from agent.offline import run_recorded_investigation
from agent.session import AgentSession
from domain.fixtures import ACME_REQUEST_TEXT, acme_campaign_request

TOOL_LABELS = {
    "get_commitments": "Checked existing commitments",
    "get_capacity": "Checked team capacity",
    "get_supplier_status": "Checked supplier availability",
    "get_dependencies": "Checked customer dependencies",
    "search_email": "Checked customer dependencies",
    "search_documents": "Checked documents",
    "get_calendar": "Checked calendar",
    "get_project_state": "Checked projects",
    "calculate_schedule": "Checked project schedule",
    "check_conflicts": "Checked project schedule",
    "find_alternatives": "Found alternatives",
    "request_human_decision": "Opened decision card",
    "create_commitment": "Created commitment",
    "monitor_commitment": "Watching commitment",
    "send_customer_message": "Queued customer message",
}


def _tool_printer() -> Callable[..., None]:
    seen: list[str] = []

    def handler(**kwargs: object) -> None:
        current = kwargs.get("current_tool_use")
        if not isinstance(current, dict):
            return
        name = current.get("name")
        if not isinstance(name, str) or name in seen:
            return
        seen.append(name)
        print(f"✓ {TOOL_LABELS.get(name, name)}", flush=True)

    return handler


def _new_session(*, persist: bool) -> AgentSession:
    session = AgentSession(
        world=load_world(),
        data_root=DATA_ROOT if persist else None,
        seed_commitment_ids=read_seed_commitment_ids(DATA_ROOT),
    )
    if persist:
        session.load_runtime()
    return session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Can I Say Yes? — check a customer request")
    parser.add_argument(
        "text",
        nargs="?",
        default=ACME_REQUEST_TEXT,
        help="Customer request text",
    )
    parser.add_argument(
        "--recorded",
        action="store_true",
        help="Replay the tool investigation without calling Bedrock",
    )
    parser.add_argument(
        "--approve",
        metavar="OPTION_ID",
        help="After assess, approve this option (e.g. alt_a) and persist the commitment",
    )
    parser.add_argument(
        "--advance",
        metavar="JUMP",
        help="Advance the simulation clock (supplier_delay, plus_1_day, plus_3_days, or ISO time)",
    )
    args = parser.parse_args(argv)

    only_advance = bool(args.advance) and not args.approve
    if args.approve:
        reset_runtime(DATA_ROOT)

    session = _new_session(persist=bool(args.approve or args.advance))
    if only_advance:
        return _run_advance(session, args.advance)
    print("Parsing request…", flush=True)
    if args.recorded:
        parsed = session.put_request(acme_campaign_request())
        print("✓ Parsed request", flush=True)
        print(
            f"  {parsed.customer_name} · due {parsed.deadline} · {parsed.scope_summary}",
            flush=True,
        )
        print("Investigating…", flush=True)
        assessment = run_recorded_investigation(session, parsed)
        for name in session.tool_names:
            print(f"✓ {TOOL_LABELS.get(name, name)}", flush=True)
    else:
        parsed = invoke(session, "parse_request", prompt=args.text)
        print("✓ Parsed request", flush=True)
        print(
            f"  {parsed.customer_name} · due {parsed.deadline} · {parsed.scope_summary}",
            flush=True,
        )
        print("Investigating…", flush=True)
        assessment = invoke(
            session,
            "assess_feasibility",
            request=parsed,
            callback_handler=_tool_printer(),
        )
    print(f"\n{assessment.decision}", flush=True)
    print(pretty_assessment(assessment))

    if not args.approve and not args.advance:
        return 0

    if not args.approve:
        return _run_advance(session, args.advance)

    print("\nOpening decision card…", flush=True)
    decision = open_decision(
        session,
        assessment,
        reason="Original Sept 18 date is unsafe. Choose how to proceed.",
    )
    print(f"✓ Decision {decision.id} · recommended {decision.recommended_option_id}", flush=True)
    print(f"Approving {args.approve}…", flush=True)
    try:
        approve_decision(session, decision.id, args.approve)
    except ValueError as exc:
        print(f"Could not approve {args.approve}: {exc}", flush=True)
        return 1
    print(f"✓ Approved {args.approve}", flush=True)
    fulfill_approved_option(session, decision.id)
    for name in session.tool_names:
        if name in {
            "request_human_decision",
            "create_commitment",
            "monitor_commitment",
            "send_customer_message",
        }:
            print(f"✓ {TOOL_LABELS[name]}", flush=True)
    commitment = next(
        item for item in session.world.commitments if item.request_id == assessment.request_id
    )
    message = session.outbox[-1]
    print(
        f"\nCommitment {commitment.id} · {commitment.status} · "
        f"{commitment.health} · due {commitment.committed_deadline}",
        flush=True,
    )
    print(f"Outbox → {message.to}\n{message.body}", flush=True)
    if args.advance:
        return _run_advance(session, args.advance)
    return 0


def _run_advance(session: AgentSession, jump: str) -> int:
    print(f"\nAdvancing clock → {jump}…", flush=True)
    opened = advance_clock(session, jump, recorded=True)
    print(f"✓ Clock {session.world.clock.now.isoformat()}", flush=True)
    frame = next(
        (item for item in session.world.suppliers if item.id == "sup_frame_grain"),
        None,
    )
    if frame is not None:
        print(f"✓ Frame & Grain available from {frame.available_from}", flush=True)
    event = next((item for item in session.world.events if item.id == "evt_supplier_delay"), None)
    if event is not None and event.consumed:
        print("✓ Consumed evt_supplier_delay", flush=True)
    for commitment in session.world.commitments:
        if commitment.request_id == "req_acme_001":
            print(
                f"\nCommitment {commitment.id} · {commitment.status} · "
                f"{commitment.health} · forecast {commitment.current_forecast} · "
                f"due {commitment.committed_deadline}",
                flush=True,
            )
    if not opened:
        print("No new human decision.", flush=True)
        return 0
    for decision in opened:
        recommended = next(
            (item for item in decision.options if item.id == decision.recommended_option_id),
            None,
        )
        cost = recommended.extra_cost.amount if recommended else 0
        print(
            f"Decision {decision.id} · recommended {decision.recommended_option_id} · ₹{cost}",
            flush=True,
        )
        print(decision.reason, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
