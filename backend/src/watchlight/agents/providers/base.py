# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 base 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""ProviderPlugin Protocol — LLM provider interface."""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class ProviderPlugin(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def label(self) -> str: ...

    def list_models(self) -> list[dict[str, Any]]: ...

    def create_stream(
        self, model: str, messages: list[dict[str, Any]], system: str = "", **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]: ...
