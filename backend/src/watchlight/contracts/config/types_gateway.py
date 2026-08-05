# 文件说明：本文件属于 契约层。
# 主要职责：实现 types gateway 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway configuration types."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from watchlight.contracts.config.types_base import GatewayAuthMode, GatewayBindMode


class GatewayRateLimitConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    max_attempts: int | None = Field(default=None, alias="maxAttempts")
    window_ms: int | None = Field(default=None, alias="windowMs")
    lockout_ms: int | None = Field(default=None, alias="lockoutMs")
    exempt_loopback: bool | None = Field(default=None, alias="exemptLoopback")


class GatewayAuthConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    mode: GatewayAuthMode | None = None
    token: str | None = None
    password: str | None = None
    allow_tailscale: bool | None = Field(default=None, alias="allowTailscale")
    rate_limit: GatewayRateLimitConfig | None = Field(default=None, alias="rateLimit")


class ControlUiConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    enabled: bool | None = None
    base_path: str | None = Field(default=None, alias="basePath")
    allowed_origins: list[str] | None = Field(default=None, alias="allowedOrigins")


class TlsConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    enabled: bool | None = None
    auto_generate: bool | None = Field(default=None, alias="autoGenerate")
    cert_path: str | None = Field(default=None, alias="certPath")
    key_path: str | None = Field(default=None, alias="keyPath")


class GatewayReloadConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    mode: str | None = None
    debounce_ms: int | None = Field(default=None, alias="debounceMs")


class GatewayRemoteConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    url: str | None = None
    transport: str | None = None
    token: str | None = None
    password: str | None = None


class GatewayConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    port: int | None = None
    mode: str | None = None
    bind: GatewayBindMode | str | None = None
    custom_bind_host: str | None = Field(default=None, alias="customBindHost")
    control_ui: ControlUiConfig | None = Field(default=None, alias="controlUi")
    auth: GatewayAuthConfig | None = None
    tls: TlsConfig | None = None
    reload: GatewayReloadConfig | None = None
    remote: GatewayRemoteConfig | None = None
    channel_health_check_minutes: int | None = Field(
        default=None, alias="channelHealthCheckMinutes"
    )
    webchat: dict[str, Any] | None = None
    http: dict[str, Any] | None = None
    nodes: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None
