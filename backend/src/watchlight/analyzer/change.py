from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

_NOISE = re.compile(
    r"(?:广告|advertisement|推荐阅读|updated at|更新时间|\b\d{1,2}:\d{2}:\d{2}\b)",
    re.IGNORECASE,
)


def stable_lines(content: str) -> list[str]:
    return [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not _NOISE.search(line)
    ]


@dataclass(frozen=True, slots=True)
class DetectedChange:
    change_type: str
    evidence: str
    uncertainty_level: str


class ChangeDetector:
    def diff(self, previous: str, current: str) -> list[DetectedChange]:
        before = stable_lines(previous)
        after = stable_lines(current)
        if before == after:
            return []
        matcher = SequenceMatcher(a=before, b=after)
        changes: list[DetectedChange] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            kind = "added" if tag == "insert" else "removed" if tag == "delete" else "modified"
            evidence = "\n".join(after[j1:j2] or before[i1:i2])
            if evidence:
                changes.append(DetectedChange(kind, evidence[:4000], "low"))
        return changes
