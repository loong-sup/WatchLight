from __future__ import annotations

import asyncio
import json
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
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.signals import SignalsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo
from watchlight.storage.repos.tasks import TasksRepo
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
        briefs = BriefsRepo.for_user(self.store, user_id).list_for_execution(execution_id)
        sendable = [brief for brief in briefs if bool(brief["sendable"])]
        if not sendable and self._report_on_no_change(execution_id, user_id):
            sendable = [self._create_no_change_brief(execution_id, user_id)]

        delivery_ids: list[str] = []
        for brief in sendable:
            delivery_ids.extend(
                self.notifier.enqueue(user_id, str(brief["brief_id"]))
            )

        execution = ExecutionsRepo.for_user(self.store, user_id).get(execution_id)
        if execution is not None:
            ExecutionsRepo.for_user(self.store, user_id).update_counts(
                execution_id,
                signal_count=len(
                    SignalsRepo.for_user(self.store, user_id).list_for_execution(execution_id)
                ),
                delivery_count=len(delivery_ids),
            )

    def _report_on_no_change(self, execution_id: str, user_id: str) -> bool:
        execution = ExecutionsRepo.for_user(self.store, user_id).get(execution_id)
        if execution is None:
            return False
        task = TasksRepo.for_user(self.store, user_id).get(str(execution["task_id"]))
        if task is None:
            return False
        policy = json.loads(str(task["notification_policy_json"]))
        return bool(policy.get("report_on_no_change", False))

    def _create_no_change_brief(self, execution_id: str, user_id: str) -> dict[str, Any]:
        executions = ExecutionsRepo.for_user(self.store, user_id)
        execution = executions.get(execution_id)
        if execution is None:
            raise KeyError(execution_id)
        task = TasksRepo.for_user(self.store, user_id).get(str(execution["task_id"]))
        if task is None:
            raise KeyError(str(execution["task_id"]))

        hits = SnapshotsRepo.for_user(self.store, user_id).hits_for_execution(execution_id)
        successful = [hit for hit in hits if hit["status"] in {"ok", "changed", "unchanged"}]
        failed_count = len(hits) - len(successful)
        if hits:
            fact = (
                f"本轮检查已完成，共检查 {len(hits)} 个来源，"
                "暂无检测到需要通知的可读内容变化。"
            )
        else:
            fact = (
                "本轮检查已完成，但没有获取到可检查的来源，"
                "暂无可报告的可读内容变化。"
            )
        if failed_count:
            fact += f"其中 {failed_count} 个来源暂时无法访问或被站点限制。"

        at = utc_now()
        source_urls = list(
            dict.fromkeys(str(hit["source_url"]) for hit in successful)
        )[:10]
        signal = SignalsRepo.for_user(self.store, user_id).insert(
            {
                "execution_id": execution_id,
                "task_id": task["task_id"],
                "change_ids": [],
                "source_urls": source_urls,
                "captured_at": at,
                "relevance": 1,
                "importance": 0,
                "novelty": 0,
                "source_credibility": 0,
                "uncertainty_level": "medium" if failed_count else "low",
                "status": "proposed",
                "dedup_key": f"periodic-report:{execution_id}",
            }
        )
        return BriefsRepo.for_user(self.store, user_id).insert(
            {
                "execution_id": execution_id,
                "signal_ids": [signal["signal_id"]],
                "facts": [fact],
                "inferences": [],
                "next_steps": [],
                "source_refs": source_urls,
                "captured_at": at,
                "uncertainty_level": "medium" if failed_count else "low",
                "sendable": True,
            }
        )


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
