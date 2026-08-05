# 文件说明：本文件属于 契约层。
# 主要职责：实现 agents 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway agents.* method schemas."""

from pydantic import BaseModel, ConfigDict, Field


class AgentSummary(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: str
    workspace: str | None = None
    session_count: int | None = Field(default=None, alias="sessionCount")


class AgentsListResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    agents: list[AgentSummary]


class AgentsCreateParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    workspace: str | None = None
