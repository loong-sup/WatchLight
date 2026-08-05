# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：处理会话相关接口。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway sessions.* method handlers."""

from typing import Any

from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.connection import GatewayWsClient
from watchlight.gateway.websocket.frames import make_event


def _get_runtime(state: GatewayRuntimeState) -> Any:
    return getattr(state, "_gateway_runtime_ref", None)


async def handle_sessions_list(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = _get_runtime(state)
    if runtime is None:
        return {"sessions": [], "total": 0}
    items = runtime.session_store.list(limit=params.get("limit"), offset=params.get("offset", 0))
    sessions = []
    for key, entry in items:
        raw: dict[str, Any] = entry.model_dump(exclude_none=True, by_alias=True)
        raw["key"] = key
        sessions.append(raw)
    return {"sessions": sessions, "total": runtime.session_store.count}


async def handle_sessions_create(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = _get_runtime(state)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}
    key = params.get("sessionKey", "")
    entry = runtime.session_store.create(key, label=params.get("label"))
    runtime.session_store.save()
    result: dict[str, Any] = entry.model_dump(exclude_none=True, by_alias=True)
    return result


async def handle_sessions_send(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    """Trigger agent run via shared run_agent_for_session, stream back to client."""
    runtime = _get_runtime(state)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}

    session_key = params.get("sessionKey", "main")
    message = params.get("message", "")
    user_id: str | None = None

    async def on_text_delta(text: str) -> None:
        await client.send_json(
            make_event(
                "agent.event",
                {
                    "type": "text_delta",
                    "sessionKey": session_key,
                    "text": text,
                },
            )
        )

    services = runtime.watchlight_mvp
    if services is not None:
        identity = services.identity.resolve_or_register(
            "webchat", "web-admin", display_name="Web Admin"
        )
        if identity.user_id is None:
            return {
                "ok": False,
                "error": {"code": "IDENTITY_PENDING", "message": identity.status},
            }
        user_id = identity.user_id
        nl_reply = await services.nl_tasks.handle_async(
            user_id,
            "webchat",
            str(message),
            conversation_id=str(session_key),
        )
        if nl_reply is not None:
            runtime.record_session_exchange(
                session_key,
                str(message),
                nl_reply,
                channel="webchat",
            )
            await on_text_delta(nl_reply)
            await client.send_json(
                make_event(
                    "agent.event",
                    {"type": "complete", "sessionKey": session_key},
                )
            )
            return {
                "ok": True,
                "sessionKey": session_key,
                "inputTokens": 0,
                "outputTokens": 0,
            }

    result = await runtime.run_agent_for_session(
        session_key=session_key,
        user_message=message,
        channel="webchat",
        sender_id="web-admin",
        conversation_id=session_key,
        user_id=user_id,
        on_text_delta=on_text_delta,
    )

    await client.send_json(
        make_event(
            "agent.event",
            {
                "type": "complete",
                "sessionKey": session_key,
            },
        )
    )

    return {
        "ok": True,
        "sessionKey": session_key,
        "inputTokens": result.input_tokens,
        "outputTokens": result.output_tokens,
    }


async def handle_sessions_abort(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = _get_runtime(state)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}
    session_key = params.get("sessionKey", "")
    rt = runtime.runtime_registry.get()
    if rt is not None:
        for run_id in list(getattr(rt, "_active_runs", {}).keys()):
            await rt.abort(run_id)
    runtime.session_store.update(session_key, {"status": "done"})
    runtime.session_store.save()
    return {"ok": True, "sessionKey": session_key}


async def handle_sessions_patch(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = _get_runtime(state)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}
    session_key = params.get("sessionKey", "")
    patch = params.get("patch", {})
    entry = runtime.session_store.update(session_key, patch)
    if entry:
        runtime.session_store.save()
        return {"ok": True}
    return {
        "ok": False,
        "error": {"code": "NOT_FOUND", "message": f"session {session_key} not found"},
    }


async def handle_sessions_compact(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    """Compact a transcript and write back an agent-aware summary checkpoint."""
    runtime = _get_runtime(state)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}

    session_key = params.get("sessionKey", "")
    reason = params.get("reason", "manual")
    entry = runtime.session_store.get(session_key)
    if entry is None:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "session not found"}}

    messages = runtime.transcript_manager.read_raw(entry.session_id)
    if len(messages) <= 12:
        return {"ok": True, "note": "too few messages to compact"}

    # Build summarize function using best available provider
    provider = runtime.provider_registry.get("dashscope")
    if provider is None:
        for pid in runtime.provider_registry.list_ids():
            provider = runtime.provider_registry.get(pid)
            if provider:
                break

    from watchlight.agents.runtime.embedded.compaction import (
        COMPACTION_SYSTEM_PROMPT,
        compact_messages,
    )

    async def summarize_fn(text: str) -> str:
        if provider is None:
            return f"[Structured summary of {len(messages)} messages — no LLM provider available]"
        parts: list[str] = []
        async for chunk in provider.create_stream(
            model="qwen-max",
            messages=[{"role": "user", "content": text}],
            system=COMPACTION_SYSTEM_PROMPT,
        ):
            if chunk.get("type") == "text_delta":
                parts.append(chunk.get("text", ""))
        return "".join(parts)

    result = await compact_messages(messages, summarize_fn=summarize_fn, reason=reason)

    # Write compacted messages back
    runtime.transcript_manager.clear(entry.session_id)
    for msg in messages:
        runtime.transcript_manager.append(entry.session_id, msg)

    # Persist checkpoint
    count = (entry.compaction_count or 0) + 1
    if hasattr(runtime, "compaction_store") and runtime.compaction_store:
        from watchlight.agents.runtime.embedded.compaction import build_compaction_checkpoint

        quality = 1.0
        if messages and isinstance(messages[0], dict):
            quality = messages[0].get("_compaction", {}).get("quality_score", 1.0)
        checkpoint = build_compaction_checkpoint(result, reason=reason, quality=quality)
        runtime.compaction_store.append(entry.session_id, checkpoint)

    runtime.session_store.update(session_key, {"compactionCount": count})
    runtime.session_store.save()

    return {
        "ok": True,
        "messagesBefore": result.messages_before,
        "messagesAfter": result.messages_after,
        "compactionCount": count,
    }


async def handle_sessions_preview(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = _get_runtime(state)
    if runtime is None:
        return {"messages": []}
    session_key = params.get("sessionKey", "")
    limit = params.get("limit", 20)
    entry = runtime.session_store.get(session_key)
    if entry is None:
        return {"messages": []}
    raw = runtime.transcript_manager.read_raw(entry.session_id)
    messages = raw[-limit:] if len(raw) > limit else raw
    return {"messages": messages, "total": len(raw)}


async def handle_sessions_delete(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = _get_runtime(state)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}
    ok = runtime.session_store.delete(params.get("sessionKey", ""))
    if ok:
        runtime.session_store.save()
    return {"ok": ok}


async def handle_sessions_reset(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = _get_runtime(state)
    if runtime is None:
        return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "no runtime"}}
    entry = runtime.session_store.reset(params.get("sessionKey", ""))
    if entry:
        runtime.session_store.save()
    return {"ok": entry is not None}
