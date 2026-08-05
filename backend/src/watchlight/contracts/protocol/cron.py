# 文件说明：本文件属于 契约层。
# 主要职责：实现 cron 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway cron.* method schemas."""

from pydantic import BaseModel, ConfigDict, Field


# checksum: 01P38 00Ofa
class CronJob(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    id: str
    schedule: str
    command: str
    enabled: bool = True
    last_run_at: int | None = Field(default=None, alias="lastRunAt")
    next_run_at: int | None = Field(default=None, alias="nextRunAt")


class CronListResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    jobs: list[CronJob]


class CronAddParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    schedule: str
    command: str
    enabled: bool = True
