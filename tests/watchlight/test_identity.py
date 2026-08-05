from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from watchlight.identity import IdentityRegistry

if TYPE_CHECKING:
    from watchlight.storage import Store


def test_register_resolve_bind_and_unbind(store: Store) -> None:
    registry = IdentityRegistry(store)
    user_id = registry.register("web", "local", display_name="Local")
    assert registry.resolve("web", "local").user_id == user_id
    assert registry.resolve("feishu", "ou-1").status == "unknown"

    token = registry.start_binding(user_id, "feishu", "ou-1")
    with pytest.raises(ValueError, match="primary"):
        registry.confirm_binding(token, "feishu")
    assert registry.confirm_binding(token, "web") == user_id
    assert registry.resolve("feishu", "ou-1").user_id == user_id

    unbind_token, impact = registry.start_unbind(user_id, "feishu")
    assert impact.retained_by_user_id == user_id
    registry.confirm_unbind(unbind_token, "web")
    assert registry.resolve("feishu", "ou-1").needs_binding


def test_unknown_identity_never_resolves_other_user(store: Store) -> None:
    registry = IdentityRegistry(store)
    registry.register("web", "alice")
    unknown = registry.resolve("web", "bob")
    assert unknown.user_id is None
    assert unknown.status == "unknown"
    assert not unknown.needs_binding
