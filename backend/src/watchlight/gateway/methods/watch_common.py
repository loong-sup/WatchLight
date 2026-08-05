from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import HTTPException, Request

if TYPE_CHECKING:
    from watchlight.gateway.boot_watchshed import WatchlightServices


def services_from_request(request: Request) -> WatchlightServices:
    services = getattr(request.app.state, "watchlight_mvp", None)
    if services is None:
        raise HTTPException(status_code=503, detail="Watchlight MVP is not started")
    return cast("WatchlightServices", services)


def user_from_request(request: Request) -> str:
    services = services_from_request(request)
    explicit = request.headers.get("x-watchlight-user-id")
    if explicit:
        if services.identity.repo.get_user(explicit) is None:
            raise HTTPException(status_code=401, detail="unknown user")
        return explicit
    channel_key = request.headers.get("x-watchlight-channel")
    channel_user = request.headers.get("x-watchlight-channel-user")
    if channel_key and channel_user:
        resolved = services.identity.resolve(channel_key, channel_user)
        if resolved.user_id:
            return resolved.user_id
    raise HTTPException(status_code=401, detail="user identity required")
