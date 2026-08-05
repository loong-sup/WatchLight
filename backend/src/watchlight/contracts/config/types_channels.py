# 文件说明：本文件属于 契约层。
# 主要职责：实现 types channels 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Channel configuration types."""

from pydantic import BaseModel, ConfigDict


class ChannelAccountConfig(BaseModel):
    """Generic channel account — specific fields vary by channel."""

    model_config = ConfigDict(extra="allow")


class ChannelConfig(BaseModel):
    """Generic single-channel config block."""

    model_config = ConfigDict(extra="allow")
    enabled: bool | None = None
    accounts: dict[str, ChannelAccountConfig] | None = None


class ChannelsConfig(BaseModel):
    """Top-level channels config — keys are channel IDs."""

    model_config = ConfigDict(extra="allow")

    # Explicit well-known channels; others via extra="allow"
    feishu: ChannelConfig | None = None
    wecom: ChannelConfig | None = None
    telegram: ChannelConfig | None = None
    discord: ChannelConfig | None = None
    slack: ChannelConfig | None = None
