from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from watchlight.storage.store import Store


class Metrics:
    NAMES = (
        "task_run_success_rate",
        "source_fail_rate",
        "signal_yield_rate",
        "delivery_success_rate",
        "duplicate_delivery_rate",
        "feedback_count",
    )

    def __init__(self, store: Store) -> None:
        self.store = store

    def snapshot(self, user_id: str | None = None) -> dict[str, float | int]:
        where = " WHERE user_id=?" if user_id else ""
        params = (user_id,) if user_id else ()
        execution = self.store.fetchone(
            f"SELECT COUNT(*) total,SUM(status='succeeded') ok FROM executions{where}", params
        )
        hits = self.store.fetchone(
            f"SELECT COUNT(*) total,SUM(status IN ('unreachable','blocked','unparseable')) bad "
            f"FROM source_hits{where}",
            params,
        )
        signals = self.store.fetchone(f"SELECT COUNT(*) total FROM signals{where}", params)
        deliveries = self.store.fetchone(
            f"SELECT COUNT(*) total,SUM(status='delivered') ok,SUM(status='suppressed') dup "
            f"FROM deliveries{where}",
            params,
        )
        feedback = self.store.fetchone(f"SELECT COUNT(*) total FROM feedbacks{where}", params)
        exec_total = int(execution["total"] or 0) if execution else 0
        hit_total = int(hits["total"] or 0) if hits else 0
        delivery_total = int(deliveries["total"] or 0) if deliveries else 0
        return {
            "task_run_success_rate": self._ratio(execution, "ok", exec_total),
            "source_fail_rate": self._ratio(hits, "bad", hit_total),
            "signal_yield_rate": self._ratio(signals, "total", exec_total),
            "delivery_success_rate": self._ratio(deliveries, "ok", delivery_total),
            "duplicate_delivery_rate": self._ratio(deliveries, "dup", delivery_total),
            "feedback_count": int(feedback["total"] or 0) if feedback else 0,
        }

    @staticmethod
    def _ratio(row: object, key: str, denominator: int) -> float:
        if row is None or denominator == 0:
            return 0.0
        from typing import Any, cast

        value = cast("Any", row)[key]
        return round(float(value or 0) / denominator, 4)
