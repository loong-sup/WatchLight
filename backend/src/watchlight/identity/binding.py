from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnbindImpact:
    user_id: str
    channel_key: str
    retained_by_user_id: str
    task_count: int
    message: str
