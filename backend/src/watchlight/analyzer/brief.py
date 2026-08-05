from __future__ import annotations

from typing import Any, Protocol

from watchlight.analyzer.degrade import handle_model_error


class BriefModelProvider(Protocol):
    async def build(self, context: dict[str, Any]) -> dict[str, Any]: ...


class DeterministicBriefProvider:
    async def build(self, context: dict[str, Any]) -> dict[str, Any]:
        evidence = str(context["evidence"])
        return {
            "facts": [evidence],
            "inferences": ["该变化与关注条件匹配。"],
            "next_steps": ["打开来源核对完整上下文。"],
        }


class BriefBuilder:
    def __init__(self, provider: BriefModelProvider | None = None) -> None:
        self.provider = provider or DeterministicBriefProvider()

    async def build(
        self,
        *,
        evidence: str,
        source_refs: list[str],
        captured_at: int | None,
        uncertainty_level: str,
    ) -> dict[str, Any]:
        try:
            content = await self.provider.build(
                {
                    "evidence": evidence,
                    "source_refs": source_refs,
                    "captured_at": captured_at,
                    "uncertainty_level": uncertainty_level,
                }
            )
        except Exception as exc:
            degraded = handle_model_error(exc)
            return {
                "facts": [],
                "inferences": [],
                "next_steps": [],
                "source_refs": source_refs,
                "captured_at": captured_at,
                "uncertainty_level": uncertainty_level,
                "sendable": degraded.sendable,
                "failure_summary": degraded.failure_summary,
            }
        sendable = bool(source_refs and captured_at and uncertainty_level != "high")
        return {
            **content,
            "source_refs": source_refs,
            "captured_at": captured_at,
            "uncertainty_level": uncertainty_level,
            "sendable": sendable,
            "failure_summary": None,
        }
