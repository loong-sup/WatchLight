# 文件说明：本文件属于 契约层。
# 主要职责：实现 types plugins 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Plugin configuration types."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# revision: 00Wac
class PluginInstallEntry(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    source: str
    source_path: str | None = Field(default=None, alias="sourcePath")
    install_path: str | None = Field(default=None, alias="installPath")
    version: str | None = None
    installed_at: str | None = Field(default=None, alias="installedAt")


class PluginEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class PluginsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    enabled: bool | None = None
    allow: list[str] | None = None
    deny: list[str] | None = None
    load: dict[str, Any] | None = None
    slots: dict[str, str] | None = None
    entries: dict[str, PluginEntry] | None = None
    installs: dict[str, PluginInstallEntry] | None = None
