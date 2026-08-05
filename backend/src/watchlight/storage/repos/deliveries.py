from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import builtins

from watchlight.storage.repos import Repo
from watchlight.storage.store import Store, new_id


class DeliveriesRepo(Repo):
    @classmethod
    def for_user(cls, store: Store, user_id: str) -> DeliveriesRepo:
        return cls(store, user_id)

    def insert(self, values: dict[str, Any]) -> dict[str, Any]:
        delivery_id = str(values.get("delivery_id") or new_id())
        self.store.execute(
            "INSERT INTO deliveries(delivery_id,signal_id,brief_id,channel_key,user_id,status,"
            "attempts,last_error,scheduled_send_at,sent_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                delivery_id,
                values["signal_id"],
                values["brief_id"],
                values["channel_key"],
                self.user_id,
                values.get("status", "queued"),
                values.get("attempts", 0),
                values.get("last_error"),
                values["scheduled_send_at"],
                values.get("sent_at"),
            ),
        )
        result = self.get(delivery_id)
        assert result is not None
        return result

    def get(self, delivery_id: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM deliveries WHERE delivery_id=? AND user_id=?", (delivery_id,)
        )

    def for_signal_channel(self, signal_id: str, channel_key: str) -> dict[str, Any] | None:
        return self.one(
            "SELECT * FROM deliveries WHERE signal_id=? AND channel_key=? AND user_id=?",
            (signal_id, channel_key),
        )

    def list(self) -> builtins.list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM deliveries WHERE user_id=? ORDER BY scheduled_send_at DESC"
        )

    def find_due(self, now: int) -> builtins.list[dict[str, Any]]:
        return self.all(
            "SELECT * FROM deliveries WHERE status IN ('queued','retry','deferred') "
            "AND scheduled_send_at<=? AND user_id=? ORDER BY scheduled_send_at",
            (now,),
        )

    def update_status(
        self,
        delivery_id: str,
        status: str,
        *,
        attempts: int | None = None,
        last_error: str | None = None,
        sent_at: int | None = None,
        scheduled_send_at: int | None = None,
    ) -> None:
        current = self.get(delivery_id)
        if current is None:
            raise KeyError(delivery_id)
        self.store.execute(
            "UPDATE deliveries SET status=?,attempts=?,last_error=?,sent_at=?,"
            "scheduled_send_at=? WHERE delivery_id=? AND user_id=?",
            (
                status,
                attempts if attempts is not None else current["attempts"],
                last_error,
                sent_at,
                scheduled_send_at
                if scheduled_send_at is not None
                else current["scheduled_send_at"],
                delivery_id,
                self.user_id,
            ),
        )

    @staticmethod
    def owners_with_due(store: Store, now: int) -> builtins.list[str]:
        return [
            str(row["user_id"])
            for row in store.fetchall(
                "SELECT DISTINCT user_id FROM deliveries WHERE "
                "status IN ('queued','retry','deferred') AND scheduled_send_at<=?",
                (now,),
            )
        ]
