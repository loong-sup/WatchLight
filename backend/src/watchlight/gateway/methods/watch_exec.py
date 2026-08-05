from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from watchlight.gateway.methods.watch_common import services_from_request, user_from_request
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo

router = APIRouter(prefix="/api/watch/executions", tags=["watch-executions"])


@router.get("")
async def list_executions(task_id: str, request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    return {
        "executions": ExecutionsRepo.for_user(
            services.store, user_from_request(request)
        ).list_for_task(task_id)
    }


@router.get("/{execution_id}")
async def get_execution(execution_id: str, request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    user_id = user_from_request(request)
    execution = ExecutionsRepo.for_user(services.store, user_id).get(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="execution not found")
    snapshots = SnapshotsRepo.for_user(services.store, user_id)
    return {
        "execution": execution,
        "source_hits": snapshots.hits_for_execution(execution_id),
        "snapshots": snapshots.list_for_execution(execution_id),
        "changes": snapshots.changes_for_execution(execution_id),
    }
