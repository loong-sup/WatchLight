from __future__ import annotations

from typing import Any

from watchlight.storage.repos import Repo
from watchlight.storage.store import Store, new_id


class SnapshotsRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> SnapshotsRepo:
        return cls(store, user_id)

    def insert_hit(self, values: dict[str, Any]) -> dict[str, Any]:
        hit_id = str(values.get("hit_id") or new_id())
        self.store.execute(
            "INSERT INTO source_hits(hit_id,execution_id,user_id,source_url,fetched_at,status,"
            "http_status,snapshot_id,error_code,retry_count,robots_disallowed) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                hit_id,
                values["execution_id"],
                self.user_id,
                values["source_url"],
                values.get("fetched_at"),
                values["status"],
                values.get("http_status"),
                values.get("snapshot_id"),
                values.get("error_code"),
                values.get("retry_count", 0),
                int(bool(values.get("robots_disallowed", False))),
            ),
        )
        result = self.one("SELECT * FROM source_hits WHERE hit_id=? AND user_id=?", (hit_id,))
        assert result is not None
        return result

    def update_hit(self, hit_id: str, **values: Any) -> None:
        allowed = {
            "fetched_at",
            "status",
            "http_status",
            "snapshot_id",
            "error_code",
            "retry_count",
            "robots_disallowed",
        }
        fields = [name for name in values if name in allowed]
        if not fields:
            return
        sql = ",".join(f"{name}=?" for name in fields)
        params = [
            int(values[name]) if name == "robots_disallowed" else values[name] for name in fields
        ]
        self.store.execute(
            f"UPDATE source_hits SET {sql} WHERE hit_id=? AND user_id=?",
            (*params, hit_id, self.user_id),
        )

    def hits_for_execution(self, execution_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM source_hits WHERE execution_id=? AND user_id=? ORDER BY fetched_at",
            (execution_id,),
        )

    def latest_for_url(self, source_url: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM snapshots WHERE source_url=? AND user_id=? "
            "ORDER BY captured_at DESC LIMIT 1",
            (source_url,),
        )

    def insert_snapshot(self, values: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = str(values.get("snapshot_id") or new_id())
        self.store.execute(
            "INSERT INTO snapshots(snapshot_id,user_id,execution_id,source_url,captured_at,"
            "content_hash,raw_ref,normalized_ref,previous_snapshot_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                snapshot_id,
                self.user_id,
                values["execution_id"],
                values["source_url"],
                values["captured_at"],
                values["content_hash"],
                values["raw_ref"],
                values["normalized_ref"],
                values.get("previous_snapshot_id"),
            ),
        )
        result = self.one(
            "SELECT * FROM snapshots WHERE snapshot_id=? AND user_id=?", (snapshot_id,)
        )
        assert result is not None
        return result

    def list_for_execution(self, execution_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM snapshots WHERE execution_id=? AND user_id=? ORDER BY captured_at",
            (execution_id,),
        )

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM snapshots WHERE snapshot_id=? AND user_id=?", (snapshot_id,)
        )

    def insert_change(self, values: dict[str, Any]) -> dict[str, Any]:
        change_id = str(values.get("change_id") or new_id())
        self.store.execute(
            "INSERT INTO changes(change_id,user_id,execution_id,snapshot_id,previous_snapshot_id,"
            "change_type,evidence_ref,uncertainty_level) VALUES (?,?,?,?,?,?,?,?)",
            (
                change_id,
                self.user_id,
                values["execution_id"],
                values["snapshot_id"],
                values.get("previous_snapshot_id"),
                values["change_type"],
                values["evidence_ref"],
                values["uncertainty_level"],
            ),
        )
        result = self.one("SELECT * FROM changes WHERE change_id=? AND user_id=?", (change_id,))
        assert result is not None
        return result

    def changes_for_execution(self, execution_id: str) -> list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM changes WHERE execution_id=? AND user_id=? ORDER BY change_id",
            (execution_id,),
        )
