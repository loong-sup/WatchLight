# 文件说明：本文件属于 契约层。
# 主要职责：实现 snapshot 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Snapshot and presence types for gateway protocol.

Matches TS TypeBox schemas in src/gateway/protocol/schema/snapshot.ts.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from watchlight.contracts.protocol.primitives import NonEmptyStr, StateVersion


class PresenceEntry(BaseModel):
    """A connected client's presence info."""

    model_config = ConfigDict(extra="forbid")

    host: NonEmptyStr | None = None
    ip: NonEmptyStr | None = None
    version: NonEmptyStr | None = None
    platform: NonEmptyStr | None = None
    device_family: NonEmptyStr | None = Field(default=None, alias="deviceFamily")
    model_identifier: NonEmptyStr | None = Field(default=None, alias="modelIdentifier")
    mode: NonEmptyStr | None = None
    last_input_seconds: Annotated[int, Field(ge=0)] | None = Field(
        default=None, alias="lastInputSeconds"
    )
    reason: NonEmptyStr | None = None
    tags: list[NonEmptyStr] | None = None
    text: str | None = None
    ts: Annotated[int, Field(ge=0)]
    device_id: NonEmptyStr | None = Field(default=None, alias="deviceId")
    roles: list[NonEmptyStr] | None = None
    scopes: list[NonEmptyStr] | None = None
    instance_id: NonEmptyStr | None = Field(default=None, alias="instanceId")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SessionDefaults(BaseModel):
    """Default session identifiers."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    default_agent_id: NonEmptyStr = Field(alias="defaultAgentId")
    main_key: NonEmptyStr = Field(alias="mainKey")
    main_session_key: NonEmptyStr = Field(alias="mainSessionKey")
    scope: NonEmptyStr | None = None


class UpdateAvailable(BaseModel):
    """Version update info."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    current_version: NonEmptyStr = Field(alias="currentVersion")
    latest_version: NonEmptyStr = Field(alias="latestVersion")
    channel: NonEmptyStr


class Snapshot(BaseModel):
    """Gateway state snapshot sent in HelloOk."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    presence: list[PresenceEntry]
    health: Any
    state_version: StateVersion = Field(alias="stateVersion")
    uptime_ms: Annotated[int, Field(ge=0)] = Field(alias="uptimeMs")
    config_path: NonEmptyStr | None = Field(default=None, alias="configPath")
    state_dir: NonEmptyStr | None = Field(default=None, alias="stateDir")
    session_defaults: SessionDefaults | None = Field(default=None, alias="sessionDefaults")
    auth_mode: Literal["none", "token", "password", "trusted-proxy"] | None = Field(
        default=None, alias="authMode"
    )
    update_available: UpdateAvailable | None = Field(default=None, alias="updateAvailable")
