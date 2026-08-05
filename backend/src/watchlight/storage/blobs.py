from __future__ import annotations

from typing import TYPE_CHECKING

from watchlight.storage.store import Store, utc_now

if TYPE_CHECKING:
    from pathlib import Path


class BlobStore:
    def __init__(self, store: Store, root: Path) -> None:
        self.store = store
        self.root = root

    def put(self, blob_id: str, kind: str, content: bytes) -> str:
        ref = f"{blob_id}.{kind}"
        path = self.root / blob_id[:2] / ref
        existing = self.store.fetchone(
            "SELECT ref FROM snapshot_blobs WHERE blob_id = ?", (blob_id,)
        )
        if existing is not None:
            return str(existing["ref"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        self.store.execute(
            "INSERT INTO snapshot_blobs(blob_id, kind, created_at, ref) VALUES (?,?,?,?)",
            (blob_id, kind, utc_now(), ref),
        )
        return ref

    def get(self, ref: str) -> bytes:
        blob_id = ref.split(".", 1)[0]
        return (self.root / blob_id[:2] / ref).read_bytes()
