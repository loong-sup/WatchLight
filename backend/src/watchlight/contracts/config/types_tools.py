# 文件说明：本文件属于 契约层。
# 主要职责：实现 types tools 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool configuration types."""

from pydantic import BaseModel, ConfigDict


class ToolsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    deny: list[str] | None = None
    allow: list[str] | None = None
