from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from watchlight.analyzer.change import ChangeDetector
from watchlight.analyzer.dedupe import CandidateSignal, CrossSourceDeduper, DedupWindow
from watchlight.analyzer.value import PreferenceFilter
from watchlight.collector.content_guard import ContentKind, classify
from watchlight.collector.snapshot import normalize_content
from watchlight.evals.metrics import percentile, safe_ratio

if TYPE_CHECKING:
    from watchlight.evals.dataset import EvalCase, EvalDataset


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    expected_notify: bool
    predicted_notify: bool
    source_count: int
    blocked_source_count: int
    raw_change_count: int
    merged_signal_count: int
    eligible_signal_count: int
    delivered_notification_count: int
    expected_fact_count: int
    matched_fact_count: int
    processing_ms: float
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvalReport:
    dataset_name: str
    dataset_version: str
    dataset_path: str
    metrics: dict[str, int | float]
    categories: dict[str, dict[str, int | float]]
    cases: tuple[CaseResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": {
                "name": self.dataset_name,
                "version": self.dataset_version,
                "path": self.dataset_path,
            },
            "metrics": self.metrics,
            "categories": self.categories,
            "cases": [asdict(case) for case in self.cases],
        }

    def write(self, output_dir: Path | str) -> tuple[Path, Path]:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        json_path = directory / f"{self.dataset_name}-report.json"
        markdown_path = directory / f"{self.dataset_name}-report.md"
        json_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(self.to_markdown(), encoding="utf-8")
        return json_path, markdown_path

    def to_markdown(self) -> str:
        metrics = self.metrics
        lines = [
            f"# Watchlight Evaluation: {self.dataset_name}",
            "",
            f"Dataset version: `{self.dataset_version}`",
            "",
            "## Summary",
            "",
            "| Metric | Result |",
            "| --- | ---: |",
            f"| Cases | {metrics['case_count']} |",
            f"| Sources | {metrics['source_count']} |",
            f"| Notification precision | {metrics['notification_precision']:.2%} |",
            f"| Change recall | {metrics['change_recall']:.2%} |",
            f"| F1 | {metrics['f1']:.2%} |",
            f"| Duplicate compression | {metrics['duplicate_compression_rate']:.2%} |",
            f"| Expected fact coverage | {metrics['fact_coverage']:.2%} |",
            f"| False alerts / 100 cases | {metrics['false_alerts_per_100_cases']:.2f} |",
            f"| Processing latency P95 | {metrics['processing_ms_p95']:.2f} ms |",
            "",
            "## Cases",
            "",
            "| Case | Category | Expected | Predicted | Raw changes | Delivered |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for case in self.cases:
            lines.append(
                f"| {case.case_id} | {case.category} | "
                f"{str(case.expected_notify).lower()} | {str(case.predicted_notify).lower()} | "
                f"{case.raw_change_count} | {case.delivered_notification_count} |"
            )
        lines.append("")
        return "\n".join(lines)


class EvalRunner:
    def __init__(self, *, dedup_window_seconds: int = 72 * 3600) -> None:
        self.detector = ChangeDetector()
        self.deduper = CrossSourceDeduper()
        self.window = DedupWindow(seconds=dedup_window_seconds)
        self.filter = PreferenceFilter()

    def run(self, dataset: EvalDataset) -> EvalReport:
        recent: dict[tuple[str, str], int] = {}
        results = tuple(self._run_case(case, recent) for case in dataset.cases)
        metrics = self._summarize(results)
        categories = {
            category: self._summarize(tuple(item for item in results if item.category == category))
            for category in sorted({item.category for item in results})
        }
        return EvalReport(
            dataset.name,
            dataset.version,
            str(dataset.path),
            metrics,
            categories,
            results,
        )

    def _run_case(
        self, case: EvalCase, recent: dict[tuple[str, str], int]
    ) -> CaseResult:
        started = time.perf_counter()
        candidates: list[CandidateSignal] = []
        blocked = 0
        raw_changes = 0
        for index, source in enumerate(case.sources):
            before_raw = source.previous_path.read_text(encoding="utf-8")
            after_raw = source.current_path.read_text(encoding="utf-8")
            if classify(after_raw, source.http_status) is not ContentKind.TARGET:
                blocked += 1
                continue
            before = normalize_content(before_raw)
            after = normalize_content(after_raw)
            for detected in self.detector.diff(before, after):
                raw_changes += 1
                candidates.append(
                    CandidateSignal(
                        detected.evidence,
                        [f"{case.case_id}:{index}:{raw_changes}"],
                        [source.url],
                    )
                )
        merged = self.deduper.merge(candidates)
        eligible = 0
        delivered = 0
        evidence: list[str] = []
        for candidate in merged:
            evidence.append(candidate.evidence)
            verdict = self.filter.apply(
                {"trigger_condition": case.trigger_condition}, [], candidate.evidence
            )
            if not verdict.keep:
                continue
            eligible += 1
            key = self.window.key(case.task_id, candidate.evidence)
            recent_at = recent.get((case.task_id, key))
            if recent_at is not None and recent_at >= case.captured_at - self.window.seconds:
                continue
            recent[(case.task_id, key)] = case.captured_at
            delivered += 1
        evidence_text = "\n".join(evidence).lower()
        matched_facts = sum(fact.lower() in evidence_text for fact in case.expected_facts)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return CaseResult(
            case_id=case.case_id,
            category=case.category,
            expected_notify=case.expected_notify,
            predicted_notify=delivered > 0,
            source_count=len(case.sources),
            blocked_source_count=blocked,
            raw_change_count=raw_changes,
            merged_signal_count=len(merged),
            eligible_signal_count=eligible,
            delivered_notification_count=delivered,
            expected_fact_count=len(case.expected_facts),
            matched_fact_count=matched_facts,
            processing_ms=elapsed_ms,
            evidence=tuple(evidence),
        )

    @staticmethod
    def _summarize(results: tuple[CaseResult, ...]) -> dict[str, int | float]:
        true_positive = sum(item.expected_notify and item.predicted_notify for item in results)
        false_positive = sum(not item.expected_notify and item.predicted_notify for item in results)
        true_negative = sum(
            not item.expected_notify and not item.predicted_notify for item in results
        )
        false_negative = sum(item.expected_notify and not item.predicted_notify for item in results)
        precision = safe_ratio(true_positive, true_positive + false_positive)
        recall = safe_ratio(true_positive, true_positive + false_negative)
        eligible = sum(item.eligible_signal_count for item in results)
        delivered = sum(item.delivered_notification_count for item in results)
        expected_facts = sum(item.expected_fact_count for item in results)
        matched_facts = sum(item.matched_fact_count for item in results)
        return {
            "case_count": len(results),
            "source_count": sum(item.source_count for item in results),
            "positive_case_count": true_positive + false_negative,
            "negative_case_count": true_negative + false_positive,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "false_negative": false_negative,
            "notification_precision": precision,
            "change_recall": recall,
            "f1": safe_ratio(2 * precision * recall, precision + recall),
            "raw_change_count": sum(item.raw_change_count for item in results),
            "merged_signal_count": sum(item.merged_signal_count for item in results),
            "eligible_signal_count": eligible,
            "delivered_notification_count": delivered,
            "duplicate_compression_rate": 1 - safe_ratio(delivered, eligible) if eligible else 0.0,
            "blocked_source_count": sum(item.blocked_source_count for item in results),
            "fact_coverage": safe_ratio(matched_facts, expected_facts),
            "false_alerts_per_100_cases": safe_ratio(false_positive * 100, len(results)),
            "processing_ms_p50": percentile((item.processing_ms for item in results), 0.5),
            "processing_ms_p95": percentile((item.processing_ms for item in results), 0.95),
        }
