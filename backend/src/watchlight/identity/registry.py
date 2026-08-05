from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from watchlight.identity.binding import UnbindImpact
from watchlight.storage.repos.identity import IdentityRepo

if TYPE_CHECKING:
    from watchlight.storage.store import Store


@dataclass(frozen=True, slots=True)
class ResolveResult:
    user_id: str | None
    needs_binding: bool
    status: str


class IdentityRegistry:
    def __init__(self, store: Store, *, binding_ttl_seconds: int = 1800) -> None:
        self.store = store
        self.repo = IdentityRepo(store)
        self.binding_ttl_seconds = binding_ttl_seconds

    def resolve(self, channel_key: str, channel_user_id: str) -> ResolveResult:
        identity = self.repo.find_channel_identity(channel_key, channel_user_id)
        if identity is None:
            return ResolveResult(user_id=None, needs_binding=False, status="unknown")
        if identity["status"] != "bound":
            return ResolveResult(
                user_id=None,
                needs_binding=True,
                status=str(identity["status"]),
            )
        return ResolveResult(
            user_id=str(identity["user_id"]), needs_binding=False, status="bound"
        )

    def resolve_or_register(
        self,
        channel_key: str,
        channel_user_id: str,
        *,
        display_name: str | None = None,
        timezone: str = "UTC",
    ) -> ResolveResult:
        """Resolve an inbound identity, creating only a genuinely new first-channel user."""
        resolved = self.resolve(channel_key, channel_user_id)
        if resolved.status != "unknown":
            return resolved
        self.register(
            channel_key,
            channel_user_id,
            display_name=display_name,
            timezone=timezone,
        )
        return self.resolve(channel_key, channel_user_id)

    def register(
        self,
        channel_key: str,
        channel_user_id: str,
        *,
        display_name: str | None = None,
        timezone: str = "UTC",
    ) -> str:
        existing = self.resolve(channel_key, channel_user_id)
        if existing.user_id:
            return existing.user_id
        if existing.status != "unknown":
            raise ValueError(f"channel identity is {existing.status}")
        user = self.repo.create_user(display_name or channel_user_id, timezone)
        user_id = str(user["user_id"])
        token = self.repo.start_binding(
            user_id, channel_key, channel_user_id, self.binding_ttl_seconds
        )
        # First-channel registration is an explicit account creation, not a cross-channel merge.
        self.store.execute(
            "UPDATE channel_identities SET status='bound',confirmed_at=?,confirm_token=NULL,"
            "confirm_expires_at=NULL WHERE confirm_token=?",
            (int(user["created_at"]), token),
        )
        self.repo.append_event(user_id, "identity_registered", {"channel": channel_key})
        return user_id

    def start_binding(
        self, initiator_user_id: str, target_channel_key: str, target_channel_user_id: str
    ) -> str:
        if self.repo.get_user(initiator_user_id) is None:
            raise KeyError(initiator_user_id)
        return self.repo.start_binding(
            initiator_user_id,
            target_channel_key,
            target_channel_user_id,
            self.binding_ttl_seconds,
        )

    def confirm_binding(self, token: str, via_channel_key: str) -> str:
        return self.repo.confirm_binding(token, via_channel_key)

    def start_unbind(self, user_id: str, channel_key: str) -> tuple[str, UnbindImpact]:
        count_row = self.store.fetchone(
            "SELECT COUNT(*) AS count FROM watch_tasks WHERE user_id=? AND status!='deleted'",
            (user_id,),
        )
        task_count = int(count_row["count"] if count_row else 0)
        impact = UnbindImpact(
            user_id=user_id,
            channel_key=channel_key,
            retained_by_user_id=user_id,
            task_count=task_count,
            message=f"解绑后 {task_count} 个任务及其历史仍归主账号保留。",
        )
        token = self.repo.start_unbind(user_id, channel_key, self.binding_ttl_seconds)
        return token, impact

    def confirm_unbind(self, token: str, via_channel_key: str) -> str:
        return self.repo.confirm_unbind(token, via_channel_key)
