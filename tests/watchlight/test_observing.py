from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from test_scheduler_service import complete_draft
from watchlight.observing import Observing, Redactor
from watchlight.observing.metrics import Metrics
from watchlight.observing.trace import TraceService
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.deliveries import DeliveriesRepo
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.signals import SignalsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo
from watchlight.storage.repos.tasks import TasksRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


def test_observing_requires_trace_keys_and_redacts(store: Store, user_id: str) -> None:
    observing = Observing(store)
    with pytest.raises(ValueError, match="task_id"):
        observing.emit({"user_id": user_id, "execution_id": "e"})
    event = observing.emit(
        {
            "user_id": user_id,
            "task_id": "t",
            "execution_id": "e",
            "event_type": "test",
            "stage": "collector",
            "payload": {"api_key": "secret"},
        }
    )
    assert "REDACTED" in str(event["payload_json"])
    assert Redactor().redact({"password": "x"})["password"] == "[REDACTED]"


def test_trace_reaches_snapshot_and_metrics_have_all_names(store: Store, user_id: str) -> None:
    task = TasksRepo.for_user(store, user_id).create(complete_draft())
    execution = ExecutionsRepo.for_user(store, user_id).insert(
        str(task["task_id"]), str(task["current_version_id"]), 1
    )
    snapshots = SnapshotsRepo.for_user(store, user_id)
    snapshot = snapshots.insert_snapshot(
        {
            "execution_id": execution["execution_id"],
            "source_url": "https://example.com",
            "captured_at": 1,
            "content_hash": "hash",
            "raw_ref": "r.raw",
            "normalized_ref": "n.normalized",
        }
    )
    change = snapshots.insert_change(
        {
            "execution_id": execution["execution_id"],
            "snapshot_id": snapshot["snapshot_id"],
            "change_type": "added",
            "evidence_ref": "release",
            "uncertainty_level": "low",
        }
    )
    signal = SignalsRepo.for_user(store, user_id).insert(
        {
            "execution_id": execution["execution_id"],
            "task_id": task["task_id"],
            "change_ids": [change["change_id"]],
            "source_urls": ["https://example.com"],
            "dedup_key": "key",
        }
    )
    brief = BriefsRepo.for_user(store, user_id).insert(
        {
            "execution_id": execution["execution_id"],
            "signal_ids": [signal["signal_id"]],
            "source_refs": ["https://example.com"],
            "captured_at": 1,
            "sendable": True,
        }
    )
    delivery = DeliveriesRepo.for_user(store, user_id).insert(
        {
            "signal_id": signal["signal_id"],
            "brief_id": brief["brief_id"],
            "channel_key": "web",
            "scheduled_send_at": 1,
        }
    )
    trace = TraceService(store).trace_delivery(user_id, str(delivery["delivery_id"]))
    assert trace["snapshots"][0]["snapshot_id"] == snapshot["snapshot_id"]
    assert set(Metrics(store).snapshot(user_id)) == set(Metrics.NAMES)
