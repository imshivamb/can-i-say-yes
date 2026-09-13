import time

from fastapi.testclient import TestClient

from agent.server import app

client = TestClient(app)


def test_api_replays_full_recorded_commitment_loop(monkeypatch) -> None:
    monkeypatch.setenv("CISAY_RECORDED", "1")
    created = client.post(
        "/api/requests",
        json={"text": "Acme campaign request", "recorded": True},
    )
    assert created.status_code == 200
    request_id = created.json()["request"]["id"]

    assessed = client.post(f"/api/requests/{request_id}/assess?recorded=true")
    assert assessed.status_code == 200
    assert assessed.json()["assessment"]["decision"] == "UNSAFE"
    decision_id = assessed.json()["decision"]["id"]

    approved = client.post(
        f"/api/decisions/{decision_id}/approve",
        json={"option_id": "alt_a"},
    )
    assert approved.status_code == 200
    repeated = client.post(
        f"/api/decisions/{decision_id}/approve",
        json={"option_id": "alt_a"},
    )
    assert repeated.status_code == 200
    commitments = client.get("/api/commitments").json()
    assert any(
        item["request_id"] == request_id and item["committed_deadline"] == "2026-09-22"
        for item in commitments
    )
    event = client.post(
        "/api/events/inbound",
        json={
            "event_id": "evt_api_supplier_approved",
            "summary": "Editor availability slipped",
            "source_reference": "gmail:message-approved",
            "payload": {
                "supplier_id": "sup_frame_grain",
                "available_from": "2026-09-20",
            },
        },
    )
    assert event.json()["opened_decisions"] == 1


def test_api_async_job_polls_recorded_assess(monkeypatch) -> None:
    monkeypatch.setenv("CISAY_RECORDED", "1")
    created = client.post(
        "/api/requests",
        json={"text": "Acme campaign request", "recorded": True},
    )
    request_id = created.json()["request"]["id"]
    started = client.post(f"/api/requests/{request_id}/assess?recorded=true&async_job=true")
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "pending"
    job_id = body["job_id"]
    result = None
    for _ in range(40):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] == "done":
            result = job["result"]
            break
        if job["status"] == "error":
            raise AssertionError(job.get("detail"))
        time.sleep(0.05)
    assert result is not None
    assert result["assessment"]["decision"] == "UNSAFE"


def test_api_reports_health_and_deduplicates_inbound_events() -> None:
    assert client.get("/ping").json() == {"status": "Healthy"}
    payload = {
        "event_id": "evt_api_supplier_1",
        "summary": "Editor slipped to September 20",
        "source_reference": "gmail:message-1",
    }
    first = client.post("/api/events/inbound", json=payload)
    second = client.post("/api/events/inbound", json=payload)
    assert first.json()["status"] == "accepted"
    assert second.json()["status"] == "duplicate"


def test_api_allows_browser_preflight_from_local_ui() -> None:
    response = client.options(
        "/api/activity",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_world_sources_lists_six_seed_rows() -> None:
    body = client.get("/api/world/sources").json()
    assert [item["key"] for item in body] == [
        "people",
        "clients",
        "commitments",
        "suppliers",
        "calendar",
        "inbox",
    ]
    assert all(item["mode"] == "seed" for item in body)
    assert body[0]["count"] >= 1


def test_api_allows_browser_preflight_from_vercel() -> None:
    response = client.options(
        "/api/activity",
        headers={
            "Origin": "https://can-i-say-yes-abc123.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://can-i-say-yes-abc123.vercel.app"
    )

