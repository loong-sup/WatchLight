from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DegradedBrief:
    sendable: bool = False
    failure_summary: str = "model provider unavailable"


def handle_model_error(error: BaseException) -> DegradedBrief:
    return DegradedBrief(failure_summary=f"model_provider_failed:{type(error).__name__}")
