# 文件说明：本文件属于 契约层。
# 主要职责：实现 hello 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Connect handshake types — ConnectParams and HelloOk.

Matches TS TypeBox schemas in src/gateway/protocol/schema/frames.ts.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from watchlight.contracts.protocol.primitives import NonEmptyStr
from watchlight.contracts.protocol.snapshot import Snapshot


class DeviceAuth(BaseModel):
    """Device authentication payload."""

    model_config = ConfigDict(extra="forbid")

    id: NonEmptyStr
    public_key: NonEmptyStr = Field(alias="publicKey")
    signature: NonEmptyStr
    signed_at: Annotated[int, Field(ge=0)] = Field(alias="signedAt")
    nonce: NonEmptyStr

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ConnectAuth(BaseModel):
    """Authentication credentials in connect request."""

    model_config = ConfigDict(extra="forbid")

    token: str | None = None
    bootstrap_token: str | None = Field(default=None, alias="bootstrapToken")
    device_token: str | None = Field(default=None, alias="deviceToken")
    password: str | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ClientInfo(BaseModel):
    """Client identification in connect request."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    display_name: NonEmptyStr | None = Field(default=None, alias="displayName")
    version: NonEmptyStr
    platform: NonEmptyStr
    device_family: NonEmptyStr | None = Field(default=None, alias="deviceFamily")
    model_identifier: NonEmptyStr | None = Field(default=None, alias="modelIdentifier")
    mode: str
    instance_id: NonEmptyStr | None = Field(default=None, alias="instanceId")


class ConnectParams(BaseModel):
    """Parameters for the 'connect' method request."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    min_protocol: Annotated[int, Field(ge=1)] = Field(alias="minProtocol")
    max_protocol: Annotated[int, Field(ge=1)] = Field(alias="maxProtocol")
    client: ClientInfo
    caps: list[NonEmptyStr] | None = None
    commands: list[NonEmptyStr] | None = None
    permissions: dict[str, bool] | None = None
    path_env: str | None = Field(default=None, alias="pathEnv")
    role: NonEmptyStr | None = None
    scopes: list[NonEmptyStr] | None = None
    device: DeviceAuth | None = None
    auth: ConnectAuth | None = None
    locale: str | None = None
    user_agent: str | None = Field(default=None, alias="userAgent")


class ServerInfo(BaseModel):
    """Server identification in HelloOk."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: NonEmptyStr
    conn_id: NonEmptyStr = Field(alias="connId")


class Features(BaseModel):
    """Supported methods and events."""

    model_config = ConfigDict(extra="forbid")

    methods: list[NonEmptyStr]
    events: list[NonEmptyStr]


class Policy(BaseModel):
    """Connection policy limits."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    max_payload: Annotated[int, Field(ge=1)] = Field(alias="maxPayload")
    max_buffered_bytes: Annotated[int, Field(ge=1)] = Field(alias="maxBufferedBytes")
    tick_interval_ms: Annotated[int, Field(ge=1)] = Field(alias="tickIntervalMs")


class DeviceTokenEntry(BaseModel):
    """Individual device token in auth response."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    device_token: NonEmptyStr = Field(alias="deviceToken")
    role: NonEmptyStr
    scopes: list[NonEmptyStr]
    issued_at_ms: Annotated[int, Field(ge=0)] = Field(alias="issuedAtMs")


class HelloOkAuth(BaseModel):
    """Auth info returned in HelloOk."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    device_token: NonEmptyStr = Field(alias="deviceToken")
    role: NonEmptyStr
    scopes: list[NonEmptyStr]
    issued_at_ms: Annotated[int, Field(ge=0)] | None = Field(default=None, alias="issuedAtMs")
    device_tokens: list[DeviceTokenEntry] | None = Field(default=None, alias="deviceTokens")


class HelloOk(BaseModel):
    """Server response to successful connect handshake."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["hello-ok"]
    protocol: Annotated[int, Field(ge=1)]
    server: ServerInfo
    features: Features
    snapshot: Snapshot
    canvas_host_url: NonEmptyStr | None = Field(default=None, alias="canvasHostUrl")
    auth: HelloOkAuth | None = None
    policy: Policy
