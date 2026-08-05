# 文件说明：本文件属于 契约层。
# 主要职责：实现 commands 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway commands.* method schemas."""

from pydantic import BaseModel, ConfigDict


class CommandEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    description: str | None = None
    aliases: list[str] | None = None


class CommandsListResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    commands: list[CommandEntry]
