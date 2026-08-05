# 文件说明：本文件属于 契约层。
# 主要职责：处理模型相关接口。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway models.* method schemas."""

from pydantic import BaseModel, ConfigDict, Field


class ModelChoice(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: str
    provider: str
    label: str | None = None
    context_tokens: int | None = Field(default=None, alias="contextTokens")


class ModelsListResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    models: list[ModelChoice]
