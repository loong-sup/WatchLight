from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from watchlight.gateway.methods.watch_common import services_from_request, user_from_request
from watchlight.observing.redact import Redactor
from watchlight.storage.repos.deliveries import DeliveriesRepo

router = APIRouter(prefix="/api/watch", tags=["watch-delivery"])


@router.get("/deliveries")
async def list_deliveries(request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    return {
        "deliveries": DeliveriesRepo.for_user(
            services.store, user_from_request(request)
        ).list()
    }


@router.post("/deliveries/{delivery_id}/feedback")
async def submit_feedback(
    delivery_id: str, request: Request, body: dict[str, Any]
) -> dict[str, Any]:
    feedback_id = services_from_request(request).feedback.submit(
        user_from_request(request), delivery_id, str(body["rating"]), body.get("reason")
    )
    return {"feedback_id": feedback_id}


@router.get("/metrics")
async def metrics(request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    return {"metrics": services.metrics.snapshot(user_from_request(request))}


@router.get("/export")
async def export(request: Request) -> dict[str, Any]:
    from watchlight.feedback.export import export_user_data

    services = services_from_request(request)
    return export_user_data(services.store, user_from_request(request), Redactor())
