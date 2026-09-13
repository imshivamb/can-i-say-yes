# Can I Say Yes?

**Before you promise a customer, let the agent check reality.**

An autonomous commitment-feasibility agent for small professional-services teams.

A customer asks, “Can you have this by Friday?” Answering that requires checking current work, people, existing commitments, suppliers, calendars, files, and dependencies. That picture is usually assembled by hand. This agent investigates it, returns **SAFE / UNSAFE / UNKNOWN** with evidence, proposes alternatives when the answer is no, and keeps watching after a commitment is made.

> Capacity software tells you what capacity you have.
> This agent investigates whether a **specific promise** is safe to make.

**Track:** Professional Agents — [Agents for Humans Hackathon](https://agentsforhumans.devpost.com/)

## Live demo

Press **Reset** first. This is a shared demo world.

4-click replay:

1. Reset
2. Check feasibility
3. Approve option A
4. Send supplier update, then approve the backup editor

Each live step calls a Strands agent. The public API is App Runner. The same
container also runs on Amazon Bedrock AgentCore; the API calls
`InvokeAgentRuntime` when `CISAY_AGENTCORE_RUNTIME_ARN` is set.

- UI: https://can-i-say-yes.vercel.app
- API: pending AWS deploy (`project-dev` currently lacks ECR / AgentCore / App Runner IAM)

## Status

The deterministic Sprints 0–5 loop is complete: the Investigator returns an
evidence-backed `UNSAFE`, a human approves an alternative, and the Monitor
re-evaluates a supplier delay into an `AT_RISK` decision. The HTTP API,
Gmail/Calendar/SES adapters, exactly-two-agent boundary, hook enforcement, and
30-case deterministic evaluation suite are also implemented. Live AWS
credentials and AgentCore deployment are environment-dependent.

```text
source .venv/bin/activate   # Python 3.12
pytest -q
python -m agent.cli --recorded
# With Bedrock credentials:
python -m agent.cli
# Run the deterministic proof suite:
python -m evals.run
# Start the local API:
uvicorn agent.server:app --reload --port 8080
```

## Product in one loop

Customer request → investigate scattered evidence → feasibility decision → human approval → commitment → background watch → world changes → re-evaluate → escalate only if a decision is required.

## Judge replay

```text
POST /api/demo/reset
POST /api/requests {"text":"...","recorded":true}
POST /api/requests/{request_id}/assess?recorded=true
POST /api/decisions/{decision_id}/approve {"option_id":"alt_a"}
POST /api/clock/advance {"to":"2026-09-19T10:00:00+05:30"}
```

The simulation clock is a deterministic fallback. The primary live path polls
Gmail for an inbound supplier message, reads Google Calendar as the live
capacity evidence source, and sends approved customer messages through SES.

## Simulated company

The demo world is **Northstar Creative**, a 10-person digital agency. The
canonical customer is **Acme Foods**. This is a bounded operational world with
provider ports, not a fake Salesforce integration. External messages remain
untrusted data.

## Measured local proof

The current deterministic suite reports 30 scenarios, including 5 prompt
injection cases. Run `python -m evals.run` to regenerate the local result; do
not copy a result into submission text until it has been rerun after the final
changes.

## License

MIT
