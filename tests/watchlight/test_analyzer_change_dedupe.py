from __future__ import annotations

from watchlight.analyzer.change import ChangeDetector
from watchlight.analyzer.dedupe import CandidateSignal, CrossSourceDeduper


def test_noise_only_change_is_ignored() -> None:
    detector = ChangeDetector()
    assert detector.diff("Product A\n更新时间 10:00:00", "Product A\n更新时间 11:00:00") == []


def test_cross_source_merge_retains_sources() -> None:
    merged = CrossSourceDeduper(similarity_threshold=0.7).merge(
        [
            CandidateSignal("Python 4 released today", ["c1"], ["https://a.example"]),
            CandidateSignal("Python 4 released today!", ["c2"], ["https://b.example"]),
        ]
    )
    assert len(merged) == 1
    assert set(merged[0].source_urls) == {"https://a.example", "https://b.example"}
    assert "similarity" in merged[0].merge_reason
