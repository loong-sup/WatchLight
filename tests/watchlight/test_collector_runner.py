from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from test_scheduler_service import complete_draft
from watchlight.collector.fetch import FetchResponse
from watchlight.collector.runner import Collector
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage import Store


class FakeFetchClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages

    async def fetch(self, url: str) -> FetchResponse:
        if url.endswith("/robots.txt"):
            return FetchResponse(url, 200, "User-agent: *\nAllow: /", {})
        return FetchResponse(url, 200, self.pages[url], {})


@pytest.mark.asyncio
async def test_collector_records_success_and_blocks_login_page(
    store: Store, user_id: str, tmp_path: Path
) -> None:
    urls = ["https://a.example/page", "https://b.example/login"]
    draft = complete_draft(source_scope={"urls": urls})
    service = TaskService(store)
    created = service.create(user_id, draft)
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=0)
    execution = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)[0]
    repo = ExecutionsRepo.for_user(store, user_id)
    assert repo.claim(str(execution["execution_id"]), 3600)
    collector = Collector(
        store,
        FakeFetchClient({urls[0]: "<h1>release 1</h1>", urls[1]: "请登录后查看"}),
        blob_root=tmp_path,
        min_host_interval=0,
    )
    result = await collector.run(str(execution["execution_id"]), user_id)
    assert result["status"] == "partial"
    hits = SnapshotsRepo.for_user(store, user_id).hits_for_execution(str(execution["execution_id"]))
    assert {hit["status"] for hit in hits} == {"ok", "blocked"}
