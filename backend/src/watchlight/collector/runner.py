from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from watchlight.collector.content_guard import ContentKind, classify
from watchlight.collector.errors import ErrorClassifier
from watchlight.collector.expander import SourceExpander, SourcePlan
from watchlight.collector.fetch import is_safe_public_url
from watchlight.collector.robots import RobotsCache
from watchlight.collector.snapshot import SnapshotWriter
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo
from watchlight.storage.repos.tasks import TasksRepo
from watchlight.storage.store import Store, utc_now

if TYPE_CHECKING:
    from watchlight.collector.fetch import FetchClient


class Collector:
    def __init__(
        self,
        store: Store,
        fetch_client: FetchClient,
        *,
        expander: SourceExpander | None = None,
        blob_root: Path | None = None,
        min_host_interval: float = 2.0,
        max_concurrent_fetches: int = 4,
        max_fetch_seconds: float = 30,
    ) -> None:
        self.store = store
        self.fetch_client = fetch_client
        self.expander = expander or SourceExpander()
        self.robots = RobotsCache(fetch_client)
        self.writer = SnapshotWriter(store, blob_root or Path(".watchlight-state/blobs"))
        self.min_host_interval = min_host_interval
        self.semaphore = asyncio.Semaphore(max_concurrent_fetches)
        self.max_fetch_seconds = max_fetch_seconds
        self._host_locks: dict[str, asyncio.Lock] = {}

    async def run(self, execution_id: str, user_id: str) -> dict[str, int | str]:
        executions = ExecutionsRepo.for_user(self.store, user_id)
        execution = executions.get(execution_id)
        if execution is None:
            raise KeyError(execution_id)
        task = TasksRepo.for_user(self.store, user_id).get(str(execution["task_id"]))
        if task is None:
            raise KeyError(str(execution["task_id"]))
        source_scope = json.loads(str(task["source_scope_json"]))
        plans = await self.expander.expand(source_scope)
        results = await asyncio.gather(
            *(self._collect_one(user_id, execution_id, plan) for plan in plans)
        )
        successes = sum(status in {"ok", "changed", "unchanged"} for status in results)
        failures = len(results) - successes
        status = "failed" if results and not successes else "partial" if failures else "succeeded"
        executions.settle(
            execution_id,
            status,
            counts={"source_count": len(results)},
            failure_summary=f"{failures} source(s) failed" if failures else None,
        )
        return {"source_count": len(results), "failures": failures, "status": status}

    async def _collect_one(
        self, user_id: str, execution_id: str, plan: SourcePlan
    ) -> str:
        host = urlparse(plan.url).hostname or ""
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        async with self.semaphore, lock:
            try:
                if not is_safe_public_url(plan.url, resolve_dns=False):
                    return self._blocked(
                        user_id, execution_id, plan.url, "blocked_non_public_url"
                    )
                if not await self.robots.is_allowed(plan.url):
                    return self._blocked(user_id, execution_id, plan.url, "robots_disallowed", True)
                response = await asyncio.wait_for(
                    self.fetch_client.fetch(plan.url), timeout=self.max_fetch_seconds
                )
                kind = classify(response.text, response.status_code)
                if kind is not ContentKind.TARGET:
                    return self._blocked(user_id, execution_id, plan.url, kind.value)
                result = self.writer.write(user_id, execution_id, plan.url, response.text)
                SnapshotsRepo.for_user(self.store, user_id).insert_hit(
                    {
                        "execution_id": execution_id,
                        "source_url": plan.url,
                        "fetched_at": utc_now(),
                        "status": result.status,
                        "http_status": response.status_code,
                        "snapshot_id": result.snapshot_id,
                    }
                )
                return result.status
            except PermissionError as exc:
                return self._blocked(user_id, execution_id, plan.url, str(exc))
            except Exception as exc:
                decision = ErrorClassifier().classify(exc)
                status = "unparseable" if decision.code.value == "parse_error" else "unreachable"
                SnapshotsRepo.for_user(self.store, user_id).insert_hit(
                    {
                        "execution_id": execution_id,
                        "source_url": plan.url,
                        "fetched_at": utc_now(),
                        "status": status,
                        "error_code": decision.code.value,
                    }
                )
                return status
            finally:
                if self.min_host_interval:
                    await asyncio.sleep(self.min_host_interval)

    def _blocked(
        self,
        user_id: str,
        execution_id: str,
        url: str,
        error_code: str,
        robots: bool = False,
    ) -> str:
        SnapshotsRepo.for_user(self.store, user_id).insert_hit(
            {
                "execution_id": execution_id,
                "source_url": url,
                "fetched_at": utc_now(),
                "status": "blocked",
                "error_code": error_code,
                "robots_disallowed": robots,
            }
        )
        return "blocked"
