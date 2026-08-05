# 文件说明：本文件属于 契约层。
# 主要职责：实现 primitives 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Primitive types shared across protocol schemas."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonEmptyStr = Annotated[str, Field(min_length=1)]


class StateVersion(BaseModel):
    """Monotonically increasing version counters for state categories."""

    model_config = ConfigDict(extra="forbid")

    presence: Annotated[int, Field(ge=0)]
    health: Annotated[int, Field(ge=0)]
