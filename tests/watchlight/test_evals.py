from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from watchlight.evals import EvalRunner, load_dataset
from watchlight.evals.metrics import percentile, safe_ratio

if TYPE_CHECKING:
    from pathlib import Path


def test_smoke_dataset_reports_expected_business_metrics(tmp_path: Path) -> None:
    dataset = load_dataset("evals/datasets/watchlight_smoke.jsonl")
    report = EvalRunner().run(dataset)

    assert report.metrics["case_count"] == 7
    assert report.metrics["source_count"] == 8
    assert report.metrics["notification_precision"] == 1.0
    assert report.metrics["change_recall"] == 1.0
    assert report.metrics["f1"] == 1.0
    assert report.metrics["duplicate_compression_rate"] == 0.25
    assert report.metrics["fact_coverage"] == 1.0
    assert report.metrics["blocked_source_count"] == 1
    assert report.metrics["false_alerts_per_100_cases"] == 0.0

    duplicate = next(case for case in report.cases if case.case_id == "release-duplicate")
    assert duplicate.eligible_signal_count == 1
    assert duplicate.delivered_notification_count == 0
    cross_source = next(case for case in report.cases if case.case_id == "cross-source-merge")
    assert cross_source.raw_change_count == 2
    assert cross_source.merged_signal_count == 1

    json_path, markdown_path = report.write(tmp_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["metrics"]["true_positive"] == 3
    assert "Notification precision | 100.00%" in markdown_path.read_text(encoding="utf-8")


def test_frozen_httpx_release_seed_is_replayable() -> None:
    report = EvalRunner().run(load_dataset("evals/datasets/httpx_release_seed.jsonl"))

    assert report.metrics["case_count"] == 5
    assert report.metrics["source_count"] == 6
    assert report.metrics["true_positive"] == 2
    assert report.metrics["true_negative"] == 3
    assert report.metrics["notification_precision"] == 1.0
    assert report.metrics["change_recall"] == 1.0
    assert report.metrics["fact_coverage"] == 1.0
    assert report.metrics["duplicate_compression_rate"] == pytest.approx(1 / 3)


def test_dataset_rejects_missing_snapshot(tmp_path: Path) -> None:
    dataset = tmp_path / "invalid.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "case_id": "missing",
                "task_id": "task",
                "captured_at": 1,
                "category": "invalid",
                "sources": [
                    {
                        "url": "https://example.com",
                        "previous_path": "missing-before.html",
                        "current_path": "missing-after.html",
                    }
                ],
                "expected_notify": False,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="snapshot not found"):
        load_dataset(dataset)


def test_metric_helpers_handle_boundaries() -> None:
    assert safe_ratio(1, 0) == 0.0
    assert percentile([], 0.95) == 0.0
    assert percentile([1.0, 2.0, 3.0], 0.5) == 2.0
