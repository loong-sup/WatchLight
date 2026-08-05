from __future__ import annotations

from typing import TYPE_CHECKING

from conftest import task_fields
from watchlight.storage.repos.identity import IdentityRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


def test_task_version_history_and_soft_delete(store: Store, user_id: str) -> None:
    repo = TasksRepo.for_user(store, user_id)
    task = repo.create(task_fields())
    task_id = str(task["task_id"])
    updated = repo.update(task_id, {"target": "Watch important Python releases"})
    assert updated["version"] == 2
    assert [row["version"] for row in repo.version_history(task_id)] == [1, 2]
    repo.set_status(task_id, "deleted")
    assert repo.get(task_id) is None
    assert repo.get(task_id, include_deleted=True) is not None


def test_begin_draining_is_atomic_and_user_scoped(store: Store, user_id: str) -> None:
    repo = TasksRepo.for_user(store, user_id)
    active = repo.create(task_fields(target="Active"), status="active")
    paused = repo.create(task_fields(target="Paused"), status="paused")
    draining = repo.create(task_fields(target="Draining"), status="draining")
    deleted = repo.create(task_fields(target="Deleted"), status="paused")
    repo.set_status(str(deleted["task_id"]), "deleted")
    other_user = str(IdentityRepo(store).create_user("Other")["user_id"])
    other = TasksRepo.for_user(store, other_user).create(
        task_fields(target="Other"), status="active"
    )

    assert repo.begin_draining(str(active["task_id"]))["status"] == "draining"  # type: ignore[index]
    assert repo.begin_draining(str(paused["task_id"]))["status"] == "draining"  # type: ignore[index]
    assert repo.begin_draining(str(draining["task_id"])) is None
    assert repo.begin_draining(str(deleted["task_id"])) is None
    assert repo.begin_draining(str(other["task_id"])) is None
    assert repo.begin_draining("missing") is None
    assert TasksRepo.for_user(store, other_user).get(str(other["task_id"]))["status"] == "active"  # type: ignore[index]
