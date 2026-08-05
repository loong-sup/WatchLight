from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.deliveries import DeliveriesRepo
from watchlight.storage.repos.signals import SignalsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo

if TYPE_CHECKING:
    from watchlight.storage.store import Store


class TraceService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def trace_delivery(self, user_id: str, delivery_id: str) -> dict[str, Any]:
        delivery = DeliveriesRepo.for_user(self.store, user_id).get(delivery_id)
        if delivery is None:
            raise KeyError(delivery_id)
        brief = BriefsRepo.for_user(self.store, user_id).get(str(delivery["brief_id"]))
        signal = SignalsRepo.for_user(self.store, user_id).get(str(delivery["signal_id"]))
        if brief is None or signal is None:
            raise RuntimeError("trace chain is incomplete")
        change_ids = json.loads(str(signal["change_ids_json"]))
        changes = [
            dict(row)
            for change_id in change_ids
            if (
                row := self.store.fetchone(
                    "SELECT * FROM changes WHERE change_id=? AND user_id=?", (change_id, user_id)
                )
            )
            is not None
        ]
        snapshot_repo = SnapshotsRepo.for_user(self.store, user_id)
        snapshots = [
            snapshot
            for change in changes
            if (snapshot := snapshot_repo.get_snapshot(str(change["snapshot_id"]))) is not None
        ]
        return {
            "delivery": delivery,
            "brief": brief,
            "signal": signal,
            "changes": changes,
            "snapshots": snapshots,
            "source_urls": json.loads(str(signal["source_urls_json"])),
        }
