from __future__ import annotations

import json
import uuid
from typing import Any

import boto3

from agent.config import agentcore_runtime_arn, aws_region, is_agentcore_self
from agent.session import AgentSession
from domain.models import Commitment, ParsedRequest, SimulationClock, Supplier, WorldEvent


def should_invoke_agentcore() -> bool:
    return bool(agentcore_runtime_arn()) and not is_agentcore_self()


def session_snapshot(session: AgentSession) -> dict[str, Any]:
    return {
        "clock": session.world.clock.model_dump(mode="json"),
        "suppliers": [item.model_dump(mode="json") for item in session.world.suppliers],
        "events": [item.model_dump(mode="json") for item in session.world.events],
        "commitments": [item.model_dump(mode="json") for item in session.world.commitments],
        "requests": [item.model_dump(mode="json") for item in session.requests.values()],
    }


def apply_session_snapshot(session: AgentSession, data: dict[str, Any]) -> None:
    if clock := data.get("clock"):
        session.world.clock = SimulationClock.model_validate(clock)
    if suppliers := data.get("suppliers"):
        session.world.suppliers = [Supplier.model_validate(item) for item in suppliers]
    if events := data.get("events"):
        session.world.events = [WorldEvent.model_validate(item) for item in events]
    if commitments := data.get("commitments"):
        by_id = {item.id: item for item in session.world.commitments}
        for item in commitments:
            commitment = Commitment.model_validate(item)
            by_id[commitment.id] = commitment
        session.world.commitments = list(by_id.values())
    if request := data.get("request"):
        session.put_request(ParsedRequest.model_validate(request))
    for item in data.get("requests") or []:
        session.put_request(ParsedRequest.model_validate(item))
    if commitment := data.get("commitment"):
        incoming = Commitment.model_validate(commitment)
        session.world.commitments = [
            incoming if item.id == incoming.id else item for item in session.world.commitments
        ]
        if not any(item.id == incoming.id for item in session.world.commitments):
            session.world.commitments.append(incoming)


def _read_runtime_body(response: dict[str, Any]) -> dict[str, Any]:
    stream = response.get("response")
    if stream is None:
        raise RuntimeError("AgentCore response did not include a body")
    chunks: list[bytes] = []
    if hasattr(stream, "iter_chunks"):
        chunks.extend(chunk for chunk in stream.iter_chunks() if chunk)
    elif hasattr(stream, "read"):
        body = stream.read()
        if body:
            chunks.append(body if isinstance(body, bytes) else str(body).encode())
    else:
        for chunk in stream:
            if chunk:
                chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode())
    if not chunks:
        raise RuntimeError("AgentCore response body was empty")
    parsed = json.loads(b"".join(chunks).decode())
    if not isinstance(parsed, dict):
        raise RuntimeError("AgentCore response was not a JSON object")
    return parsed


def invoke_agentcore(kind: str, snapshot: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    runtime_arn = agentcore_runtime_arn()
    if not runtime_arn:
        raise RuntimeError("CISAY_AGENTCORE_RUNTIME_ARN is not set")
    client = boto3.client("bedrock-agentcore", region_name=aws_region())
    payload = {"input": {"kind": kind, **snapshot, **extra}}
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=str(uuid.uuid4()),
        qualifier="DEFAULT",
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(payload).encode(),
    )
    body = _read_runtime_body(response)
    output = body.get("output")
    if not isinstance(output, dict):
        raise RuntimeError(f"AgentCore response missing output: {body}")
    return output
