from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from watchlight.storage.repos.identity import IdentityRepo


class IdentityAudit:
    def __init__(self, repo: IdentityRepo) -> None:
        self.repo = repo

    def append(self, user_id: str, event_type: str, detail: dict[str, Any]) -> None:
        self.repo.append_event(user_id, event_type, detail)
