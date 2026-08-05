from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from watchlight.storage.repos import Repo
from watchlight.storage.repos.identity import IdentityRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.storage import Store

from conftest import task_fields


def test_task_queries_are_isolated_by_user(store: Store) -> None:
    identities = IdentityRepo(store)
    user_a = str(identities.create_user("A")["user_id"])
    user_b = str(identities.create_user("B")["user_id"])
    task = TasksRepo.for_user(store, user_a).create(task_fields())
    assert TasksRepo.for_user(store, user_b).get(str(task["task_id"])) is None
    assert TasksRepo.for_user(store, user_b).list() == []


def test_repo_rejects_unscoped_read(store: Store, user_id: str) -> None:
    repo = Repo(store, user_id)
    with pytest.raises(ValueError, match="user_id"):
        repo.one("SELECT * FROM watch_tasks")
