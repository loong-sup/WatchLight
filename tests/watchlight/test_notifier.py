from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from test_scheduler_service import complete_draft
from watchlight.notifier.channels import (
    ChannelAdapters,
    MemoryChannelAdapter,
    RuntimeChannelAdapter,
)
from watchlight.notifier.dnd import DoNotDisturbCalculator
from watchlight.notifier.queue import Notifier
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.deliveries import DeliveriesRepo
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.signals import SignalsRepo

if TYPE_CHECKING:
    from watchlight.storage import Store


def create_sendable_brief(store: Store, user_id: str, *, dnd: dict[str, str] | None = None) -> str:
    policy = {"channels": ["web"], "immediate": True}
    if dnd:
        policy["do_not_disturb"] = dnd
    service = TaskService(store)
    created = service.create(user_id, complete_draft(notification_policy=policy))
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=0)
    execution = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)[0]
    signal = SignalsRepo.for_user(store, user_id).insert(
        {
            "execution_id": execution["execution_id"],
            "task_id": created.task_id,
            "change_ids": [],
            "source_urls": ["https://example.com"],
            "captured_at": 10,
            "dedup_key": "k",
            "status": "proposed",
        }
    )
    brief = BriefsRepo.for_user(store, user_id).insert(
        {
            "execution_id": execution["execution_id"],
            "signal_ids": [signal["signal_id"]],
            "facts": ["Version 2 released"],
            "source_refs": ["https://example.com"],
            "captured_at": 10,
            "uncertainty_level": "low",
            "sendable": True,
        }
    )
    return str(brief["brief_id"])


def test_dnd_across_midnight() -> None:
    calculator = DoNotDisturbCalculator()
    # 2024-01-01 23:00 UTC is inside 22:00-08:00 UTC.
    delayed = calculator.next_send_at(
        1704150000, {"from": "22:00", "to": "08:00", "tz": "UTC"}
    )
    assert delayed == 1704182400


@pytest.mark.asyncio
async def test_enqueue_deduplicates_and_delivers(store: Store, user_id: str) -> None:
    brief_id = create_sendable_brief(store, user_id)
    adapters = ChannelAdapters()
    memory = MemoryChannelAdapter()
    adapters.register("web", memory)
    notifier = Notifier(store, adapters)
    first = notifier.enqueue(user_id, brief_id, now=20)
    second = notifier.enqueue(user_id, brief_id, now=20)
    assert len(first) == 1
    assert second == []
    assert await notifier.drain_due(20) == first
    assert len(memory.sent) == 1
    assert DeliveriesRepo.for_user(store, user_id).get(first[0])["status"] == "delivered"  # type: ignore[index]


@pytest.mark.asyncio
async def test_dnd_defers_until_window_end(store: Store, user_id: str) -> None:
    brief_id = create_sendable_brief(
        store, user_id, dnd={"from": "22:00", "to": "08:00", "tz": "UTC"}
    )
    adapters = ChannelAdapters()
    adapters.register("web", MemoryChannelAdapter())
    notifier = Notifier(store, adapters)
    delivery_id = notifier.enqueue(user_id, brief_id, now=1704150000)[0]
    delivery = DeliveriesRepo.for_user(store, user_id).get(delivery_id)
    assert delivery is not None
    assert delivery["status"] == "deferred"
    assert delivery["scheduled_send_at"] == 1704182400


@pytest.mark.asyncio
async def test_retry_rebuilds_text_without_parsing_last_error(
    store: Store, user_id: str
) -> None:
    brief_id = create_sendable_brief(store, user_id)

    class FlakyAdapter:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def send(self, _user_id: str, text: str) -> None:
            self.calls.append(text)
            if len(self.calls) == 1:
                raise RuntimeError("temporary failure")

    flaky = FlakyAdapter()
    adapters = ChannelAdapters()
    adapters.register("web", flaky)
    notifier = Notifier(store, adapters)
    delivery_id = notifier.enqueue(user_id, brief_id, now=20)[0]

    assert await notifier.drain_due(20) == []
    failed_once = DeliveriesRepo.for_user(store, user_id).get(delivery_id)
    assert failed_once is not None
    assert failed_once["status"] == "retry"
    assert failed_once["last_error"] == "RuntimeError: temporary failure"

    assert await notifier.drain_due(25) == [delivery_id]
    delivered = DeliveriesRepo.for_user(store, user_id).get(delivery_id)
    assert delivered is not None
    assert delivered["status"] == "delivered"
    assert delivered["last_error"] is None
    assert flaky.calls == [flaky.calls[0], flaky.calls[0]]
    assert "Version 2 released" in flaky.calls[0]


@pytest.mark.asyncio
async def test_runtime_feishu_adapter_marks_bound_user_as_open_id(
    store: Store, user_id: str
) -> None:
    store.execute(
        "INSERT INTO channel_identities(channel_key,channel_user_id,user_id,status) "
        "VALUES ('feishu','ou-user',?,'bound')",
        (user_id,),
    )
    sent: list[tuple[str, str | None]] = []

    class FakePlugin:
        async def send(self, _account: str, recipient: str, message: object) -> None:
            channel_data = getattr(message, "channel_data", None) or {}
            sent.append((recipient, channel_data.get("receive_id_type")))

    adapter = RuntimeChannelAdapter(store, "feishu", FakePlugin())  # type: ignore[arg-type]
    await adapter.send(user_id, "测试通知")

    assert sent == [("ou-user", "open_id")]
