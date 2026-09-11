from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from watchlight.storage.repos.identity import IdentityRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


def test_binding_requires_other_channel_confirmation(store: Store) -> None:
    repo = IdentityRepo(store)
    user_id = str(repo.create_user("A")["user_id"])
    token = repo.start_binding(user_id, "feishu", "ou-1", 1800)
    with pytest.raises(ValueError, match="primary"):
        repo.confirm_binding(token, "feishu")
    assert repo.confirm_binding(token, "web") == user_id
    assert repo.find_channel_identity("feishu", "ou-1")["status"] == "bound"  # type: ignore[index]


def test_expired_binding_does_not_resolve(store: Store) -> None:
    repo = IdentityRepo(store)
    user_id = str(repo.create_user("A")["user_id"])
    token = repo.start_binding(user_id, "feishu", "ou-1", 1)
    with pytest.raises(ValueError, match="expired"):
        repo.confirm_binding(token, "web", now=10**12)
