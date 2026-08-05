from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from watchlight.notifier.dedup import DedupGate
from watchlight.notifier.dnd import DoNotDisturbCalculator
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.deliveries import DeliveriesRepo
from watchlight.storage.repos.identity import IdentityRepo
from watchlight.storage.repos.signals import SignalsRepo
from watchlight.storage.repos.tasks import TasksRepo
from watchlight.storage.store import Store, utc_now

if TYPE_CHECKING:
    from watchlight.notifier.channels import ChannelAdapters


class Notifier:
    def __init__(
        self,
        store: Store,
        adapters: ChannelAdapters,
        *,
        max_attempts: int = 3,
    ) -> None:
        self.store = store
        self.adapters = adapters
        self.max_attempts = max_attempts
        self.dedup = DedupGate(store)
        self.dnd = DoNotDisturbCalculator()

    def enqueue(self, user_id: str, brief_id: str, *, now: int | None = None) -> list[str]:
        at = now or utc_now()
        brief = BriefsRepo.for_user(self.store, user_id).get(brief_id)
        if brief is None or not bool(brief["sendable"]):
            return []
        signal_ids = json.loads(str(brief["signal_ids_json"]))
        if not signal_ids:
            return []
        signal = SignalsRepo.for_user(self.store, user_id).get(str(signal_ids[0]))
        if signal is None:
            return []
        task = TasksRepo.for_user(self.store, user_id).get(str(signal["task_id"]))
        if task is None:
            return []
        policy = json.loads(str(task["notification_policy_json"]))
        user = IdentityRepo(self.store).get_user(user_id) or {"timezone": "UTC"}
        delayed_until = self.dnd.next_send_at(
            at, policy.get("do_not_disturb"), user_timezone=str(user["timezone"])
        )
        facts = json.loads(str(brief["facts_json"]))
        sources = json.loads(str(brief["source_refs_json"]))
        text = self._render(str(task["target"]), facts, sources)
        delivery_ids: list[str] = []
        channels = list(dict.fromkeys(str(item) for item in policy.get("channels", [])))
        bound_count = len(IdentityRepo(self.store).list_bound(user_id)) or len(channels)
        for channel_key in channels[:bound_count]:
            if not self.dedup.check(user_id, str(signal["signal_id"]), channel_key):
                continue
            delivery = DeliveriesRepo.for_user(self.store, user_id).insert(
                {
                    "signal_id": signal["signal_id"],
                    "brief_id": brief_id,
                    "channel_key": channel_key,
                    "status": "deferred" if delayed_until else "queued",
                    "scheduled_send_at": delayed_until or at,
                    "last_error": json.dumps({"pending_text": text}, ensure_ascii=False),
                }
            )
            delivery_ids.append(str(delivery["delivery_id"]))
        return delivery_ids

    async def drain_due(self, now: int | None = None) -> list[str]:
        at = now or utc_now()
        delivered: list[str] = []
        for user_id in DeliveriesRepo.owners_with_due(self.store, at):
            repo = DeliveriesRepo.for_user(self.store, user_id)
            for item in repo.find_due(at):
                delivery_id = str(item["delivery_id"])
                attempts = int(item["attempts"]) + 1
                try:
                    payload = json.loads(str(item["last_error"] or "{}"))
                    text = str(payload.get("pending_text", "Watchlight 有新的重要变化。"))
                    await self.adapters.get(str(item["channel_key"])).send(user_id, text)
                except Exception as exc:
                    if attempts < self.max_attempts:
                        repo.update_status(
                            delivery_id,
                            "retry",
                            attempts=attempts,
                            last_error=f"{type(exc).__name__}: {exc}",
                            scheduled_send_at=at + min(5 * (2 ** (attempts - 1)), 60),
                        )
                    else:
                        repo.update_status(
                            delivery_id,
                            "failed",
                            attempts=attempts,
                            last_error=f"{type(exc).__name__}: {exc}",
                        )
                    continue
                repo.update_status(
                    delivery_id, "delivered", attempts=attempts, last_error=None, sent_at=at
                )
                delivered.append(delivery_id)
                SignalsRepo.for_user(self.store, user_id).update_status(
                    str(item["signal_id"]), "notified", at
                )
        return delivered

    @staticmethod
    def _render(task_name: str, facts: list[Any], sources: list[Any]) -> str:
        fact_text = "\n".join(f"- {item}" for item in facts)
        source_text = "\n".join(f"- {item}" for item in sources)
        return f"{task_name}\n\n发生了什么：\n{fact_text}\n\n来源：\n{source_text}"
