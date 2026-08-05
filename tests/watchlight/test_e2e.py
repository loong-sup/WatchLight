from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from watchlight.analyzer import Analyzer
from watchlight.collector import Collector
from watchlight.collector.fetch import FetchResponse
from watchlight.feedback import FeedbackService, PreferenceService
from watchlight.gateway.boot_watchshed import ExecutionPipeline
from watchlight.notifier.channels import ChannelAdapters, MemoryChannelAdapter
from watchlight.notifier.queue import Notifier
from watchlight.observing.trace import TraceService
from watchlight.scheduler.loop import SchedulerLoop
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.deliveries import DeliveriesRepo
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.signals import SignalsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo
from watchlight.storage.store import utc_now

if TYPE_CHECKING:
    from watchlight.storage import Store


class FixtureFetchClient:
    def __init__(self, content: str) -> None:
        self.content = content

    async def fetch(self, url: str) -> FetchResponse:
        if url.endswith("/robots.txt"):
            return FetchResponse(url, 200, "User-agent: *\nAllow: /", {})
        return FetchResponse(url, 200, self.content, {})


@pytest.mark.asyncio
async def test_fixed_source_full_watchlight_chain(
    store: Store, user_id: str, tmp_path: Path
) -> None:
    fixtures = Path("fixtures/watchlight/sources")
    fetcher = FixtureFetchClient((fixtures / "page_v1.html").read_text(encoding="utf-8"))
    collector = Collector(store, fetcher, blob_root=tmp_path / "blobs", min_host_interval=0)
    analyzer = Analyzer(store, blob_root=tmp_path / "blobs")
    adapters = ChannelAdapters()
    memory = MemoryChannelAdapter()
    adapters.register("web", memory)
    notifier = Notifier(store, adapters)
    scheduler = SchedulerLoop(store, ExecutionPipeline(store, collector, analyzer, notifier))
    tasks = TaskService(store)
    draft = {
        "target": "Watch Watchlight releases",
        "source_scope": {"urls": ["https://fixture.example/product"]},
        "trigger_condition": {"must_contain": ["v2.0"]},
        "frequency_seconds": 3600,
        "notification_policy": {"channels": ["web"], "immediate": True},
    }
    created = tasks.create(user_id, draft)
    assert created.task_id and created.normalized_version_id
    tasks.confirm(user_id, created.task_id, created.normalized_version_id, now=100)

    assert len(await scheduler.tick(3700)) == 1
    first = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)
    first_completed = [row for row in first if row["status"] == "succeeded"]
    assert len(first_completed) == 1

    fetcher.content = (fixtures / "page_v2.html").read_text(encoding="utf-8")
    assert len(await scheduler.tick(7300)) == 1
    signals = SignalsRepo.for_user(store, user_id).list_for_task(created.task_id)
    assert signals and signals[0]["status"] == "proposed"
    briefs = BriefsRepo.for_user(store, user_id).list_for_execution(
        str(signals[0]["execution_id"])
    )
    assert briefs and bool(briefs[0]["sendable"])

    delivered = await notifier.drain_due(utc_now() + 1)
    assert len(delivered) == 1
    delivery = DeliveriesRepo.for_user(store, user_id).get(delivered[0])
    assert delivery and delivery["status"] == "delivered"
    trace = TraceService(store).trace_delivery(user_id, delivered[0])
    assert trace["source_urls"] == ["https://fixture.example/product"]
    assert trace["snapshots"] and trace["changes"]

    FeedbackService(store).submit(user_id, delivered[0], "useless", "v2.0")
    assert PreferenceService(store).apply_filter(user_id, created.task_id, "v2.0") == "exclude"

    fetcher.content = (fixtures / "page_login.html").read_text(encoding="utf-8")
    signal_count = len(SignalsRepo.for_user(store, user_id).list_for_task(created.task_id))
    assert len(await scheduler.tick(10900)) == 1
    latest_execution = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)[1]
    hits = SnapshotsRepo.for_user(store, user_id).hits_for_execution(
        str(latest_execution["execution_id"])
    )
    assert hits and hits[0]["status"] == "blocked"
    assert len(SignalsRepo.for_user(store, user_id).list_for_task(created.task_id)) == signal_count


def test_unsupported_action_does_not_persist(store: Store, user_id: str) -> None:
    result = TaskService(store).create(user_id, "关注商品并自动购买，每天通过飞书通知")
    assert result.task_id is None
    assert result.error and result.error.startswith("unsupported_action")
