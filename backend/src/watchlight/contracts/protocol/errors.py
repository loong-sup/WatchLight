# 文件说明：本文件属于 契约层。
# 主要职责：实现 errors 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Error shape and error codes for gateway protocol."""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from watchlight.contracts.protocol.primitives import NonEmptyStr


class ErrorCodes(StrEnum):
    NOT_LINKED = "NOT_LINKED"
    NOT_PAIRED = "NOT_PAIRED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"
    APPROVAL_NOT_FOUND = "APPROVAL_NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"


class ErrorShape(BaseModel):
    """Error payload in ResponseFrame."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    code: NonEmptyStr
    message: NonEmptyStr
    details: Any | None = None
    retryable: bool | None = None
    retry_after_ms: Annotated[int, Field(ge=0)] | None = Field(default=None, alias="retryAfterMs")
