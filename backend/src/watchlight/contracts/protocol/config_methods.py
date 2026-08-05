# 文件说明：本文件属于 契约层。
# 主要职责：实现 config methods 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway config.* method schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ConfigGetParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    key: str | None = None


class ConfigGetResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    config: dict[str, Any]


class ConfigSetParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    key: str
    value: Any


class ConfigApplyParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    config: dict[str, Any]


class ConfigPatchParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    patch: dict[str, Any]
