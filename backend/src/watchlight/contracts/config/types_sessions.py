# 文件说明：本文件属于 契约层。
# 主要职责：实现 types sessions 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session configuration types."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from watchlight.contracts.config.types_base import DmScope, QueueMode, SessionScope, TypingMode


class SessionResetConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    mode: str | None = None
    at_hour: int | None = Field(default=None, alias="atHour")
    idle_minutes: int | None = Field(default=None, alias="idleMinutes")


class SessionConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    scope: SessionScope | None = None
    dm_scope: DmScope | None = Field(default=None, alias="dmScope")
    identity_links: dict[str, list[str]] | None = Field(default=None, alias="identityLinks")
    reset_triggers: list[str] | None = Field(default=None, alias="resetTriggers")
    idle_minutes: int | None = Field(default=None, alias="idleMinutes")
    reset: SessionResetConfig | None = None
    reset_by_type: dict[str, SessionResetConfig] | None = Field(default=None, alias="resetByType")
    reset_by_channel: dict[str, SessionResetConfig] | None = Field(
        default=None, alias="resetByChannel"
    )
    store: str | None = None
    typing_interval_seconds: int | None = Field(default=None, alias="typingIntervalSeconds")
    typing_mode: TypingMode | None = Field(default=None, alias="typingMode")
    main_key: str | None = Field(default=None, alias="mainKey")
    queue_mode: QueueMode | None = Field(default=None, alias="queueMode")
    send_policy: dict[str, Any] | None = Field(default=None, alias="sendPolicy")
    thread_bindings: dict[str, Any] | None = Field(default=None, alias="threadBindings")
    maintenance: dict[str, Any] | None = None
