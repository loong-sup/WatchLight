# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""RuntimeRegistry — register and select agent runtimes."""

from watchlight.agents.runtime.protocol import AgentRuntime


class RuntimeRegistry:
    def __init__(self) -> None:
        self._runtimes: dict[str, AgentRuntime] = {}
        self._default: str | None = None

    def register(self, runtime: AgentRuntime, default: bool = False) -> None:
        self._runtimes[runtime.runtime_id] = runtime
        if default or self._default is None:
            self._default = runtime.runtime_id

    def get(self, runtime_id: str | None = None) -> AgentRuntime | None:
        if runtime_id:
            return self._runtimes.get(runtime_id)
        if self._default:
            return self._runtimes.get(self._default)
        return None

    def list(self) -> list[str]:
        return list(self._runtimes.keys())

    @property
    def default_id(self) -> str | None:
        return self._default
