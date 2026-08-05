from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from watchlight.storage import Store, migrate
from watchlight.storage.repos.identity import IdentityRepo

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def store() -> Iterator[Store]:
    value = Store.open(":memory:")
    migrate(value)
    try:
        yield value
    finally:
        value.close()


@pytest.fixture
def user_id(store: Store) -> str:
    return str(IdentityRepo(store).create_user("Test User", "Asia/Shanghai")["user_id"])


def task_fields(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "target": "Watch Python releases",
        "source_scope": {"urls": ["https://example.com/releases"]},
        "trigger_condition": {"must_contain": ["release"]},
        "frequency_seconds": 3600,
        "notification_policy": {"channels": ["web"], "immediate": True},
    }
    values.update(changes)
    return values
