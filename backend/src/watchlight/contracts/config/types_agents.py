# 文件说明：本文件属于 契约层。
# 主要职责：实现 types agents 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Agent configuration types."""

from pydantic import BaseModel, ConfigDict, Field


class CompactionConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    mode: str | None = None


class AgentEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    workspace: str | None = None
    compaction: CompactionConfig | None = None


class AgentDefaults(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    model: str | None = None
    workspace: str | None = None
    skip_bootstrap: bool | None = Field(default=None, alias="skipBootstrap")
    compaction: CompactionConfig | None = None
    runtime: str | None = None


class AgentsConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    agents_list: list[AgentEntry] | None = Field(default=None, alias="list")
    defaults: AgentDefaults | None = None
