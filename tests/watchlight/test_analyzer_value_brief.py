from __future__ import annotations

from typing import Any

import pytest
from watchlight.analyzer.brief import BriefBuilder
from watchlight.analyzer.value import PreferenceFilter


class FailingProvider:
    async def build(self, context: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("provider down")


@pytest.mark.asyncio
async def test_brief_requires_source_time_and_low_uncertainty() -> None:
    builder = BriefBuilder()
    good = await builder.build(
        evidence="release 2",
        source_refs=["https://example.com"],
        captured_at=10,
        uncertainty_level="low",
    )
    assert good["sendable"] is True
    missing = await builder.build(
        evidence="release 2", source_refs=[], captured_at=10, uncertainty_level="low"
    )
    assert missing["sendable"] is False
    uncertain = await builder.build(
        evidence="release 2",
        source_refs=["https://example.com"],
        captured_at=10,
        uncertainty_level="high",
    )
    assert uncertain["sendable"] is False


@pytest.mark.asyncio
async def test_model_failure_is_not_faked_as_success() -> None:
    result = await BriefBuilder(FailingProvider()).build(
        evidence="release",
        source_refs=["https://example.com"],
        captured_at=10,
        uncertainty_level="low",
    )
    assert result["sendable"] is False
    assert str(result["failure_summary"]).startswith("model_provider_failed")


def test_explicit_conditions_control_verdict() -> None:
    filter_ = PreferenceFilter()
    task = {"trigger_condition": {"must_contain": ["release"], "must_not_contain": ["beta"]}}
    assert filter_.apply(task, [], "stable release").keep
    assert not filter_.apply(task, [], "beta release").keep
