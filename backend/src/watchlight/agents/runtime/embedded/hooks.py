# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 hooks 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool execution hooks — before/after callbacks."""

from collections.abc import Awaitable, Callable
from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("agent.hooks")

BeforeToolHook = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any] | None]]
AfterToolHook = Callable[[str, dict[str, Any], Any], Awaitable[None]]


class ToolHookRegistry:
    def __init__(self) -> None:
        self._before: list[BeforeToolHook] = []
        self._after: list[AfterToolHook] = []

    def on_before(self, hook: BeforeToolHook) -> None:
        self._before.append(hook)

    def on_after(self, hook: AfterToolHook) -> None:
        self._after.append(hook)

    async def run_before(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Run before hooks. Returns potentially modified params."""
        current_params = params
        for hook in self._before:
            result = await hook(tool_name, current_params)
            if result is not None:
                current_params = result
        return current_params

    async def run_after(self, tool_name: str, params: dict[str, Any], result: Any) -> None:
        """Run after hooks."""
        for hook in self._after:
            try:
                await hook(tool_name, params, result)
            except Exception as e:
                log.error("after_hook_error", tool=tool_name, error=str(e))
