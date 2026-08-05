from __future__ import annotations

import json
import secrets
from typing import Any

from watchlight.storage.repos import row_dict
from watchlight.storage.store import Store, new_id, utc_now


class IdentityRepo:
    def __init__(self, store: Store) -> None:
        self.store = store

    def create_user(self, display_name: str, timezone: str = "UTC") -> dict[str, Any]:
        user_id = new_id()
        self.store.execute(
            "INSERT INTO users(user_id,display_name,timezone,created_at) VALUES (?,?,?,?)",
            (user_id, display_name, timezone, utc_now()),
        )
        result = row_dict(self.store.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,)))
        assert result is not None
        return result

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return row_dict(self.store.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,)))

    def find_channel_identity(
        self, channel_key: str, channel_user_id: str
    ) -> dict[str, Any] | None:
        return row_dict(
            self.store.fetchone(
                "SELECT * FROM channel_identities WHERE channel_key=? AND channel_user_id=?",
                (channel_key, channel_user_id),
            )
        )

    def list_bound(self, user_id: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.store.fetchall(
                "SELECT * FROM channel_identities WHERE user_id=? AND status='bound'", (user_id,)
            )
        ]

    def start_binding(
        self,
        user_id: str,
        channel_key: str,
        channel_user_id: str,
        ttl_seconds: int,
    ) -> str:
        token = secrets.token_urlsafe(24)
        now = utc_now()
        self.store.execute(
            "INSERT INTO channel_identities(channel_key,channel_user_id,user_id,status,"
            "confirm_token,confirm_expires_at) VALUES (?,?,?,'pending',?,?) "
            "ON CONFLICT(channel_key,channel_user_id) DO UPDATE SET user_id=excluded.user_id,"
            "status='pending',confirm_token=excluded.confirm_token,"
            "confirm_expires_at=excluded.confirm_expires_at,confirmed_at=NULL",
            (channel_key, channel_user_id, user_id, token, now + ttl_seconds),
        )
        self.append_event(user_id, "binding_started", {"channel": channel_key})
        return token

    def confirm_binding(self, token: str, via_channel_key: str, now: int | None = None) -> str:
        at = now or utc_now()
        row = self.store.fetchone(
            "SELECT * FROM channel_identities WHERE confirm_token=? AND status='pending'", (token,)
        )
        if row is None or int(row["confirm_expires_at"] or 0) < at:
            raise ValueError("binding token is invalid or expired")
        if via_channel_key == str(row["channel_key"]):
            raise ValueError("binding must be confirmed from the primary channel")
        self.store.execute(
            "UPDATE channel_identities SET status='bound',confirmed_at=?,confirm_token=NULL,"
            "confirm_expires_at=NULL WHERE channel_key=? AND channel_user_id=?",
            (at, row["channel_key"], row["channel_user_id"]),
        )
        user_id = str(row["user_id"])
        self.append_event(user_id, "binding_confirmed", {"channel": row["channel_key"]})
        return user_id

    def start_unbind(self, user_id: str, channel_key: str, ttl_seconds: int) -> str:
        row = self.store.fetchone(
            "SELECT * FROM channel_identities WHERE user_id=? AND channel_key=? AND status='bound'",
            (user_id, channel_key),
        )
        if row is None:
            raise KeyError(channel_key)
        token = secrets.token_urlsafe(24)
        self.store.execute(
            "UPDATE channel_identities SET confirm_token=?,confirm_expires_at=? "
            "WHERE user_id=? AND channel_key=? AND channel_user_id=?",
            (
                token,
                utc_now() + ttl_seconds,
                user_id,
                channel_key,
                row["channel_user_id"],
            ),
        )
        self.append_event(user_id, "unbind_started", {"channel": channel_key})
        return token

    def confirm_unbind(self, token: str, via_channel_key: str) -> str:
        now = utc_now()
        row = self.store.fetchone(
            "SELECT * FROM channel_identities WHERE confirm_token=? AND status='bound'", (token,)
        )
        if row is None or int(row["confirm_expires_at"] or 0) < now:
            raise ValueError("unbind token is invalid or expired")
        if via_channel_key == str(row["channel_key"]):
            raise ValueError("unbind must be confirmed from another bound channel")
        self.store.execute(
            "UPDATE channel_identities SET status='unbinding',confirm_token=NULL,"
            "confirm_expires_at=NULL WHERE channel_key=? AND channel_user_id=?",
            (row["channel_key"], row["channel_user_id"]),
        )
        user_id = str(row["user_id"])
        self.append_event(user_id, "unbind_confirmed", {"channel": row["channel_key"]})
        return user_id

    def append_event(self, user_id: str, event_type: str, detail: dict[str, Any]) -> None:
        self.store.execute(
            "INSERT INTO identity_events VALUES (?,?,?,?,?)",
            (new_id(), user_id, event_type, json.dumps(detail), utc_now()),
        )
