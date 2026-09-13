from pathlib import Path

from adapters.files.store import read_seed_commitment_ids
from adapters.files.store import read_runtime
from adapters.files.world import DATA_ROOT, load_world
from agent import agent as agent_module
from agent.config import cors_origins
from agent.runtime import apply_session_snapshot, session_snapshot, should_invoke_agentcore
from agent.session import AgentSession
from domain.fixtures import acme_campaign_request
from domain.ids import new_id
from domain.models import ActivityItem, SimulationClock


def _session(tmp_path: Path) -> AgentSession:
    return AgentSession(
        world=load_world(),
        data_root=tmp_path,
        seed_commitment_ids=read_seed_commitment_ids(DATA_ROOT),
    )


def test_should_invoke_agentcore_only_when_arn_is_set_on_product_api(monkeypatch) -> None:
    monkeypatch.delenv("CISAY_AGENTCORE_RUNTIME_ARN", raising=False)
    monkeypatch.delenv("CISAY_AGENTCORE_SELF", raising=False)
    assert should_invoke_agentcore() is False

    monkeypatch.setenv("CISAY_AGENTCORE_RUNTIME_ARN", "arn:aws:bedrock-agentcore:us-east-1:1:runtime/x")
    assert should_invoke_agentcore() is True

    monkeypatch.setenv("CISAY_AGENTCORE_SELF", "1")
    assert should_invoke_agentcore() is False


def test_cors_origins_read_from_env(monkeypatch) -> None:
    monkeypatch.setenv("CISAY_CORS_ORIGINS", "https://demo.example, http://localhost:3000")
    assert cors_origins() == ["https://demo.example", "http://localhost:3000"]


def test_session_snapshot_round_trip_keeps_clock_and_request(tmp_path: Path) -> None:
    session = _session(tmp_path)
    request = session.put_request(acme_campaign_request())
    snapshot = session_snapshot(session)

    remote = _session(tmp_path / "remote")
    apply_session_snapshot(remote, snapshot)
    apply_session_snapshot(remote, {"request": request.model_dump(mode="json")})

    assert remote.world.clock == session.world.clock
    assert remote.requests[request.id].customer_name == "Acme Foods"


def test_invoke_uses_agentcore_when_runtime_arn_is_set(tmp_path: Path, monkeypatch) -> None:
    session = _session(tmp_path)
    request = acme_campaign_request()
    captured: dict[str, object] = {}

    def fake_invoke_agentcore(kind: str, snapshot: dict, extra: dict) -> dict:
        captured["kind"] = kind
        captured["snapshot"] = snapshot
        captured["extra"] = extra
        return request.model_dump(mode="json")

    monkeypatch.setenv("CISAY_AGENTCORE_RUNTIME_ARN", "arn:aws:bedrock-agentcore:us-east-1:1:runtime/x")
    monkeypatch.delenv("CISAY_AGENTCORE_SELF", raising=False)
    monkeypatch.setattr(agent_module, "invoke_agentcore", fake_invoke_agentcore)

    parsed = agent_module.invoke(session, "parse_request", prompt="hello")

    assert captured["kind"] == "parse_request"
    assert captured["extra"]["prompt"] == "hello"
    assert isinstance(captured["snapshot"]["clock"], dict)
    assert parsed.id == request.id
    assert session.requests[request.id].customer_name == "Acme Foods"


def test_read_runtime_uses_default_clock_when_runtime_is_empty(tmp_path: Path) -> None:
    (tmp_path / "runtime").mkdir()
    state = read_runtime(tmp_path)
    assert state.clock.timezone == "Asia/Kolkata"
    assert state.commitments == []


def test_apply_session_snapshot_replaces_clock(tmp_path: Path) -> None:
    session = _session(tmp_path)
    apply_session_snapshot(
        session,
        {"clock": SimulationClock(now=session.world.clock.now).model_dump(mode="json")},
    )
    assert session.world.clock.timezone == "Asia/Kolkata"


def test_persist_activity_writes_only_the_activity_file(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session.activity.append(
        ActivityItem(
            id=new_id("aud"),
            timestamp=session.world.clock.now,
            text="get_capacity started",
        )
    )
    session.persist_activity()

    remote = _session(tmp_path)
    remote.load_runtime()
    assert remote.activity[-1].text == "get_capacity started"
    assert not (tmp_path / "runtime" / "commitments.json").exists()
