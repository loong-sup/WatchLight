from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import TYPE_CHECKING

from watchlight.storage.blobs import BlobStore
from watchlight.storage.repos.snapshots import SnapshotsRepo
from watchlight.storage.store import new_id, utc_now

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage.store import Store


_SPACE = re.compile(r"[^\S\r\n]+")
_HTML_HINT = re.compile(
    r"<!doctype\s+html|<(?:html|head|body|main|article|section|div|p|h[1-6]|ul|ol|li|"
    r"table|tr|td|style|script|template|svg|noscript)(?:\s|>|/)",
    re.IGNORECASE,
)
_IGNORED_TAGS = {
    "style",
    "script",
    "noscript",
    "template",
    "svg",
    "canvas",
    "iframe",
    "object",
}
_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
NORMALIZER_VERSION = 2


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        normalized = tag.lower()
        if self._ignored_depth:
            self._ignored_depth += 1
        elif normalized in _IGNORED_TAGS:
            self._ignored_depth = 1
        elif normalized in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if not self._ignored_depth and tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            self._ignored_depth -= 1
        elif tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _clean_lines(content: str) -> str:
    lines = (_SPACE.sub(" ", line).strip() for line in content.splitlines())
    return "\n".join(line for line in lines if line)


def normalize_content(content: str) -> str:
    if not _HTML_HINT.search(content):
        return _clean_lines(content)
    parser = _VisibleTextParser()
    parser.feed(content)
    parser.close()
    return _clean_lines("".join(parser.parts))


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
        previous = repo.latest_for_url(source_url, NORMALIZER_VERSION)
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
                "normalizer_version": NORMALIZER_VERSION,
            }
        )
        return SnapshotWriteResult(
            "changed" if previous else "ok",
            snapshot_id,
            str(previous["snapshot_id"]) if previous else None,
            digest,
        )
