from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from watchlight.gateway.methods.watch_common import services_from_request, user_from_request
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.signals import SignalsRepo

router = APIRouter(prefix="/api/watch", tags=["watch-signals"])


@router.get("/signals")
async def list_signals(execution_id: str, request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    user_id = user_from_request(request)
    return {
        "signals": SignalsRepo.for_user(services.store, user_id).list_for_execution(
            execution_id
        ),
        "briefs": BriefsRepo.for_user(services.store, user_id).list_for_execution(
            execution_id
        ),
    }


@router.get("/trace/{delivery_id}")
async def trace_delivery(delivery_id: str, request: Request) -> dict[str, Any]:
    try:
        return services_from_request(request).trace.trace_delivery(
            user_from_request(request), delivery_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="delivery not found") from exc
