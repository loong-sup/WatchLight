# 文件说明：本文件属于 工具系统层。
# 主要职责：集中定义类型和数据结构。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool type definitions."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    prompt_instructions: str = ""
    handler: Callable[..., Awaitable[Any]] | None = None


@dataclass
class ToolContext:
    session_key: str | None = None
    agent_id: str | None = None
    workspace: str | None = None
    channel: str | None = None
    sender_id: str | None = None
    conversation_id: str | None = None
    user_message: str | None = None
    user_id: str | None = None
    sender_is_owner: bool = False


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
