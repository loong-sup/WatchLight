from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher


def normalize_fingerprint(text: str) -> str:
    normalized = re.sub(r"\W+", " ", text.lower()).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


@dataclass(slots=True)
class CandidateSignal:
    evidence: str
    change_ids: list[str]
    source_urls: list[str]
    merge_reason: str = "single_source"


class CrossSourceDeduper:
    def __init__(self, *, similarity_threshold: float = 0.86) -> None:
        self.similarity_threshold = similarity_threshold

    def merge(self, candidates: list[CandidateSignal]) -> list[CandidateSignal]:
        merged: list[CandidateSignal] = []
        for candidate in candidates:
            target = next(
                (
                    item
                    for item in merged
                    if SequenceMatcher(a=item.evidence, b=candidate.evidence).ratio()
                    >= self.similarity_threshold
                ),
                None,
            )
            if target is None:
                merged.append(candidate)
                continue
            target.change_ids.extend(candidate.change_ids)
            target.source_urls.extend(
                url for url in candidate.source_urls if url not in target.source_urls
            )
            target.merge_reason = f"text_similarity>={self.similarity_threshold}"
        return merged


class DedupWindow:
    def __init__(self, *, seconds: int = 72 * 3600) -> None:
        self.seconds = seconds

    def key(self, task_id: str, evidence: str) -> str:
        return f"{task_id}:{normalize_fingerprint(evidence)}"
