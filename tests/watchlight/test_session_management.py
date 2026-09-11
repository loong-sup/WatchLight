from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from watchlight.contracts.config.types_watchlight import WatchlightConfig
from watchlight.gateway.methods.sessions import (
    handle_sessions_archive,
    handle_sessions_delete,
    handle_sessions_preview,
)
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.sessions.compaction import CompactionStore
from watchlight.sessions.store import SessionStore
from watchlight.sessions.transcript import TranscriptManager


def build_runtime(tmp_path: Path) -> SimpleNamespace:
    state_dir = tmp_path / "state"
    return SimpleNamespace(
        session_store=SessionStore(state_dir),
        transcript_manager=TranscriptManager(state_dir),
        compaction_store=CompactionStore(state_dir),
    )


def build_state(runtime: SimpleNamespace) -> GatewayRuntimeState:
    state = GatewayRuntimeState(WatchlightConfig())
    state._gateway_runtime_ref = runtime  # type: ignore[attr-defined]
    return state


@pytest.mark.asyncio
async def test_session_preview_archive_and_restore_preserve_transcript(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)
    entry = runtime.session_store.create("web:history", channel="webchat")
    runtime.transcript_manager.append(
        entry.session_id,
        {"role": "user", "content": "历史问题", "ts": 100},
    )
    runtime.transcript_manager.append(
        entry.session_id,
        {"role": "assistant", "content": "历史回答", "ts": 200},
    )
    runtime.session_store.save()
    state = build_state(runtime)
    client = SimpleNamespace(send_json=AsyncMock())

    preview = await handle_sessions_preview(
        {"sessionKey": "web:history", "limit": 20}, client, state
    )
    assert [message["content"] for message in preview["messages"]] == ["历史问题", "历史回答"]

    archived = await handle_sessions_archive(
        {"sessionKey": "web:history", "archived": True}, client, state
    )
    assert archived["ok"] is True
    assert runtime.session_store.get("web:history").archived_at is not None
    assert len(runtime.transcript_manager.read_raw(entry.session_id)) == 2

    restored = await handle_sessions_archive(
        {"sessionKey": "web:history", "archived": False}, client, state
    )
    assert restored["ok"] is True
    assert runtime.session_store.get("web:history").archived_at is None
    assert len(runtime.transcript_manager.read_raw(entry.session_id)) == 2


@pytest.mark.asyncio
async def test_session_delete_removes_metadata_and_transcript(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)
    entry = runtime.session_store.create("web:delete", channel="webchat")
    runtime.transcript_manager.append(entry.session_id, {"role": "user", "content": "删除我"})
    runtime.session_store.save()
    state = build_state(runtime)
    client = SimpleNamespace(send_json=AsyncMock())

    deleted = await handle_sessions_delete({"sessionKey": "web:delete"}, client, state)

    assert deleted == {"ok": True}
    assert runtime.session_store.get("web:delete") is None
    assert runtime.transcript_manager.read_raw(entry.session_id) == []


@pytest.mark.asyncio
async def test_running_session_cannot_be_archived_or_deleted(tmp_path: Path) -> None:
    runtime = build_runtime(tmp_path)
    runtime.session_store.create("web:running", channel="webchat")
    runtime.session_store.update("web:running", {"status": "running"})
    state = build_state(runtime)
    client = SimpleNamespace(send_json=AsyncMock())

    archived = await handle_sessions_archive(
        {"sessionKey": "web:running", "archived": True}, client, state
    )
    deleted = await handle_sessions_delete({"sessionKey": "web:running"}, client, state)

    assert archived["error"]["code"] == "SESSION_RUNNING"
    assert deleted["error"]["code"] == "SESSION_RUNNING"
    assert runtime.session_store.get("web:running") is not None
