from __future__ import annotations

from typing import TYPE_CHECKING, Any

from watchlight.observing.redact import Redactor
from watchlight.storage.repos.events import EventsRepo

if TYPE_CHECKING:
    from watchlight.storage.store import Store


class Observing:
    def __init__(self, store: Store, *, redactor: Redactor | None = None) -> None:
        self.store = store
        self.redactor = redactor or Redactor()

    def emit(self, event: dict[str, Any]) -> dict[str, Any]:
        missing = [name for name in ("user_id", "task_id", "execution_id") if name not in event]
        if missing:
            raise ValueError(f"observing event missing keys: {', '.join(missing)}")
        user_id = str(event["user_id"])
        safe = self.redactor.redact(event)
        return EventsRepo.for_user(self.store, user_id).insert(safe)
