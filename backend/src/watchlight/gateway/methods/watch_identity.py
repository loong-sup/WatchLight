from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from watchlight.gateway.methods.watch_common import services_from_request, user_from_request

router = APIRouter(prefix="/api/watch/identity", tags=["watch-identity"])


@router.post("/register")
async def register(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = services_from_request(request).identity.register(
            str(body["channel_key"]),
            str(body["channel_user_id"]),
            display_name=body.get("display_name"),
            timezone=str(body.get("timezone", "UTC")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"user_id": user_id}


@router.post("/binding/start")
async def binding_start(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    token = services_from_request(request).identity.start_binding(
        user_from_request(request), str(body["channel_key"]), str(body["channel_user_id"])
    )
    return {"token": token}


@router.post("/binding/confirm")
async def binding_confirm(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    user_id = services_from_request(request).identity.confirm_binding(
        str(body["token"]), str(body["via_channel_key"])
    )
    return {"user_id": user_id}


@router.post("/unbind/start")
async def unbind_start(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    token, impact = services_from_request(request).identity.start_unbind(
        user_from_request(request), str(body["channel_key"])
    )
    return {"token": token, "impact": asdict(impact)}


@router.post("/unbind/confirm")
async def unbind_confirm(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    user_id = services_from_request(request).identity.confirm_unbind(
        str(body["token"]), str(body["via_channel_key"])
    )
    return {"user_id": user_id}
