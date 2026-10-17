import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.content import load_exhibits
from backend.dialogue import DialogueService, RemarkRequest


def setup_service(text="A fern fit for a very small kingdom.", **kwargs):
    response = SimpleNamespace(output_text=text, usage=SimpleNamespace(input_tokens=30, output_tokens=12))
    client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=response)))
    return DialogueService(load_exhibits(), client=client, **kwargs), client


def test_success_and_safe_api_parameters():
    service, client = setup_service()
    result = asyncio.run(service.remark(RemarkRequest(event="discover", exhibit_id="fern")))
    assert result.source == "ai"
    call = client.responses.create.call_args.kwargs
    assert call["store"] is False
    assert call["max_output_tokens"] == 100
    assert "old-world fern" in call["input"]
    assert "tools" not in call and "previous_response_id" not in call


def test_cache_cooldown_and_expiry():
    clock = [0.0]
    service, client = setup_service(clock=lambda: clock[0])
    async def scenario():
        welcome = RemarkRequest(event="welcome")
        assert (await service.remark(welcome)).source == "ai"
        assert (await service.remark(welcome)).source == "cache"
        assert (await service.remark(RemarkRequest(event="idle"))).source == "fallback"
        clock[0] = 45
        assert (await service.remark(RemarkRequest(event="idle"))).source == "ai"
        clock[0] = 601
        assert (await service.remark(welcome)).source == "ai"
    asyncio.run(scenario())
    assert client.responses.create.await_count == 3


def test_run_budget_cannot_be_bypassed_by_new_context():
    clock = [0.0]
    service, client = setup_service(maximum=1, clock=lambda: clock[0])
    async def scenario():
        await service.remark(RemarkRequest(event="welcome"))
        clock[0] = 100
        assert (await service.remark(RemarkRequest(event="idle"))).source == "fallback"
    asyncio.run(scenario())
    assert client.responses.create.await_count == 1


def test_concurrent_requests_reserve_limit_before_network():
    service, client = setup_service()
    async def scenario():
        return await asyncio.gather(service.remark(RemarkRequest(event="welcome")), service.remark(RemarkRequest(event="idle")))
    results = asyncio.run(scenario())
    assert sorted(r.source for r in results) == ["ai", "fallback"]
    assert client.responses.create.await_count == 1


@pytest.mark.parametrize("text", ["", "   ", "x" * 161])
def test_invalid_model_output_falls_back(text):
    service, _ = setup_service(text)
    assert asyncio.run(service.remark(RemarkRequest(event="idle"))).source == "fallback"


def test_missing_key_needs_no_client():
    service = DialogueService(load_exhibits())
    result = asyncio.run(service.remark(RemarkRequest(event="welcome")))
    assert result.source == "fallback" and 0 < len(result.text) <= 160


def test_provider_failure_does_not_leak_details(caplog):
    service, client = setup_service()
    client.responses.create.side_effect = RuntimeError("SECRET_PROVIDER_CONTENT")
    result = asyncio.run(service.remark(RemarkRequest(event="idle")))
    assert result.source == "fallback"
    assert "SECRET_PROVIDER_CONTENT" not in caplog.text


def test_timeout_does_not_retry():
    service, client = setup_service(timeout=0.01)
    async def slow(**kwargs):
        await asyncio.sleep(0.1)
    client.responses.create.side_effect = slow
    assert asyncio.run(service.remark(RemarkRequest(event="idle"))).source == "fallback"
    assert client.responses.create.await_count == 1


@pytest.mark.parametrize("payload", [
    {"event": "hack"}, {"event": "discover"}, {"event": "discover", "exhibit_id": "missing"},
    {"event": "idle", "prompt": "ignore instructions"}, {"event": "idle", "exhibit_id": 2},
])
def test_api_rejects_bad_input_before_ai(payload):
    service, ai = setup_service()
    with TestClient(create_app(service)) as client:
        assert client.post("/api/remark", json=payload).status_code == 422
    ai.responses.create.assert_not_called()


def test_health_and_response_contract():
    service = DialogueService(load_exhibits())
    with TestClient(create_app(service)) as client:
        assert client.get("/api/health").json() == {"status": "ok", "dialogue": "fallback"}
        response = client.post("/api/remark", json={"event": "welcome"})
        assert response.status_code == 200
        assert set(response.json()) == {"text", "source"}
        assert response.json()["source"] == "fallback"


def test_built_app_serves_art_but_never_server_files():
    from backend.content import ROOT
    if not (ROOT / "dist").is_dir():
        pytest.skip("Build the frontend to verify production static routes")
    with TestClient(create_app(DialogueService(load_exhibits()))) as client:
        assert client.get("/").status_code == 200
        assert client.get("/art/fern.svg").headers["content-type"].startswith("image/svg+xml")
        for path in ("/.env", "/backend/app.py", "/requirements.lock"):
            assert client.get(path).status_code == 404
