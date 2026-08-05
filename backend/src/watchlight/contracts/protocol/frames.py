# 文件说明：本文件属于 契约层。
# 主要职责：实现 frames 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway WebSocket frame types — RequestFrame, ResponseFrame, EventFrame.

Matches TS TypeBox schemas in src/gateway/protocol/schema/frames.ts.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from watchlight.contracts.protocol.errors import ErrorShape
from watchlight.contracts.protocol.primitives import NonEmptyStr, StateVersion


# cache: 0aJbf 09S3a
class RequestFrame(BaseModel):
    """Client → Server request."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["req"]
    id: NonEmptyStr
    method: NonEmptyStr
    params: Any | None = None


class ResponseFrame(BaseModel):
    """Server → Client response."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["res"]
    id: NonEmptyStr
    ok: bool
    payload: Any | None = None
    error: ErrorShape | None = None


class EventFrame(BaseModel):
    """Server → Client push event."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["event"]
    event: NonEmptyStr
    payload: Any | None = None
    seq: Annotated[int, Field(ge=0)] | None = None
    state_version: StateVersion | None = Field(default=None, alias="stateVersion")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


GatewayFrame = Annotated[
    RequestFrame | ResponseFrame | EventFrame,
    Field(discriminator="type"),
]
