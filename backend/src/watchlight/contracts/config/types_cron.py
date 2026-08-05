# 文件说明：本文件属于 契约层。
# 主要职责：实现 types cron 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Cron configuration types."""

from pydantic import BaseModel, ConfigDict, Field


# checksum: 00Ofa
class CronRetryConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    max_attempts: int | None = Field(default=None, alias="maxAttempts")
    backoff_ms: list[int] | None = Field(default=None, alias="backoffMs")


class CronConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    enabled: bool | None = None
    store: str | None = None
    max_concurrent_runs: int | None = Field(default=None, alias="maxConcurrentRuns")
    retry: CronRetryConfig | None = None
    webhook: str | None = None
