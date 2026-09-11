# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：创建 Web 应用并挂载路由。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""FastAPI application factory."""

import hashlib
import hmac
import json
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.responses import PlainTextResponse

from watchlight.channels.wecom.crypto import WeComCryptoError, WeComSignatureError
from watchlight.contracts.config.types_watchlight import WatchlightConfig
from watchlight.core.logging import get_logger
from watchlight.gateway.boot import GatewayRuntime
from watchlight.gateway.boot_watchshed import WatchlightServices, bootstrap_watchlight
from watchlight.gateway.http.health import router as health_router
from watchlight.gateway.http.security import setup_security
from watchlight.gateway.methods.agent import handle_agent, handle_agent_wait
from watchlight.gateway.methods.channels import handle_channels_status
from watchlight.gateway.methods.config import (
    handle_config_apply,
    handle_config_get,
    handle_config_patch,
    handle_config_set,
)
from watchlight.gateway.methods.models import handle_models_list
from watchlight.gateway.methods.registry import MethodRegistry
from watchlight.gateway.methods.sessions import (
    handle_sessions_abort,
    handle_sessions_archive,
    handle_sessions_compact,
    handle_sessions_create,
    handle_sessions_delete,
    handle_sessions_list,
    handle_sessions_patch,
    handle_sessions_preview,
    handle_sessions_reset,
    handle_sessions_send,
)
from watchlight.gateway.methods.tools import handle_tools_catalog, handle_tools_effective
from watchlight.gateway.methods.watch_delivery import router as watch_delivery_router
from watchlight.gateway.methods.watch_exec import router as watch_exec_router
from watchlight.gateway.methods.watch_identity import router as watch_identity_router
from watchlight.gateway.methods.watch_signals import router as watch_signals_router
from watchlight.gateway.methods.watch_tasks import router as watch_tasks_router
from watchlight.gateway.state import GatewayRuntimeState
from watchlight.gateway.websocket.handler import handle_websocket

log = get_logger("gateway.app")


def create_method_registry() -> MethodRegistry:
    registry = MethodRegistry()
    registry.register("config.get", handle_config_get)
    registry.register("config.set", handle_config_set)
    registry.register("config.apply", handle_config_apply)
    registry.register("config.patch", handle_config_patch)
    registry.register("sessions.list", handle_sessions_list)
    registry.register("sessions.create", handle_sessions_create)
    registry.register("sessions.send", handle_sessions_send)
    registry.register("sessions.abort", handle_sessions_abort)
    registry.register("sessions.patch", handle_sessions_patch)
    registry.register("sessions.compact", handle_sessions_compact)
    registry.register("sessions.preview", handle_sessions_preview)
    registry.register("sessions.archive", handle_sessions_archive)
    registry.register("sessions.delete", handle_sessions_delete)
    registry.register("sessions.reset", handle_sessions_reset)
    registry.register("agent", handle_agent)
    registry.register("agent.wait", handle_agent_wait)
    registry.register("tools.catalog", handle_tools_catalog)
    registry.register("tools.effective", handle_tools_effective)
    registry.register("channels.status", handle_channels_status)
    registry.register("models.list", handle_models_list)
    return registry


