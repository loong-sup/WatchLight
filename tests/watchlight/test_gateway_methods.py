from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from watchlight.contracts.config.types_watchlight import WatchlightConfig, WatchshedConfig
from watchlight.gateway.app import create_app
from watchlight.gateway.boot import AgentRunResult, GatewayRuntime
from watchlight.gateway.boot_watchshed import bootstrap_watchlight
from watchlight.gateway.methods.sessions import handle_sessions_send
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.sessions.store import SessionStore
from watchlight.sessions.transcript import TranscriptManager


def test_gateway_task_identity_isolation_and_trace_route(tmp_path: Path) -> None:
    config = WatchlightConfig(
        watchshed=WatchshedConfig(
            dbPath=str(tmp_path / "watch.db"), blobRoot=str(tmp_path / "blobs")
        )
    )
    services = bootstrap_watchlight(config)
    user_a = services.identity.register("web", "alice")
    user_b = services.identity.register("web", "bob")
    app = create_app(config, boot=False)
    app.state.watchlight_mvp = services
    client = TestClient(app)
    headers_a = {"x-watchlight-user-id": user_a}
    draft = {
        "target": "Watch releases",
        "source_scope": {"urls": ["https://example.com/releases"]},
        "trigger_condition": {"must_contain": ["release"]},
        "frequency_seconds": 3600,
        "notification_policy": {"channels": ["web"], "immediate": True},
    }
    response = client.post("/api/watch/tasks", json=draft, headers=headers_a)
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    assert client.get(f"/api/watch/tasks/{task_id}", headers=headers_a).status_code == 200
    assert (
        client.get(
            f"/api/watch/tasks/{task_id}", headers={"x-watchlight-user-id": user_b}
        ).status_code
        == 403
    )
    assert client.get("/api/watch/tasks").status_code == 401
    assert client.get("/api/watch/trace/missing", headers=headers_a).status_code == 404
    deleted = client.delete(f"/api/watch/tasks/{task_id}", headers=headers_a)
    assert deleted.status_code == 200
    assert deleted.json()["task"]["status"] == "draining"
    services.store.close()


@pytest.mark.asyncio
async def test_web_deterministic_task_reply_is_recorded_once(tmp_path: Path) -> None:
    config = WatchlightConfig(
        watchshed=WatchshedConfig(
            dbPath=str(tmp_path / "watch.db"), blobRoot=str(tmp_path / "blobs")
        )
    )
    services = bootstrap_watchlight(config)
    runtime = object.__new__(GatewayRuntime)
    runtime.watchlight_mvp = services
    runtime.session_store = SessionStore(tmp_path / "state")
    runtime.transcript_manager = TranscriptManager(tmp_path / "state")
    runtime.run_agent_for_session = AsyncMock()
    state = GatewayRuntimeState(config)
    state._gateway_runtime_ref = runtime  # type: ignore[attr-defined]
    client = SimpleNamespace(send_json=AsyncMock())

    result = await handle_sessions_send(
        {"sessionKey": "web:test-tasks", "message": "当前有哪些任务"},
        client,
        state,
    )

    assert result["ok"] is True
    assert result["inputTokens"] == 0
    runtime.run_agent_for_session.assert_not_awaited()
    entry = runtime.session_store.get("web:test-tasks")
    assert entry is not None
    transcript = runtime.transcript_manager.read_raw(entry.session_id)
    assert [line["role"] for line in transcript] == ["user", "assistant"]
    assert transcript[0]["content"] == "当前有哪些任务"
    assert transcript[1]["content"] == "当前没有关注任务。"
    services.store.close()


@pytest.mark.asyncio
async def test_web_model_path_propagates_canonical_user_id(tmp_path: Path) -> None:
    config = WatchlightConfig(
        watchshed=WatchshedConfig(
            dbPath=str(tmp_path / "watch.db"), blobRoot=str(tmp_path / "blobs")
        )
    )
    services = bootstrap_watchlight(config)
    runtime = object.__new__(GatewayRuntime)
    runtime.watchlight_mvp = services
    runtime.run_agent_for_session = AsyncMock(return_value=AgentRunResult())
    state = GatewayRuntimeState(config)
    state._gateway_runtime_ref = runtime  # type: ignore[attr-defined]
    client = SimpleNamespace(send_json=AsyncMock())

    await handle_sessions_send(
        {"sessionKey": "web:ordinary", "message": "你好"},
        client,
        state,
    )

    kwargs = runtime.run_agent_for_session.await_args.kwargs
    resolved = services.identity.resolve("webchat", "web-admin")
    assert resolved.user_id is not None
    assert kwargs["user_id"] == resolved.user_id
    services.store.close()


@pytest.mark.asyncio
async def test_web_delete_confirmation_is_scoped_to_session(tmp_path: Path) -> None:
    config = WatchlightConfig(
        watchshed=WatchshedConfig(
            dbPath=str(tmp_path / "watch.db"), blobRoot=str(tmp_path / "blobs")
        )
    )
    services = bootstrap_watchlight(config)
    identity = services.identity.resolve_or_register("webchat", "web-admin")
    assert identity.user_id is not None
    created = services.tasks.create(
        identity.user_id,
        {
            "target": "Web Session Task",
            "source_scope": {"urls": [], "keywords": ["Web Session Task"]},
            "trigger_condition": {"must_contain": [], "must_not_contain": []},
            "frequency_seconds": 86400,
            "notification_policy": {"channels": ["web"], "immediate": True},
        },
    )
    assert created.task_id and created.normalized_version_id
    services.tasks.confirm(
        identity.user_id, created.task_id, created.normalized_version_id, now=100
    )
    runtime = object.__new__(GatewayRuntime)
    runtime.watchlight_mvp = services
    runtime.session_store = SessionStore(tmp_path / "state")
    runtime.transcript_manager = TranscriptManager(tmp_path / "state")
    runtime.run_agent_for_session = AsyncMock(return_value=AgentRunResult())
    state = GatewayRuntimeState(config)
    state._gateway_runtime_ref = runtime  # type: ignore[attr-defined]
    client = SimpleNamespace(send_json=AsyncMock())

    async def send(session_key: str, message: str) -> None:
        await handle_sessions_send(
            {"sessionKey": session_key, "message": message},
            client,
            state,
        )

    await send("web:delete-a", "删除任务")
    await send("web:delete-a", "Session")
    await send("web:delete-b", "确认删除")
    assert services.tasks.list(identity.user_id)[0]["status"] == "active"
    await send("web:delete-a", "确认删除")
    assert services.tasks.list(identity.user_id)[0]["status"] == "draining"
    runtime.run_agent_for_session.assert_not_awaited()
    services.store.close()
