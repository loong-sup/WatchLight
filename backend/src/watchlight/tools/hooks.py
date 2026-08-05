# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 hooks 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool hooks — before/after execution callbacks."""

from collections.abc import Awaitable, Callable
from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("tools.hooks")

BeforeHook = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any] | None]]
AfterHook = Callable[[str, dict[str, Any], Any], Awaitable[None]]


class ToolHooks:
    def __init__(self) -> None:
        self._before: list[BeforeHook] = []
        self._after: list[AfterHook] = []

    def register_before(self, hook: BeforeHook) -> None:
        self._before.append(hook)

    def register_after(self, hook: AfterHook) -> None:
        self._after.append(hook)

    async def run_before(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        current = params
        for hook in self._before:
            result = await hook(name, current)
            if result is not None:
                current = result
        return current

    async def run_after(self, name: str, params: dict[str, Any], result: Any) -> None:
        for hook in self._after:
            try:
                await hook(name, params, result)
            except Exception as e:
                log.error("tool_after_hook_error", tool=name, error=str(e))
