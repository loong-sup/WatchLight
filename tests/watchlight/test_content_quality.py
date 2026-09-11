from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from test_scheduler_service import complete_draft
from watchlight.analyzer import Analyzer
from watchlight.analyzer.quality import classify_content_quality
from watchlight.collector.snapshot import SnapshotWriter
from watchlight.scheduler.service import TaskService
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.signals import SignalsRepo

if TYPE_CHECKING:
    from pathlib import Path

    from watchlight.storage import Store


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (
            ":root{--wp--color:#000;--wp--space:1rem;--wp--ratio:1;}"
            ".card{color:#fff;margin:10px;}",
            "css",
        ),
        (
            "function render(){const data={value:1};let node=document.querySelector('x');"
            "return data;}",
            "javascript",
        ),
        ("<div><span>payload</span><script>bad()</script></div>", "markup"),
        ('{"alpha": 1, "beta": 2, "gamma": {"value": 3}}', "serialized"),
    ],
)
def test_machine_oriented_content_is_rejected(content: str, reason: str) -> None:
    result = classify_content_quality(content)

    assert result.safe is False
    assert result.reason == reason


@pytest.mark.parametrize(
    "content",
    [
        "The release explains how CSS custom properties improve the design system.",
        "小米汽车今天发布了新的技术说明，重点介绍智能驾驶能力的更新。",
        "The JSON API changed its response format, according to the release notes.",
    ],
)
def test_readable_technical_prose_is_accepted(content: str) -> None:
    assert classify_content_quality(content).safe is True


@pytest.mark.asyncio
async def test_analyzer_suppresses_css_evidence(
    store: Store, user_id: str, tmp_path: Path
) -> None:
    service = TaskService(store)
    created = service.create(
        user_id,
        complete_draft(trigger_condition={"must_contain": [], "must_not_contain": []}),
    )
    assert created.task_id and created.normalized_version_id
    service.confirm(user_id, created.task_id, created.normalized_version_id, now=0)
    execution = ExecutionsRepo.for_user(store, user_id).list_for_task(created.task_id)[0]
    execution_id = str(execution["execution_id"])
    assert ExecutionsRepo.for_user(store, user_id).claim(execution_id, 1)
    blob_root = tmp_path / "blobs"
    writer = SnapshotWriter(store, blob_root)
    writer.write(
        user_id,
        execution_id,
        "https://example.com/theme",
        ":root{--wp--color:#000;--wp--space:1rem;--wp--ratio:1;}",
        captured_at=2,
    )
    writer.write(
        user_id,
        execution_id,
        "https://example.com/theme",
        ":root{--wp--color:#111;--wp--space:2rem;--wp--ratio:2;}",
        captured_at=3,
    )

    await Analyzer(store, blob_root=blob_root).run(execution_id, user_id)

    signals = SignalsRepo.for_user(store, user_id).list_for_execution(execution_id)
    assert len(signals) == 1
    assert signals[0]["status"] == "suppressed"
    briefs = BriefsRepo.for_user(store, user_id).list_for_execution(execution_id)
    assert len(briefs) == 1
    assert briefs[0]["sendable"] == 0
    assert briefs[0]["facts_json"] == "[]"
    assert briefs[0]["failure_summary"] == "content_quality:css"
