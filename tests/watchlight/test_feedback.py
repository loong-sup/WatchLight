from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from test_notifier import create_sendable_brief
from watchlight.feedback import FeedbackService, PreferenceService
from watchlight.notifier.channels import ChannelAdapters, MemoryChannelAdapter
from watchlight.notifier.queue import Notifier
from watchlight.storage.repos.identity import IdentityRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


@pytest.mark.asyncio
async def test_feedback_creates_visible_revocable_task_preference(
    store: Store, user_id: str
) -> None:
    brief_id = create_sendable_brief(store, user_id)
    adapters = ChannelAdapters()
    adapters.register("web", MemoryChannelAdapter())
    notifier = Notifier(store, adapters)
    delivery_id = notifier.enqueue(user_id, brief_id, now=20)[0]
    await notifier.drain_due(20)
    feedback_id = FeedbackService(store).submit(user_id, delivery_id, "useless", "beta")
    preferences = PreferenceService(store)
    task_id = str(store.fetchone("SELECT task_id FROM signals LIMIT 1")["task_id"])
    items = preferences.list_for_task(user_id, task_id)
    assert items[0]["originating_feedback_id"] == feedback_id
    assert preferences.apply_filter(user_id, task_id, "beta release") == "exclude"
    preferences.revoke(user_id, str(items[0]["preference_id"]))
    assert preferences.apply_filter(user_id, task_id, "beta release") == "include"


@pytest.mark.asyncio
async def test_other_user_cannot_feedback_on_delivery(store: Store, user_id: str) -> None:
    brief_id = create_sendable_brief(store, user_id)
    adapters = ChannelAdapters()
    adapters.register("web", MemoryChannelAdapter())
    delivery_id = Notifier(store, adapters).enqueue(user_id, brief_id, now=20)[0]
    other = str(IdentityRepo(store).create_user("Other")["user_id"])
    with pytest.raises(PermissionError):
        FeedbackService(store).submit(other, delivery_id, "useful")
