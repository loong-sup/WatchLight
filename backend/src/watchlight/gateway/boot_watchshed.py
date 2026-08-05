from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from watchlight.analyzer import Analyzer
from watchlight.collector import Collector
from watchlight.collector.expander import BuiltinSearchProvider, SourceExpander
from watchlight.collector.fetch import HttpxFetchClient
from watchlight.contracts.config.types_watchlight import WatchlightConfig, WatchshedConfig
from watchlight.feedback import FeedbackService, PreferenceService
from watchlight.identity import IdentityRegistry
from watchlight.notifier.channels import (
    ChannelAdapter,
    ChannelAdapters,
    MemoryChannelAdapter,
    RuntimeChannelAdapter,
)
from watchlight.notifier.queue import Notifier
from watchlight.observing import Observing
from watchlight.observing.metrics import Metrics
from watchlight.observing.trace import TraceService
from watchlight.scheduler.intent import ModelTaskIntentExtractor, TaskIntentExtractor
from watchlight.scheduler.limits import Limits
from watchlight.scheduler.loop import SchedulerLoop
from watchlight.scheduler.nl import NaturalLanguageTaskFlow
from watchlight.scheduler.service import TaskService
from watchlight.storage import Store, migrate, utc_now
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.tools.builtin.watch_tasks import create_watch_tasks_list_tool

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from watchlight.gateway.boot import GatewayRuntime


class ExecutionPipeline:
    def __init__(
        self, store: Store, collector: Collector, analyzer: Analyzer, notifier: Notifier
    ) -> None:
        self.store = store
        self.collector = collector
        self.analyzer = analyzer
        self.notifier = notifier

    async def run(self, execution_id: str, user_id: str) -> None:
        await self.collector.run(execution_id, user_id)
        await self.analyzer.run(execution_id, user_id)
        for brief in BriefsRepo.for_user(self.store, user_id).list_for_execution(execution_id):
            if bool(brief["sendable"]):
                self.notifier.enqueue(user_id, str(brief["brief_id"]))


@dataclass(slots=True)
class WatchlightServices:
    store: Store
    identity: IdentityRegistry
    tasks: TaskService
    nl_tasks: NaturalLanguageTaskFlow
    scheduler: SchedulerLoop
    collector: Collector
    analyzer: Analyzer
    notifier: Notifier
    feedback: FeedbackService
    preferences: PreferenceService
    observing: Observing
    metrics: Metrics
    trace: TraceService
    tick_seconds: int
    _tasks: list[asyncio.Task[None]] = field(default_factory=list)

    async def start(self) -> None:
        self.scheduler.recover(utc_now())
        if self._tasks:
            return
        self._tasks = [
            asyncio.create_task(self._loop(self.scheduler.tick), name="watchlight-scheduler"),
            asyncio.create_task(self._loop(self.notifier.drain_due), name="watchlight-notifier"),
        ]

    async def _loop(self, operation: Callable[[], Awaitable[Any]]) -> None:
        while True:
            await operation()
            await asyncio.sleep(self.tick_seconds)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self.store.close()


def bootstrap_watchlight(
    config: WatchlightConfig, gateway_runtime: GatewayRuntime | None = None
) -> WatchlightServices:
    settings = config.watchshed or WatchshedConfig()
    store = Store.open(settings.db_path)
    migrate(store)
    identity = IdentityRegistry(store)
    limits = Limits(
        max_tasks_per_user=settings.max_tasks_per_user,
        max_concurrent_global=settings.max_concurrent_executions,
    )
    tasks = TaskService(store, limits=limits)
    if gateway_runtime is not None:
        gateway_runtime.tool_registry.register(create_watch_tasks_list_tool(store))
    fetcher = HttpxFetchClient(timeout_seconds=settings.max_fetch_seconds)
    collector = Collector(
        store,
        fetcher,
        expander=SourceExpander(BuiltinSearchProvider()),
        blob_root=Path(settings.blob_root),
        max_concurrent_fetches=settings.max_concurrent_fetches,
        max_fetch_seconds=settings.max_fetch_seconds,
    )
    analyzer = Analyzer(store, blob_root=Path(settings.blob_root))
    intent_extractor: TaskIntentExtractor | None = None
    provider_registry = getattr(gateway_runtime, "provider_registry", None)
    default_provider = getattr(gateway_runtime, "default_provider", "")
    default_model = getattr(gateway_runtime, "default_model", "")
    if provider_registry is not None and default_provider and default_model:
        provider = provider_registry.get(default_provider)
        if provider is not None:
            intent_extractor = ModelTaskIntentExtractor(provider, default_model)
    adapters = ChannelAdapters()
    channel_mapping = {"web": "webchat", "webchat": "webchat", "feishu": "feishu"}
    for policy_key, plugin_key in channel_mapping.items():
        plugin = gateway_runtime.channel_registry.get(plugin_key) if gateway_runtime else None
        adapter: ChannelAdapter
        if plugin is not None:
            adapter = RuntimeChannelAdapter(store, policy_key, plugin)
        else:
            adapter = MemoryChannelAdapter()
        adapters.register(policy_key, adapter)
    notifier = Notifier(store, adapters)
    pipeline = ExecutionPipeline(store, collector, analyzer, notifier)
    scheduler = SchedulerLoop(store, pipeline)
    return WatchlightServices(
        store=store,
        identity=identity,
        tasks=tasks,
        nl_tasks=NaturalLanguageTaskFlow(tasks, intent_extractor=intent_extractor),
        scheduler=scheduler,
        collector=collector,
        analyzer=analyzer,
        notifier=notifier,
        feedback=FeedbackService(store),
        preferences=PreferenceService(store),
        observing=Observing(store),
        metrics=Metrics(store),
        trace=TraceService(store),
        tick_seconds=settings.scheduler_tick_seconds,
    )
