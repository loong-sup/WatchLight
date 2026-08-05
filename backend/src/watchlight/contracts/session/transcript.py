# 文件说明：本文件属于 契约层。
# 主要职责：实现 transcript 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Transcript line types for JSONL session files."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class TranscriptLine(BaseModel):
    """A single line in a session .jsonl transcript file.

    Uses extra='allow' because transcript lines can have many provider-specific fields.
    """

    model_config = ConfigDict(extra="allow")

    role: str
    content: str | None = None
    ts: int | None = None
    usage: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None
