# 文件说明：本文件属于 契约层。
# 主要职责：实现 types Watchlight 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Top-level WatchlightConfig — the canonical config file shape.

All fields are Optional because the config file can be partial.
Uses extra="allow" to forward-compat with unknown TS-side fields.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from watchlight.contracts.config.types_agents import AgentsConfig
from watchlight.contracts.config.types_auth import AuthConfig
from watchlight.contracts.config.types_base import ConsoleStyle, LogLevel, UpdateChannel
from watchlight.contracts.config.types_channels import ChannelsConfig
from watchlight.contracts.config.types_cron import CronConfig
from watchlight.contracts.config.types_gateway import GatewayConfig
from watchlight.contracts.config.types_hooks import HooksConfig
from watchlight.contracts.config.types_memory import MemoryConfig
from watchlight.contracts.config.types_plugins import PluginsConfig
from watchlight.contracts.config.types_sessions import SessionConfig
from watchlight.contracts.config.types_tools import ToolsConfig


class MetaConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    last_touched_version: str | None = Field(default=None, alias="lastTouchedVersion")
    last_touched_at: str | int | None = Field(default=None, alias="lastTouchedAt")


class EnvConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    shell_env: dict[str, Any] | None = Field(default=None, alias="shellEnv")
    vars: dict[str, str] | None = None


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    level: LogLevel | None = None
    file: str | None = None
    max_file_bytes: int | None = Field(default=None, alias="maxFileBytes")
    console_level: LogLevel | None = Field(default=None, alias="consoleLevel")
    console_style: ConsoleStyle | None = Field(default=None, alias="consoleStyle")
    redact_sensitive: str | None = Field(default=None, alias="redactSensitive")


class UpdateConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    channel: UpdateChannel | None = None
    check_on_start: bool | None = Field(default=None, alias="checkOnStart")
    auto: dict[str, Any] | None = None


class McpServerConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str | int | bool] | None = None
    cwd: str | None = None
    url: str | None = None
    headers: dict[str, str | int | bool] | None = None


class McpConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    servers: dict[str, McpServerConfig] | None = None


class WatchshedConfig(BaseModel):
    """Configuration for the personal intelligence tracking MVP."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
    enabled: bool = True
    db_path: str = Field(default=".watchlight-state/watchlight-mvp.db", alias="dbPath")
    blob_root: str = Field(default=".watchlight-state/blobs", alias="blobRoot")
    scheduler_tick_seconds: int = Field(default=30, alias="schedulerTickSeconds", ge=1)
    max_tasks_per_user: int = Field(default=20, alias="maxTasksPerUser", ge=1)
    max_concurrent_executions: int = Field(
        default=4, alias="maxConcurrentExecutions", ge=1
    )
    max_concurrent_fetches: int = Field(default=4, alias="maxConcurrentFetches", ge=1)
    max_fetch_seconds: int = Field(default=30, alias="maxFetchSeconds", ge=1)


class WatchlightConfig(BaseModel):
    """Top-level config file model. Matches ~/.watchlight/watchlight.json.

    Uses extra='allow' so unknown TS-side fields don't break loading.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    schema_: str | None = Field(default=None, alias="$schema")
    meta: MetaConfig | None = None
    env: EnvConfig | None = None
    logging: LoggingConfig | None = None
    update: UpdateConfig | None = None
    gateway: GatewayConfig | None = None
    agents: AgentsConfig | None = None
    auth: AuthConfig | None = None
    session: SessionConfig | None = None
    channels: ChannelsConfig | None = None
    plugins: PluginsConfig | None = None
    tools: ToolsConfig | None = None
    hooks: HooksConfig | None = None
    memory: MemoryConfig | None = None
    cron: CronConfig | None = None
    mcp: McpConfig | None = None
    watchshed: WatchshedConfig | None = None
    secrets: dict[str, Any] | None = None
    models: dict[str, Any] | None = None
    bindings: dict[str, Any] | None = None
    broadcast: dict[str, Any] | None = None
    audio: dict[str, Any] | None = None
    media: dict[str, Any] | None = None
    messages: dict[str, Any] | None = None
    commands: dict[str, Any] | None = None
    approvals: dict[str, Any] | None = None
    web: dict[str, Any] | None = None
    discovery: dict[str, Any] | None = None
    canvas_host: dict[str, Any] | None = Field(default=None, alias="canvasHost")
    talk: dict[str, Any] | None = None
    acp: dict[str, Any] | None = None
    ui: dict[str, Any] | None = None
    browser: dict[str, Any] | None = None
    cli: dict[str, Any] | None = None
    skills: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None
    wizard: dict[str, Any] | None = None
    node_host: dict[str, Any] | None = Field(default=None, alias="nodeHost")
