# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 compaction 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session compaction — agent-aware context governance system.

Not a chat summarizer. This is a runtime-continuable context compactor that:
1. Treats tool calls, code, decisions, and pending actions as first-class objects
2. Produces structured compaction checkpoints (not destructive rewrites)
3. Dynamically triggers based on model context window + message structure
4. Validates summary quality and can roll back on failure
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from watchlight.contracts.agent.runtime import CompactionResult
from watchlight.core.logging import get_logger

log = get_logger("agent.compaction")

# ── Constants ─────────────────────────────────────────────────────

COMPACTION_TIMEOUT_S = 900  # 15 minutes (matching TS)
MIN_MESSAGES_TO_COMPACT = 12  # Don't compact if fewer than this
DEFAULT_KEEP_RECENT = 10

# Dynamic trigger thresholds
TRIGGER_TOKEN_RATIO = 0.75  # Trigger at 75% of context window
URGENT_TOKEN_RATIO = 0.90  # Urgent compact at 90%

# Summary prompt — agent-aware, not just chat summary
COMPACTION_SYSTEM_PROMPT = (
    "You are summarizing an AI agent's conversation history for context continuation.\n\n"
    "CRITICAL: This summary will replace the original messages. The agent must be able "
    "to continue working from this summary alone.\n\n"
    "Preserve these elements with high priority:\n"
    "1. TOOL CALLS & RESULTS: What tools were called, what they returned (especially errors)\n"
    "2. CODE: File paths, function names, code snippets that were discussed or modified\n"
    "3. DECISIONS: What was decided, why, and what alternatives were rejected\n"
    "4. PENDING ACTIONS: Anything the user asked for that hasn't been completed yet\n"
    "5. USER PREFERENCES: How the user wants things done (language, style, constraints)\n"
    "6. KEY FACTS: Names, URLs, credentials references, configuration values\n\n"
    "Format as structured notes, not prose. Use the same language as the conversation."
)


# ── Types ─────────────────────────────────────────────────────────


@dataclass
class CompactionCheckpoint:
    """Persistent record of a compaction event."""

    version: int
    timestamp: int
    reason: str  # "overflow" | "timeout" | "manual" | "scheduled"
    messages_before: int
    messages_after: int
    tokens_before: int
    tokens_after: int
    summary_length: int
    quality_score: float  # 0.0-1.0, based on validation
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactionContext:
    """Input context for compaction decisions."""

    context_window: int = 32000
    current_tokens: int = 0
    message_count: int = 0
    tool_call_count: int = 0
    last_compaction_at: int = 0
    compaction_count: int = 0


# ── Message Classification ────────────────────────────────────────


def _classify_message(msg: dict[str, Any]) -> str:
    """Classify a message for compaction priority.

    Returns a compact category label such as tool_call, code, user, or assistant.
    """
    role = msg.get("role", "")
    content = str(msg.get("content", ""))

    if role == "tool":
        return "tool_result"
    if msg.get("tool_calls"):
        return "tool_call"
    if role == "system":
        return "system"
    if role == "user":
        return "user"
    if role == "assistant":
        # Check for code content
        if "```" in content or "def " in content or "class " in content:
            return "code"
        return "assistant"
    return "other"


