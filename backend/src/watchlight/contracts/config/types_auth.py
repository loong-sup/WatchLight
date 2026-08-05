# 文件说明：本文件属于 契约层。
# 主要职责：实现 types auth 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Auth configuration types."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuthProfile(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    provider: str
    mode: str
    email: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    profiles: dict[str, AuthProfile] | None = None
    order: dict[str, list[str]] | None = None
    cooldowns: dict[str, Any] | None = None
