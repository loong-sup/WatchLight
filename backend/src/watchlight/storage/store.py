from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


def utc_now() -> int:
    return int(time.time())


def new_id() -> str:
    """Return a lexically time-ordered identifier suitable for SQLite TEXT keys."""
    timestamp = int(time.time() * 1000)
    return f"{timestamp:012x}{uuid.uuid4().hex[12:]}"


class Store:
    """Small SQLite unit-of-work used by Watchlight business repositories."""

    def __init__(self, connection: sqlite3.Connection, path: str) -> None:
        self._connection = connection
        self.path = path
        self._lock = threading.RLock()
        self._closed = False

    @classmethod
    def open(cls, path: str | Path) -> Store:
        value = str(path)
        if value != ":memory:":
            Path(value).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(value, check_same_thread=False, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = NORMAL")
        if value != ":memory:":
            connection.execute("PRAGMA journal_mode = WAL")
        return cls(connection, value)

    @property
    def connection(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("store is closed")
        return self._connection

    def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self.connection.execute(sql, params)

    def executemany(self, sql: str, values: Sequence[Sequence[Any]]) -> sqlite3.Cursor:
        with self._lock:
            return self.connection.executemany(sql, values)

    def fetchone(
        self, sql: str, params: Sequence[Any] | dict[str, Any] = ()
    ) -> sqlite3.Row | None:
        return cast("sqlite3.Row | None", self.execute(sql, params).fetchone())

    def fetchall(
        self, sql: str, params: Sequence[Any] | dict[str, Any] = ()
    ) -> list[sqlite3.Row]:
        return list(self.execute(sql, params).fetchall())

    @contextmanager
    def transaction(self) -> Iterator[Store]:
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self
            except BaseException:
                self.connection.execute("ROLLBACK")
                raise
            else:
                self.connection.execute("COMMIT")

    def migrate(self) -> None:
        from watchlight.storage.migrations import migrate

        migrate(self)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
