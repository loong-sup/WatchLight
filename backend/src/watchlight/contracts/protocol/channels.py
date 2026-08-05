# 文件说明：本文件属于 契约层。
# 主要职责：实现 channels 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway channels.* method schemas."""

from pydantic import BaseModel, ConfigDict


class ChannelStatusEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    channel: str
    account_id: str | None = None
    enabled: bool | None = None
    connected: bool | None = None
    running: bool | None = None


class ChannelsStatusResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    channels: list[ChannelStatusEntry]