def create_app(config: WatchlightConfig | None = None, boot: bool = True) -> FastAPI:
    """Create the FastAPI application with all routes.

    Args:
        config: Config to use. Defaults to empty config.
        boot: Whether to boot the full runtime (providers, channels, etc.).
              Set to False for testing.
    """
    actual_config = config or WatchlightConfig()

    gateway_runtime: GatewayRuntime | None = None
    watchlight_services: WatchlightServices | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        nonlocal gateway_runtime, watchlight_services
        if boot:
            gateway_runtime = GatewayRuntime(actual_config)
            gateway_runtime.attach_event_clients(state.connected_clients)
            gateway_runtime.boot()
            await gateway_runtime.start_channels()
            app.state.gateway_runtime = gateway_runtime
            # Wire runtime ref to state so method handlers can access it
            state._gateway_runtime_ref = gateway_runtime  # type: ignore[attr-defined]
            if actual_config.watchshed is None or actual_config.watchshed.enabled:
                watchlight_services = bootstrap_watchlight(actual_config, gateway_runtime)
                app.state.watchlight_mvp = watchlight_services
                gateway_runtime.watchlight_mvp = watchlight_services
                await watchlight_services.start()
            log.info("gateway_started")
        yield
        if watchlight_services:
            await watchlight_services.stop()
        if gateway_runtime:
            await gateway_runtime.stop_channels()
            log.info("gateway_stopped")

    app = FastAPI(title="Watchlight Gateway", version="0.1.0", lifespan=lifespan)
    state = GatewayRuntimeState(config=actual_config)
    method_registry = create_method_registry()

    app.state.gateway_state = state
    app.state.method_registry = method_registry

    # HTTP routes
    setup_security(app)
    app.include_router(health_router)
    app.include_router(watch_tasks_router)
    app.include_router(watch_exec_router)
    app.include_router(watch_signals_router)
    app.include_router(watch_delivery_router)
    app.include_router(watch_identity_router)

    @app.get("/api/config")
    async def get_config() -> dict[str, object]:
        return {"config": state.config.model_dump(exclude_none=True, by_alias=True)}

    @app.patch("/api/config")
    async def patch_config(patch: dict[str, object]) -> dict[str, object]:
        return {"ok": True}

    @app.get("/api/sessions")
    async def get_sessions() -> dict[str, object]:
        if hasattr(app.state, "gateway_runtime") and app.state.gateway_runtime:
            rt = app.state.gateway_runtime
            items = rt.session_store.list(limit=100)
            sessions = []
            for key, entry in items:
                raw = entry.model_dump(exclude_none=True, by_alias=True)
                raw["key"] = key
                sessions.append(raw)
            return {"sessions": sessions, "total": rt.session_store.count}
        return {"sessions": [], "total": 0}

    @app.get("/api/models")
    async def get_models() -> dict[str, object]:
        if hasattr(app.state, "gateway_runtime") and app.state.gateway_runtime:
            return {"models": app.state.gateway_runtime.provider_registry.all_models()}
        return {"models": []}

    @app.get("/api/channels/status")
    async def channels_status() -> dict[str, object]:
        if hasattr(app.state, "gateway_runtime") and app.state.gateway_runtime:
            return {"channels": app.state.gateway_runtime.channel_registry.status()}
        return {"channels": []}

    @app.post("/internal/channels/feishu/events")
    async def feishu_internal_event(request: Request) -> dict[str, object]:
        """Receive Feishu events from a local sidecar or test harness."""
        runtime = getattr(app.state, "gateway_runtime", None)
        if runtime is None:
            raise HTTPException(status_code=503, detail="gateway runtime not started")

        secret = os.environ.get("WATCHLIGHT_FEISHU_INTERNAL_SECRET", "")
        if not secret:
            raise HTTPException(status_code=503, detail="feishu internal secret not configured")

        body = await request.body()
        signature = request.headers.get("x-watchlight-signature", "")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if signature.startswith("sha256="):
            signature = signature[len("sha256=") :]
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="invalid signature")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail="invalid json") from e
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be an object")

        account_id = payload.get("accountId") or payload.get("account_id") or "default"
        if not isinstance(account_id, str) or not account_id:
            raise HTTPException(status_code=400, detail="invalid account id")
        handled = await runtime.handle_feishu_sidecar_event(account_id, payload)
        return {"ok": True, "handled": handled}

    def _wecom_runtime() -> GatewayRuntime:
        runtime = getattr(app.state, "gateway_runtime", None)
        if runtime is None:
            raise HTTPException(status_code=503, detail="gateway runtime not started")
        return runtime

    def _wecom_query(request: Request) -> tuple[str, str, str]:
        signature = request.query_params.get("msg_signature", "")
        timestamp = request.query_params.get("timestamp", "")
        nonce = request.query_params.get("nonce", "")
        if not signature or not timestamp or not nonce:
            raise HTTPException(status_code=400, detail="missing WeCom callback parameters")
        return signature, timestamp, nonce

    async def _verify_wecom(request: Request, account_id: str) -> PlainTextResponse:
        signature, timestamp, nonce = _wecom_query(request)
        echo_str = request.query_params.get("echostr", "")
        if not echo_str:
            raise HTTPException(status_code=400, detail="missing echostr")
        try:
            plain = _wecom_runtime().verify_wecom_callback(
                account_id,
                signature=signature,
                timestamp=timestamp,
                nonce=nonce,
                echo_str=echo_str,
            )
        except WeComSignatureError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except WeComCryptoError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PlainTextResponse(plain)

    async def _receive_wecom(request: Request, account_id: str) -> Response:
        signature, timestamp, nonce = _wecom_query(request)
        body = await request.body()
        if len(body) > 1024 * 1024:
            raise HTTPException(status_code=413, detail="WeCom callback body is too large")
        try:
            await _wecom_runtime().handle_wecom_callback(
                account_id,
                signature=signature,
                timestamp=timestamp,
                nonce=nonce,
                body=body,
            )
        except WeComSignatureError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except WeComCryptoError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        # AI 运行在插件创建的后台任务中；先快速返回空包，避免企业微信超时重试。
        return Response(status_code=200)

    @app.get("/api/channels/wecom/events")
    async def verify_wecom_default(request: Request) -> PlainTextResponse:
        return await _verify_wecom(request, "default")

    @app.post("/api/channels/wecom/events")
    async def receive_wecom_default(request: Request) -> Response:
        return await _receive_wecom(request, "default")

    @app.get("/api/channels/wecom/{account_id}/events")
    async def verify_wecom_account(request: Request, account_id: str) -> PlainTextResponse:
        return await _verify_wecom(request, account_id)

    @app.post("/api/channels/wecom/{account_id}/events")
    async def receive_wecom_account(request: Request, account_id: str) -> Response:
        return await _receive_wecom(request, account_id)

    @app.get("/api/schema")
    async def get_schema() -> dict[str, object]:
        """Return JSON Schema for key models — contract alignment with frontend."""
        from watchlight.contracts.channel.plugin import InboundMessage, OutboundMessage
        from watchlight.contracts.protocol.frames import EventFrame, RequestFrame, ResponseFrame
        from watchlight.contracts.session.entry import SessionEntry

        return {
            "SessionEntry": SessionEntry.model_json_schema(),
            "InboundMessage": InboundMessage.model_json_schema(),
            "OutboundMessage": OutboundMessage.model_json_schema(),
            "RequestFrame": RequestFrame.model_json_schema(),
            "ResponseFrame": ResponseFrame.model_json_schema(),
            "EventFrame": EventFrame.model_json_schema(),
        }

    @app.get("/api/status")
    async def get_status() -> dict[str, object]:
        return {"snapshot": state.build_snapshot()}

    @app.get("/api/diagnostics")
    async def get_diagnostics() -> dict[str, object]:
        from watchlight.gateway.diagnostics import GatewayDiagnostics

        rt = getattr(app.state, "gateway_runtime", None)
        diag = GatewayDiagnostics(actual_config, runtime=rt)
        report = diag.run_all()
        return report.to_dict()

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        await handle_websocket(ws, state, method_registry.as_dict())

    return app
