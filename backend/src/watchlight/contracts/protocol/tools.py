# 文件说明：本文件属于 契约层。
# 主要职责：处理工具相关接口。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway tools.* method schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = Field(default=None, alias="inputSchema")


class ToolsCatalogResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    tools: list[ToolCatalogEntry]


class ToolsEffectiveResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    tools: list[ToolCatalogEntry]
    denied: list[str] | None = None
