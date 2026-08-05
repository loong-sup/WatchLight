from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Sequence

    from watchlight.storage.store import Store


_USER_FILTER = re.compile(r"\buser_id\b", re.IGNORECASE)


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


@dataclass(slots=True)
class Repo:
    store: Store
    user_id: str

    def _assert_user_filter(self, sql: str) -> None:
        operation = sql.lstrip().split(maxsplit=1)[0].upper()
        if operation in {"SELECT", "UPDATE", "DELETE"} and not _USER_FILTER.search(sql):
            raise ValueError("repository query must include a user_id filter")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        self._assert_user_filter(sql)
        return self.store.execute(sql, (*params, self.user_id))

    def one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        self._assert_user_filter(sql)
        return row_dict(self.store.fetchone(sql, (*params, self.user_id)))

    def all(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        self._assert_user_filter(sql)
        return [dict(row) for row in self.store.fetchall(sql, (*params, self.user_id))]


__all__ = ["Repo", "row_dict"]
