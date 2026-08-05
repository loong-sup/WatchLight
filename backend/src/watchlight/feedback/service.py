from __future__ import annotations

from typing import TYPE_CHECKING

from watchlight.feedback.preferences import PreferenceService
from watchlight.storage.repos.deliveries import DeliveriesRepo
from watchlight.storage.repos.feedback import FeedbackRepo
from watchlight.storage.repos.signals import SignalsRepo

if TYPE_CHECKING:
    from watchlight.storage.store import Store


class FeedbackService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.preferences = PreferenceService(store)

    def submit(
        self, user_id: str, delivery_id: str, rating: str, reason: str | None = None
    ) -> str:
        if rating not in {"useful", "useless", "too_frequent"}:
            raise ValueError("invalid feedback rating")
        delivery = DeliveriesRepo.for_user(self.store, user_id).get(delivery_id)
        if delivery is None:
            raise PermissionError("delivery does not belong to user")
        signal = SignalsRepo.for_user(self.store, user_id).get(str(delivery["signal_id"]))
        if signal is None:
            raise KeyError(str(delivery["signal_id"]))
        repo = FeedbackRepo.for_user(self.store, user_id)
        feedback = repo.insert_feedback(
            {"delivery_id": delivery_id, "rating": rating, "reason": reason}
        )
        preference_id = self.preferences.create_from_feedback(
            user_id,
            str(signal["task_id"]),
            str(feedback["feedback_id"]),
            rating,
            reason,
        )
        if preference_id:
            repo.link_preference(str(feedback["feedback_id"]), preference_id)
        return str(feedback["feedback_id"])
