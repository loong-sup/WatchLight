from __future__ import annotations

from typing import TYPE_CHECKING

from watchlight.storage.repos.deliveries import DeliveriesRepo

if TYPE_CHECKING:
    from watchlight.storage.store import Store


class DedupGate:
    def __init__(self, store: Store) -> None:
        self.store = store

    def check(self, user_id: str, signal_id: str, channel_key: str) -> bool:
        return (
            DeliveriesRepo.for_user(self.store, user_id).for_signal_channel(
                signal_id, channel_key
            )
            is None
        )
