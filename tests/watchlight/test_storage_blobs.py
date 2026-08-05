from __future__ import annotations

from typing import TYPE_CHECKING

from watchlight.storage.blobs import BlobStore

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage import Store


def test_blob_round_trip_is_append_only(store: Store, tmp_path: Path) -> None:
    blobs = BlobStore(store, tmp_path)
    ref = blobs.put("ab123", "raw", b"first")
    assert blobs.put("ab123", "raw", b"second") == ref
    assert blobs.get(ref) == b"first"
