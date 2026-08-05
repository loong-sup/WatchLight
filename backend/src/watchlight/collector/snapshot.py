from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from watchlight.storage.blobs import BlobStore
from watchlight.storage.repos.snapshots import SnapshotsRepo
from watchlight.storage.store import new_id, utc_now

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage.store import Store


_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def normalize_content(content: str) -> str:
    return _SPACE.sub(" ", _TAG.sub(" ", content)).strip()


@dataclass(frozen=True, slots=True)
class SnapshotWriteResult:
    status: str
    snapshot_id: str | None
    previous_snapshot_id: str | None
    content_hash: str


class SnapshotWriter:
    def __init__(self, store: Store, blob_root: Path) -> None:
        self.store = store
        self.blobs = BlobStore(store, blob_root)

    def write(
        self,
        user_id: str,
        execution_id: str,
        source_url: str,
        raw: str,
        *,
        captured_at: int | None = None,
    ) -> SnapshotWriteResult:
        at = captured_at or utc_now()
        normalized = normalize_content(raw)
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        repo = SnapshotsRepo.for_user(self.store, user_id)
        previous = repo.latest_for_url(source_url)
        if previous is not None and previous["content_hash"] == digest:
            return SnapshotWriteResult(
                "unchanged", None, str(previous["snapshot_id"]), digest
            )
        snapshot_id = new_id()
        raw_ref = self.blobs.put(f"{snapshot_id}r", "raw", raw.encode())
        normalized_ref = self.blobs.put(f"{snapshot_id}n", "normalized", normalized.encode())
        repo.insert_snapshot(
            {
                "snapshot_id": snapshot_id,
                "execution_id": execution_id,
                "source_url": source_url,
                "captured_at": at,
                "content_hash": digest,
                "raw_ref": raw_ref,
                "normalized_ref": normalized_ref,
                "previous_snapshot_id": previous["snapshot_id"] if previous else None,
            }
        )
        return SnapshotWriteResult(
            "changed" if previous else "ok",
            snapshot_id,
            str(previous["snapshot_id"]) if previous else None,
            digest,
        )
