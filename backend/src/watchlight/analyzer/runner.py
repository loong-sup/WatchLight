from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from watchlight.analyzer.brief import BriefBuilder
from watchlight.analyzer.change import ChangeDetector
from watchlight.analyzer.dedupe import CandidateSignal, CrossSourceDeduper, DedupWindow
from watchlight.analyzer.quality import classify_content_quality
from watchlight.analyzer.value import PreferenceFilter
from watchlight.storage.blobs import BlobStore
from watchlight.storage.repos.briefs import BriefsRepo
from watchlight.storage.repos.executions import ExecutionsRepo
from watchlight.storage.repos.feedback import FeedbackRepo
from watchlight.storage.repos.signals import SignalsRepo
from watchlight.storage.repos.snapshots import SnapshotsRepo
from watchlight.storage.repos.tasks import TasksRepo
from watchlight.storage.store import Store, utc_now

if TYPE_CHECKING:
    from watchlight.analyzer.brief import BriefModelProvider


class Analyzer:
    def __init__(
        self,
        store: Store,
        *,
        blob_root: Path | None = None,
        model_provider: BriefModelProvider | None = None,
    ) -> None:
        self.store = store
        self.blobs = BlobStore(store, blob_root or Path(".watchlight-state/blobs"))
        self.detector = ChangeDetector()
        self.deduper = CrossSourceDeduper()
        self.window = DedupWindow()
        self.filter = PreferenceFilter()
        self.briefs = BriefBuilder(model_provider)

    async def run(self, execution_id: str, user_id: str) -> dict[str, int | str]:
        executions = ExecutionsRepo.for_user(self.store, user_id)
        execution = executions.get(execution_id)
        if execution is None:
            raise KeyError(execution_id)
        tasks = TasksRepo.for_user(self.store, user_id)
        task = tasks.get(str(execution["task_id"]))
        if task is None:
            raise KeyError(str(execution["task_id"]))
        task_version = {
            "trigger_condition": json.loads(str(task["trigger_condition_json"]))
        }
        snapshots = SnapshotsRepo.for_user(self.store, user_id)
        candidates: list[CandidateSignal] = []
        for snapshot in snapshots.list_for_execution(execution_id):
            previous_id = snapshot.get("previous_snapshot_id")
            if not previous_id:
                continue
            previous = snapshots.get_snapshot(str(previous_id))
            if previous is None:
                continue
            before = self.blobs.get(str(previous["normalized_ref"])).decode()
            after = self.blobs.get(str(snapshot["normalized_ref"])).decode()
            for detected in self.detector.diff(before, after):
                change = snapshots.insert_change(
                    {
                        "execution_id": execution_id,
                        "snapshot_id": snapshot["snapshot_id"],
                        "previous_snapshot_id": previous_id,
                        "change_type": detected.change_type,
                        "evidence_ref": detected.evidence,
                        "uncertainty_level": detected.uncertainty_level,
                    }
                )
                candidates.append(
                    CandidateSignal(
                        detected.evidence,
                        [str(change["change_id"])],
                        [str(snapshot["source_url"])],
                    )
                )
        merged = self.deduper.merge(candidates)
        signals_repo = SignalsRepo.for_user(self.store, user_id)
        preferences = FeedbackRepo.for_user(self.store, user_id).list_preferences(
            str(task["task_id"])
        )
        signal_count = 0
        sendable_count = 0
        for candidate in merged:
            verdict = self.filter.apply(task_version, preferences, candidate.evidence)
            quality = classify_content_quality(candidate.evidence)
            dedup_key = self.window.key(str(task["task_id"]), candidate.evidence)
            duplicate = signals_repo.find_recent(
                str(task["task_id"]), dedup_key, utc_now() - self.window.seconds
            )
            status = (
                "suppressed"
                if not quality.safe or not verdict.keep
                else "deduped"
                if duplicate
                else "proposed"
            )
            signal = signals_repo.insert(
                {
                    "execution_id": execution_id,
                    "task_id": task["task_id"],
                    "change_ids": candidate.change_ids,
                    "source_urls": candidate.source_urls,
                    "captured_at": utc_now(),
                    "relevance": verdict.relevance,
                    "importance": verdict.importance,
                    "novelty": verdict.novelty,
                    "source_credibility": verdict.source_credibility,
                    "uncertainty_level": verdict.uncertainty_level,
                    "status": status,
                    "dedup_key": dedup_key,
                }
            )
            signal_count += 1
            brief_data = await self.briefs.build(
                evidence=candidate.evidence,
                source_refs=candidate.source_urls,
                captured_at=int(signal["captured_at"]),
                uncertainty_level=verdict.uncertainty_level,
            )
            if status != "proposed":
                brief_data["sendable"] = False
            if not quality.safe:
                brief_data["facts"] = []
                brief_data["failure_summary"] = f"content_quality:{quality.reason}"
            BriefsRepo.for_user(self.store, user_id).insert(
                {"execution_id": execution_id, "signal_ids": [signal["signal_id"]], **brief_data}
            )
            sendable_count += int(bool(brief_data["sendable"]))
        current_status = str(execution["status"])
        final_status = "partial" if current_status == "partial" else "succeeded"
        executions.settle(
            execution_id,
            final_status,
            counts={
                "source_count": int(execution["source_count"]),
                "change_count": len(candidates),
                "signal_count": signal_count,
            },
        )
        return {
            "change_count": len(candidates),
            "signal_count": signal_count,
            "sendable_count": sendable_count,
            "status": final_status,
        }
