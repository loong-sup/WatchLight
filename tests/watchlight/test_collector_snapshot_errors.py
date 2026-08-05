from __future__ import annotations

from typing import TYPE_CHECKING

from test_scheduler_service import complete_draft
from watchlight.collector.snapshot import SnapshotWriter
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage import Store


def test_identical_content_does_not_duplicate_snapshot(
    store: Store, user_id: str, tmp_path: Path
) -> None:
    service = TaskService(store)
    created = service.create(user_id, complete_draft())
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=0)
    execution = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)[0]
    writer = SnapshotWriter(store, tmp_path)
    first = writer.write(user_id, str(execution["execution_id"]), "https://example.com", "<p>A</p>")
    second = writer.write(
        user_id, str(execution["execution_id"]), "https://example.com", "<p>A</p>"
    )
    assert first.status == "ok"
    assert second.status == "unchanged"
    snapshots = SnapshotsRepo.for_user(store, user_id).list_for_execution(
        str(execution["execution_id"])
    )
    assert len(snapshots) == 1
