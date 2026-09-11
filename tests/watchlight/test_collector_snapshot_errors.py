from __future__ import annotations

from typing import TYPE_CHECKING

from test_scheduler_service import complete_draft
from watchlight.collector.snapshot import NORMALIZER_VERSION, SnapshotWriter
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


def test_normalizer_upgrade_creates_baseline_before_detecting_changes(
    store: Store, user_id: str, tmp_path: Path
) -> None:
    service = TaskService(store)
    created = service.create(user_id, complete_draft())
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=0)
    execution = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)[0]
    execution_id = str(execution["execution_id"])
    snapshots = SnapshotsRepo.for_user(store, user_id)
    snapshots.insert_snapshot(
        {
            "snapshot_id": "legacy-snapshot",
            "execution_id": execution_id,
            "source_url": "https://example.com",
            "captured_at": 1,
            "content_hash": "legacy-hash",
            "raw_ref": "legacy.raw",
            "normalized_ref": "legacy.normalized",
            "normalizer_version": 1,
        }
    )
    writer = SnapshotWriter(store, tmp_path)

    baseline = writer.write(
        user_id, execution_id, "https://example.com", "<p>Readable baseline</p>", captured_at=2
    )
    changed = writer.write(
        user_id, execution_id, "https://example.com", "<p>Readable update</p>", captured_at=3
    )

    assert baseline.status == "ok"
    assert baseline.previous_snapshot_id is None
    assert changed.status == "changed"
    assert changed.previous_snapshot_id == baseline.snapshot_id
    current = snapshots.get_snapshot(str(changed.snapshot_id))
    assert current is not None
    assert current["normalizer_version"] == NORMALIZER_VERSION
