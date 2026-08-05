# 文件说明：本文件属于 契约层。
# 主要职责：处理会话相关接口。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway sessions.* method schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionsListParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    agent_id: str | None = Field(default=None, alias="agentId")
    filter: str | None = None
    limit: int | None = None
    offset: int | None = None


class SessionsListResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    sessions: list[dict[str, Any]]
    total: int | None = None


class SessionsSendParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    session_key: str = Field(alias="sessionKey")
    message: str
    agent_id: str | None = Field(default=None, alias="agentId")


class SessionsAbortParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    session_key: str = Field(alias="sessionKey")
    agent_id: str | None = Field(default=None, alias="agentId")


class SessionsCreateParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    session_key: str = Field(alias="sessionKey")
    agent_id: str | None = Field(default=None, alias="agentId")
    label: str | None = None


class SessionsPatchParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    session_key: str = Field(alias="sessionKey")
    agent_id: str | None = Field(default=None, alias="agentId")
    patch: dict[str, Any]


class SessionsResetParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    session_key: str = Field(alias="sessionKey")
    agent_id: str | None = Field(default=None, alias="agentId")


class SessionsDeleteParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    session_key: str = Field(alias="sessionKey")
    agent_id: str | None = Field(default=None, alias="agentId")


class SessionsCompactParams(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    session_key: str = Field(alias="sessionKey")
    agent_id: str | None = Field(default=None, alias="agentId")
    reason: str | None = None
