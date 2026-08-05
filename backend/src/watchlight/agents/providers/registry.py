# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Provider registry."""

from watchlight.agents.providers.base import ProviderPlugin


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderPlugin] = {}

    def register(self, provider: ProviderPlugin) -> None:
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> ProviderPlugin | None:
        return self._providers.get(provider_id)

    def list_ids(self) -> list[str]:
        return list(self._providers.keys())

    def all_models(self) -> list[dict[str, str]]:
        result = []
        for provider in self._providers.values():
            for model in provider.list_models():
                model["provider"] = provider.id
                result.append(model)
        return result
