# 文件说明：本文件属于 契约层。
# 主要职责：实现 types memory 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Memory configuration types."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    backend: str | None = None
    citations: str | None = None
    qmd: dict[str, Any] | None = None