def _extract_structured_content(messages: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Extract structured elements from messages for high-fidelity summarization."""
    extracted: dict[str, list[str]] = {
        "tool_calls": [],
        "tool_results": [],
        "code_snippets": [],
        "decisions": [],
        "user_requests": [],
        "errors": [],
    }

    for msg in messages:
        content = str(msg.get("content", ""))
        category = _classify_message(msg)

        if category == "tool_call":
            calls = msg.get("tool_calls", [])
            for call in calls:
                fn = call.get("function", {})
                name = fn.get("name", call.get("name", "unknown"))
                extracted["tool_calls"].append(f"{name}(...)")

        elif category == "tool_result":
            # Preserve error results with higher priority
            if any(kw in content.lower() for kw in ("error", "failed", "exception", "traceback")):
                extracted["errors"].append(content[:500])
            else:
                extracted["tool_results"].append(content[:200])

        elif category == "code":
            # Extract code blocks
            import re

            blocks = re.findall(r"```[\s\S]*?```", content)
            for block in blocks[:5]:
                extracted["code_snippets"].append(block[:300])

        elif category == "user":
            extracted["user_requests"].append(content[:300])

    return extracted


# ── Trigger Logic ─────────────────────────────────────────────────


def should_compact(
    messages: list[dict[str, Any]],
    context_window: int = 32000,
    threshold: float = TRIGGER_TOKEN_RATIO,
) -> bool:
    """Dynamic compaction trigger based on context pressure."""
    from watchlight.agents.runtime.embedded.tool_result import estimate_tokens

    if len(messages) < MIN_MESSAGES_TO_COMPACT:
        return False

    total_tokens = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
    ratio = total_tokens / max(context_window, 1)

    # Dynamic threshold: lower when many tool results (they compress well)
    tool_count = sum(1 for m in messages if m.get("role") == "tool")
    adjusted_threshold = threshold - (tool_count * 0.01)  # 1% lower per tool result
    adjusted_threshold = max(adjusted_threshold, 0.5)  # Floor at 50%

    return ratio > adjusted_threshold


def compute_compaction_reason(
    messages: list[dict[str, Any]],
    context_window: int = 32000,
    explicit_reason: str | None = None,
) -> str:
    """Determine the compaction reason for checkpoint metadata."""
    if explicit_reason:
        return explicit_reason
    from watchlight.agents.runtime.embedded.tool_result import estimate_tokens

    total = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
    ratio = total / max(context_window, 1)
    if ratio > URGENT_TOKEN_RATIO:
        return "overflow"
    if ratio > TRIGGER_TOKEN_RATIO:
        return "budget"
    return "manual"


# ── Core Compaction ───────────────────────────────────────────────


async def compact_messages(
    messages: list[dict[str, Any]],
    summarize_fn: Any | None = None,
    keep_recent: int = DEFAULT_KEEP_RECENT,
    timeout_s: float = COMPACTION_TIMEOUT_S,
    context_window: int = 32000,
    reason: str = "auto",
) -> CompactionResult:
    """Compact message history with agent-aware structured summarization.

    Modifies messages in-place. Produces a summary that preserves tool calls,
    code, decisions, and pending actions — not just a chat summary.

    Args:
        messages: Full message history (mutated in place).
        summarize_fn: async (text) -> summary string.
        keep_recent: Number of recent messages to preserve verbatim.
        timeout_s: Maximum time for compaction.
        context_window: Model context window for dynamic keep_recent.
        reason: Why compaction is happening.
    """
    from watchlight.agents.runtime.embedded.tool_result import estimate_tokens

    messages_before = len(messages)
    tokens_before = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)

    if messages_before <= keep_recent + 2:
        return CompactionResult(messages_before=messages_before, messages_after=messages_before)

    if not _has_real_conversation(messages):
        return CompactionResult(messages_before=messages_before, messages_after=messages_before)

    # Dynamic keep_recent: keep more if context window is large
    if context_window > 100000:
        keep_recent = min(keep_recent + 5, messages_before - 2)

    # Separate old and recent
    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]

    # Extract structured content for high-fidelity summary
    structured = _extract_structured_content(old_messages)

    # Build summarization input — structured, not just linear text
    summary_parts: list[str] = []
    summary_parts.append(f"=== Conversation History ({len(old_messages)} messages) ===\n")

    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))
        category = _classify_message(msg)

        # Priority-based content inclusion
        if category in ("tool_call", "tool_result", "code"):
            summary_parts.append(f"[{role}/{category}]: {content[:2000]}")
        elif category in ("user", "assistant"):
            summary_parts.append(f"[{role}]: {content[:1000]}")
        # Skip system messages and other in summary input

    # Append structured extraction hints
    if structured["errors"]:
        summary_parts.append("\n=== Errors encountered ===\n" + "\n".join(structured["errors"][:5]))
    if structured["tool_calls"]:
        summary_parts.append("\n=== Tools used ===\n" + ", ".join(set(structured["tool_calls"])))

    old_text = "\n".join(summary_parts)

    # Generate summary with timeout + quality validation
    summary: str
    summary_quality = 1.0
    if summarize_fn:
        try:
            raw_summary = await asyncio.wait_for(
                summarize_fn(old_text),
                timeout=timeout_s,
            )
            # Quality validation
            summary_quality = _validate_summary_quality(raw_summary, old_messages, structured)
            if summary_quality < 0.3:
                log.warning(
                    "compaction_low_quality",
                    quality=summary_quality,
                    summary_preview=raw_summary[:100],
                )
                # Use fallback instead of bad summary
                summary = _build_fallback_summary(old_messages, structured)
                summary_quality = 0.5
            else:
                summary = raw_summary

        except TimeoutError:
            log.error("compaction_timeout", timeout_s=timeout_s)
            summary = _build_fallback_summary(old_messages, structured)
            summary_quality = 0.3
        except Exception as e:
            log.error("compaction_summary_failed", error=str(e))
            summary = _build_fallback_summary(old_messages, structured)
            summary_quality = 0.3
    else:
        summary = _build_fallback_summary(old_messages, structured)
        summary_quality = 0.5

    # Build summary message with structured metadata
    summary_msg: dict[str, Any] = {
        "role": "system",
        "content": (
            f"[Compaction v{int(time.time())}] "
            f"Context compacted from {len(old_messages)} messages. "
            f"Reason: {reason}.\n\n{summary}"
        ),
        "_compaction": {
            "version": int(time.time()),
            "reason": reason,
            "messages_compacted": len(old_messages),
            "quality_score": summary_quality,
            "tools_used": list(set(structured["tool_calls"])),
            "had_errors": len(structured["errors"]) > 0,
        },
    }

    # Replace in place
    messages.clear()
    messages.append(summary_msg)
    messages.extend(recent_messages)

    tokens_after = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)

    result = CompactionResult(
        messages_before=messages_before,
        messages_after=len(messages),
        summary=summary[:500],
    )
    log.info(
        "compaction_done",
        before=messages_before,
        after=result.messages_after,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        quality=summary_quality,
        reason=reason,
    )
    return result


# ── Quality Validation ────────────────────────────────────────────


def _validate_summary_quality(
    summary: str,
    original_messages: list[dict[str, Any]],
    structured: dict[str, list[str]],
) -> float:
    """Score summary quality 0.0-1.0 based on content preservation."""
    if not summary or len(summary) < 50:
        return 0.0

    score = 0.5  # Baseline

    # Check if tool names are mentioned
    if structured["tool_calls"]:
        tool_names = set(structured["tool_calls"])
        mentioned = sum(1 for t in tool_names if t.split("(")[0] in summary)
        score += 0.2 * (mentioned / max(len(tool_names), 1))

    # Check if errors are mentioned
    if structured["errors"] and any(kw in summary.lower() for kw in ("error", "failed", "issue")):
        score += 0.1

    # Check reasonable length (not too short, not just echoing)
    if len(summary) > 200:
        score += 0.1
    if len(summary) < len("\n".join(str(m.get("content", ""))[:50] for m in original_messages)):
        score += 0.1  # Actually compressed

    return min(score, 1.0)


def _build_fallback_summary(
    messages: list[dict[str, Any]],
    structured: dict[str, list[str]],
) -> str:
    """Build a structured fallback summary without LLM."""
    parts: list[str] = []
    parts.append(f"Previous conversation ({len(messages)} messages compacted):")

    # User requests
    if structured["user_requests"]:
        parts.append("\nUser discussed:")
        for req in structured["user_requests"][:5]:
            parts.append(f"  - {req[:150]}")

    # Tools used
    if structured["tool_calls"]:
        parts.append(f"\nTools used: {', '.join(set(structured['tool_calls'][:10]))}")

    # Errors
    if structured["errors"]:
        parts.append(f"\nErrors encountered: {len(structured['errors'])}")
        parts.append(f"  Last error: {structured['errors'][-1][:200]}")

    # Code
    if structured["code_snippets"]:
        parts.append(f"\nCode discussed: {len(structured['code_snippets'])} snippet(s)")

    return "\n".join(parts)


# ── Helpers ───────────────────────────────────────────────────────


def _has_real_conversation(messages: list[dict[str, Any]]) -> bool:
    real = sum(
        1
        for m in messages
        if m.get("role") in ("user", "assistant") and str(m.get("content", "")).strip()
    )
    return real >= 2


def build_compaction_checkpoint(
    result: CompactionResult,
    reason: str,
    quality: float,
    context_window: int = 32000,
) -> CompactionCheckpoint:
    """Build a checkpoint record for session persistence."""
    return CompactionCheckpoint(
        version=int(time.time()),
        timestamp=int(time.time() * 1000),
        reason=reason,
        messages_before=result.messages_before,
        messages_after=result.messages_after,
        tokens_before=0,  # Set by caller
        tokens_after=0,  # Set by caller
        summary_length=len(result.summary or ""),
        quality_score=quality,
    )
