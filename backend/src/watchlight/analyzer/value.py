from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Verdict:
    relevance: float
    importance: float
    novelty: float
    source_credibility: float
    uncertainty_level: str
    keep: bool
    rationale: str


class PreferenceFilter:
    def apply(
        self,
        task_version: dict[str, Any],
        preferences: list[dict[str, Any]],
        evidence: str,
    ) -> Verdict:
        lowered = evidence.lower()
        condition = task_version.get("trigger_condition", {})
        must = [str(item).lower() for item in condition.get("must_contain", [])]
        excluded = [str(item).lower() for item in condition.get("must_not_contain", [])]
        for preference in preferences:
            if preference.get("revoked_at"):
                continue
            value = json.loads(str(preference.get("value_json", '""')))
            if preference.get("kind") == "include":
                must.append(str(value).lower())
            elif preference.get("kind") == "exclude":
                excluded.append(str(value).lower())
        hits_required = not must or any(term in lowered for term in must)
        hits_excluded = any(term in lowered for term in excluded)
        keep = hits_required and not hits_excluded
        return Verdict(
            relevance=0.9 if hits_required else 0.2,
            importance=0.72 if keep else 0.2,
            novelty=0.85,
            source_credibility=0.7,
            uncertainty_level="low",
            keep=keep,
            rationale="matched task conditions" if keep else "filtered by explicit task conditions",
        )
