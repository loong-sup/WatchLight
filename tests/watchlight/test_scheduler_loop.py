from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from test_scheduler_service import complete_draft
from watchlight.scheduler.loop import SchedulerLoop
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.executions import ExecutionsRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


@pytest.mark.asyncio
async def test_tick_claims_only_one_execution_per_task(store: Store, user_id: str) -> None:
    service = TaskService(store)
    created = service.create(user_id, complete_draft())
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=0)
    service.trigger_now(user_id, created.task_id, now=1)
    claimed = await SchedulerLoop(store).tick(4000)
    assert len(claimed) == 1
    states = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)
    assert [row["status"] for row in states].count("running") == 1


def test_recover_stale_running(store: Store, user_id: str) -> None:
    service = TaskService(store)
    created = service.create(user_id, complete_draft())
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=0)
    repo = ExecutionsRepo.for_user(store, user_id)
    execution = repo.list_for_task(created.task_id)[0]
    assert repo.claim(str(execution["execution_id"]), 1)
    recovered = SchedulerLoop(store).recover(now=1000, heartbeat_timeout=600)
    assert recovered == [execution["execution_id"]]
    assert repo.get(str(execution["execution_id"]))["status"] == "recovered"  # type: ignore[index]


@pytest.mark.asyncio
async def test_draining_waits_for_running_execution_before_deletion(
    store: Store, user_id: str
) -> None:
    service = TaskService(store)
    created = service.create(user_id, complete_draft())
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=100)
    executions = ExecutionsRepo.for_user(store, user_id)
    execution = executions.list_for_task(created.task_id)[0]
    assert executions.claim(str(execution["execution_id"]), 101)
    assert service.confirm_delete(user_id, created.task_id)["status"] == "draining"  # type: ignore[index]

    await SchedulerLoop(store).tick(now=102)
    task = service.list(user_id)[0]
    assert task["status"] == "draining"

    executions.settle(str(execution["execution_id"]), "succeeded", now=103)
    await SchedulerLoop(store).tick(now=104)
    assert service.list(user_id) == []
