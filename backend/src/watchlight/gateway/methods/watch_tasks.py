from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from watchlight.gateway.methods.watch_common import services_from_request, user_from_request
from watchlight.storage.repos.tasks import TasksRepo

router = APIRouter(prefix="/api/watch/tasks", tags=["watch-tasks"])


@router.get("")
async def list_tasks(request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    user_id = user_from_request(request)
    return {"tasks": TasksRepo.for_user(services.store, user_id).list()}


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    user_id = user_from_request(request)
    task = TasksRepo.for_user(services.store, user_id).get(task_id)
    if task is not None:
        return {"task": task}
    exists = services.store.fetchone(
        "SELECT 1 FROM watch_tasks WHERE task_id=? AND user_id!=?", (task_id, user_id)
    )
    if exists is not None:
        raise HTTPException(status_code=403, detail="task belongs to another user")
    raise HTTPException(status_code=404, detail="task not found")


@router.post("")
async def create_task(request: Request, draft: dict[str, Any]) -> dict[str, Any]:
    services = services_from_request(request)
    result = services.tasks.create(user_from_request(request), draft)
    return {
        "task_id": result.task_id,
        "normalized_summary": result.normalized_summary,
        "missing_fields": result.missing_fields,
        "normalized_version_id": result.normalized_version_id,
        "error": result.error,
    }


@router.post("/{task_id}/confirm")
async def confirm_task(task_id: str, request: Request, body: dict[str, Any]) -> dict[str, Any]:
    task = services_from_request(request).tasks.confirm(
        user_from_request(request), task_id, str(body["normalized_version_id"])
    )
    return {"task": task}


@router.patch("/{task_id}")
async def update_task(task_id: str, request: Request, body: dict[str, Any]) -> dict[str, Any]:
    task = services_from_request(request).tasks.update(user_from_request(request), task_id, body)
    return {"task": task}


@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request) -> dict[str, Any]:
    task = services_from_request(request).tasks.delete(user_from_request(request), task_id)
    return {"task": task}


@router.post("/{task_id}/{action}")
async def task_action(task_id: str, action: str, request: Request) -> dict[str, Any]:
    services = services_from_request(request)
    user_id = user_from_request(request)
    if action == "pause":
        return {"task": services.tasks.pause(user_id, task_id)}
    if action == "resume":
        return {"task": services.tasks.resume(user_id, task_id)}
    if action == "trigger":
        return {"execution_id": services.tasks.trigger_now(user_id, task_id)}
    raise HTTPException(status_code=404, detail="unknown task action")
