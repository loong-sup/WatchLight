# 文件说明：本文件属于 契约层。
# 主要职责：实现 manifest 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Plugin manifest schema — parses watchlight.plugin.json.

Matches the JSON manifest format used by TS plugins in extensions/*.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderAuthChoice(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    provider: str
    method: str
    choice_id: str = Field(alias="choiceId")
    choice_label: str = Field(alias="choiceLabel")
    group_id: str | None = Field(default=None, alias="groupId")
    group_label: str | None = Field(default=None, alias="groupLabel")


class ModelSupport(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    model_prefixes: list[str] | None = Field(default=None, alias="modelPrefixes")


class PluginManifest(BaseModel):
    """The watchlight.plugin.json file shape."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    enabled_by_default: bool | None = Field(default=None, alias="enabledByDefault")
    providers: list[str] | None = None
    channels: list[str] | None = None
    model_support: ModelSupport | None = Field(default=None, alias="modelSupport")
    cli_backends: list[str] | None = Field(default=None, alias="cliBackends")
    provider_auth_env_vars: dict[str, list[str]] | None = Field(
        default=None, alias="providerAuthEnvVars"
    )
    channel_env_vars: dict[str, list[str]] | None = Field(default=None, alias="channelEnvVars")
    provider_auth_choices: list[ProviderAuthChoice] | None = Field(
        default=None, alias="providerAuthChoices"
    )
    contracts: dict[str, Any] | None = None
    config_schema: dict[str, Any] | None = Field(default=None, alias="configSchema")
