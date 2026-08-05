# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 inventory 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool inventory — dynamic effective tools based on session context."""

from typing import Any

from watchlight.tools.policy import ToolPolicy
from watchlight.tools.registry import ToolRegistry
from watchlight.tools.types import ToolDefinition


class ToolInventory:
    """Compute effective tool set for a given session context."""

    def __init__(self, registry: ToolRegistry, default_policy: ToolPolicy | None = None) -> None:
        self._registry = registry
        self._default_policy = default_policy or ToolPolicy()
        self._overrides: dict[str, ToolPolicy] = {}  # session_key → policy

    def set_override(self, session_key: str, policy: ToolPolicy) -> None:
        self._overrides[session_key] = policy

    def get_effective(self, session_key: str | None = None) -> list[ToolDefinition]:
        policy = self._overrides.get(session_key or "", self._default_policy)
        return [t for t in self._registry.list_all() if policy.is_allowed(t.name)]

    def get_effective_catalog(self, session_key: str | None = None) -> list[dict[str, Any]]:
        tools = self.get_effective(session_key)
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in tools
        ]
