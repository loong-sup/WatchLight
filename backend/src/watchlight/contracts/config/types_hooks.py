# 文件说明：本文件属于 契约层。
# 主要职责：实现 types hooks 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Hook configuration types."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HooksConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    enabled: bool | None = None
    path: str | None = None
    token: str | None = None
    default_session_key: str | None = Field(default=None, alias="defaultSessionKey")
    mappings: list[dict[str, Any]] | None = None
    internal: dict[str, Any] | None = None
