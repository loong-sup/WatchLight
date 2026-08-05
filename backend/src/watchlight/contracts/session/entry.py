# 文件说明：本文件属于 契约层。
# 主要职责：实现 entry 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""SessionEntry — the per-session metadata stored in sessions.json.

This is one of the most complex types (~120 optional fields).
Uses extra='allow' for forward compat with new TS fields.
"""

from pydantic import BaseModel, ConfigDict, Field


class SessionEntry(BaseModel):
    """Single session entry in the session store."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    session_id: str = Field(alias="sessionId")
    updated_at: int = Field(alias="updatedAt")

    # Session file
    session_file: str | None = Field(default=None, alias="sessionFile")

    # Spawn/subagent
    spawned_by: str | None = Field(default=None, alias="spawnedBy")
    parent_session_key: str | None = Field(default=None, alias="parentSessionKey")
    forked_from_parent: bool | None = Field(default=None, alias="forkedFromParent")
    spawn_depth: int | None = Field(default=None, alias="spawnDepth")
    subagent_role: str | None = Field(default=None, alias="subagentRole")

    # Status
    status: str | None = None
    started_at: int | None = Field(default=None, alias="startedAt")
    ended_at: int | None = Field(default=None, alias="endedAt")
    runtime_ms: int | None = Field(default=None, alias="runtimeMs")

    # Model/provider
    model: str | None = None
    model_provider: str | None = Field(default=None, alias="modelProvider")
    model_override: str | None = Field(default=None, alias="modelOverride")
    provider_override: str | None = Field(default=None, alias="providerOverride")

    # Token usage
    input_tokens: int | None = Field(default=None, alias="inputTokens")
    output_tokens: int | None = Field(default=None, alias="outputTokens")
    total_tokens: int | None = Field(default=None, alias="totalTokens")
    estimated_cost_usd: float | None = Field(default=None, alias="estimatedCostUsd")
    cache_read: int | None = Field(default=None, alias="cacheRead")
    cache_write: int | None = Field(default=None, alias="cacheWrite")
    context_tokens: int | None = Field(default=None, alias="contextTokens")

    # Compaction
    compaction_count: int | None = Field(default=None, alias="compactionCount")

    # Channel/routing
    channel: str | None = None
    group_id: str | None = Field(default=None, alias="groupId")
    subject: str | None = None
    last_channel: str | None = Field(default=None, alias="lastChannel")
    last_to: str | None = Field(default=None, alias="lastTo")
    last_account_id: str | None = Field(default=None, alias="lastAccountId")
    last_thread_id: str | int | None = Field(default=None, alias="lastThreadId")

    # Display
    label: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")

    # Queue
    queue_mode: str | None = Field(default=None, alias="queueMode")
    queue_debounce_ms: int | None = Field(default=None, alias="queueDebounceMs")

    # Session settings
    chat_type: str | None = Field(default=None, alias="chatType")
    thinking_level: str | None = Field(default=None, alias="thinkingLevel")
    fast_mode: bool | None = Field(default=None, alias="fastMode")
    send_policy: str | None = Field(default=None, alias="sendPolicy")
    group_activation: str | None = Field(default=None, alias="groupActivation")
