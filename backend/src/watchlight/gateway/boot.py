# 文件说明：本文件属于 Gateway 服务层，是 Watchlight 后端运行时的装配和调度中心。
# 主要职责：
# 1. 服务启动阶段：注册模型供应商、agent runtime、消息通道、工具注册表和会话存储。
# 2. 消息运行阶段：把飞书/WebChat 等入口消息整理成 AgentRunRequest，再交给 runtime 执行。
# 3. 事件观察阶段：把模型输出、工具调用、token 用量和错误转换成 runtime.event 推给前端。
# 4. 通道回包阶段：agent run 完成后，把最终回复交还给原始 channel，例如飞书机器人。
# 阅读主线：
# main.py -> cli/gateway.py -> server.py -> app.py -> GatewayRuntime.boot/start_channels
# -> _handle_inbound -> run_agent_for_session -> EmbeddedRuntime/tool_loop -> channel.send
# 运行影响：以下注释只用于源码阅读，不改变运行逻辑。

"""Gateway 启动编排：把模型、runtime、通道、工具和会话路由组装到一起。"""

import asyncio
import json
import os
import time
import uuid
from typing import TYPE_CHECKING, Any

from watchlight.agents.harness.builtin import BuiltinHarness
from watchlight.agents.harness.registry import HarnessRegistry
from watchlight.agents.providers.registry import ProviderRegistry
from watchlight.agents.runtime.embedded.runner import EmbeddedRuntime
from watchlight.agents.runtime.registry import RuntimeRegistry
from watchlight.agents.system_prompt.builder import DEFAULT_WATCHLIGHT_IDENTITY, build_system_prompt
from watchlight.channels.feishu.plugin import FeishuChannelPlugin
from watchlight.channels.registry import ChannelRegistry
from watchlight.channels.routing import resolve_session_key
from watchlight.channels.webchat.plugin import WebChatPlugin
from watchlight.contracts.agent.runtime import AgentEventType, AgentRunRequest
from watchlight.contracts.channel.plugin import InboundMessage, OutboundMessage
from watchlight.contracts.config.types_watchlight import WatchlightConfig
from watchlight.core.logging import get_logger
from watchlight.core.paths import resolve_state_dir
from watchlight.extensions.anthropic.provider import AnthropicProvider
from watchlight.extensions.dashscope.provider import DashScopeProvider
from watchlight.extensions.deepseek.provider import DeepSeekProvider
from watchlight.extensions.openai.provider import OpenAIProvider
from watchlight.gateway.websocket.broadcast import broadcast_event
from watchlight.gateway.websocket.frames import make_event
from watchlight.sessions.compaction import CompactionStore
from watchlight.sessions.last_route import build_last_route_patch
from watchlight.sessions.lifecycle import end_run, start_run
from watchlight.sessions.store import SessionStore
from watchlight.sessions.transcript import TranscriptManager
from watchlight.tools.factory import create_default_tool_registry
from watchlight.tools.policy import ToolPolicy

if TYPE_CHECKING:
    from watchlight.gateway.boot_watchshed import WatchlightServices

log = get_logger("gateway.boot")

RUNTIME_EVENT = "runtime.event"
SECRET_KEY_PARTS = ("secret", "token", "key", "authorization", "password")
MAX_TRACE_TEXT_CHARS = 6000
MAX_TRACE_LIST_ITEMS = 80


def _truncate_trace_text(value: str, max_chars: int = MAX_TRACE_TEXT_CHARS) -> str:
    # 前端运行工作台会展示模型输出、工具结果和 messages 快照。
    # 如果某个字段特别长，直接广播会让浏览器卡顿，也会让调试信息难以阅读。
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n...[truncated, {len(value)} total chars]"


def _redact_trace_value(value: Any, key: str = "") -> Any:
    # runtime 事件会直接展示在前端工作台，写入前先脱敏并截断，避免泄露密钥或撑爆 UI。
    # 这个函数递归处理 dict/list，因此 messages、tool params、tool result 都能统一经过脱敏。
    if key and any(part in key.lower() for part in SECRET_KEY_PARTS):
        return "[redacted]"
    if isinstance(value, str):
        return _truncate_trace_text(value)
    if isinstance(value, dict):
        return {
            str(item_key): _redact_trace_value(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        items = [_redact_trace_value(item) for item in value[:MAX_TRACE_LIST_ITEMS]]
        if len(value) > MAX_TRACE_LIST_ITEMS:
            items.append(f"...[{len(value) - MAX_TRACE_LIST_ITEMS} more items]")
        return items
    return value


def _message_snapshot(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # messages 是模型上下文的核心调试信息；展示前必须先做脱敏和截断。
    return [_redact_trace_value(message) for message in messages]


class AgentRunResult:
    """一次 agent 运行的汇总结果，供飞书入站消息和本地 sessions.send 共用。"""

    def __init__(self) -> None:
        # run_id 用于把同一次模型运行里的事件、回复和日志串起来。
        self.run_id: str = ""
        # texts 保存模型流式输出的文本片段；最终回复会把它们拼接起来。
        self.texts: list[str] = []
        # token 用量由 runtime 的 USAGE 事件累加，最后写回 session 统计。
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        # error 为 None 表示本次运行成功；非空时 Gateway 会把 session 标记为 failed。
        self.error: str | None = None
        # 某些工具会给出更适合直接发给用户的回复，例如“文档已创建 + URL”。
        # 一旦设置 preferred_response，最终聊天回复会优先使用它，而不是模型草稿正文。
        self.preferred_response: str | None = None


def _extract_tool_reply_text(tool_result: Any) -> str:
    # 部分工具会返回更适合直接发给用户的 reply_text，例如飞书文档工具返回文档链接。
    # 这里故意只识别 JSON dict 中的 reply_text，避免误把普通工具输出当成最终回复。
    if not isinstance(tool_result, str) or not tool_result:
        return ""
    try:
        payload = json.loads(tool_result)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    reply_text = payload.get("reply_text")
    return reply_text.strip() if isinstance(reply_text, str) else ""


def _tool_prompt_instructions(tool_registry: Any, profile: str) -> list[str]:
    # 工具使用规则由工具自己声明；Gateway 只按当前 profile 汇总“被允许的工具”规则。
    # profile 的作用是约束入口能力：飞书这类远程消息入口使用 messaging，本地入口可用 full。
    policy = ToolPolicy(profile=profile)
    instructions: list[str] = []
    for tool in tool_registry.list_all():
        if policy.is_allowed(tool.name) and tool.prompt_instructions:
            instructions.append(f"{tool.name}:\n{tool.prompt_instructions}")
    return instructions


def _infer_provider_from_model(model: str) -> str | None:
    # 配置里有时只写模型名，不写 provider；这里用常见模型前缀做轻量推断。
    # 推断结果必须后续再和已注册 provider 对齐，不能凭模型名直接假设 key 可用。
    normalized = model.lower()
    if normalized.startswith("claude"):
        return "anthropic"
    if normalized.startswith(("gpt", "o")):
        return "openai"
    if normalized.startswith("deepseek"):
        return "deepseek"
    if normalized.startswith(("qwen", "kimi", "glm")):
        return "dashscope"
    return None


def _split_configured_model(model: str) -> tuple[str | None, str]:
    # 支持两种配置写法：
    # - "qwen3.6-max-preview"：只指定模型，由 _infer_provider_from_model 推断 provider。
    # - "dashscope:qwen3.6-max-preview"：显式指定 provider 和模型。
    if ":" not in model:
        return None, model
    provider, model_id = model.split(":", 1)
    return provider or None, model_id


class GatewayRuntime:
    """Gateway 运行时容器，持有 provider、channel、tool、session 等核心组件。"""

    def __init__(self, config: WatchlightConfig) -> None:
        self.config = config

        # Registry 是 GatewayRuntime 的“能力目录”。
        # 服务启动时先把 provider/runtime/channel/tool 注册进去；
        # 真正处理消息时再从这些 registry 中取出对应能力执行。
        self.provider_registry = ProviderRegistry()
        self.runtime_registry = RuntimeRegistry()
        self.harness_registry = HarnessRegistry()
        self.channel_registry = ChannelRegistry()
        self.tool_registry = create_default_tool_registry()

        # 这里先放兜底默认值；等 provider 注册完成后，会根据配置模型和可用 API Key 重算。
        self.default_provider = "dashscope"
        self.default_model = "qwen-max"

        # state_dir 是本地状态目录，保存 session 元数据、transcript、压缩记录等。
        # 这些对象共同保证同一个飞书用户下次发消息时还能接上之前上下文。
        self._state_dir = resolve_state_dir()
        self.session_store = SessionStore(self._state_dir)
        self.transcript_manager = TranscriptManager(self._state_dir)
        self.compaction_store = CompactionStore(self._state_dir)

        # _event_clients 由 gateway/app.py 在 FastAPI lifespan 中注入。
        # 它不是业务执行必需项，但前端运行工作台依赖它实时展示执行链路。
        self._event_clients: dict[str, Any] | None = None
        self._event_seq = 0
        self.watchlight_mvp: WatchlightServices | None = None

    def attach_event_clients(self, clients: dict[str, Any]) -> None:
        # FastAPI WebSocket 层管理连接池，GatewayRuntime 只保存引用并在运行时广播事件。
        self._event_clients = clients

    async def _emit_runtime_event(
        self,
        event_type: str,
        *,
        layer: str,
        session_key: str,
        run_id: str | None = None,
        status: str = "active",
        title: str = "",
        detail: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        # runtime.event 是“给人看的运行轨迹”，不参与 agent 决策。
        # 任何一个阶段想让前端看到进度，都通过这里统一发事件。
        clients = self._event_clients
        if not clients:
            return
        self._event_seq += 1
        # payload 字段尽量保持稳定，前端可以按 layer/status/runId/sessionKey 做聚合展示。
        payload = {
            "type": event_type,
            "layer": layer,
            "status": status,
            "title": title or event_type,
            "detail": detail,
            "sessionKey": session_key,
            "runId": run_id,
            "ts": int(time.time() * 1000),
            "data": _redact_trace_value(data or {}),
        }
        await broadcast_event(clients, make_event(RUNTIME_EVENT, payload, seq=self._event_seq))

    def boot(self) -> None:
        # boot 只负责“装配能力”，不处理某条具体用户消息。
        # app.py 在服务启动时调用它，让 GatewayRuntime 进入可接收消息的状态。
        self._load_sessions()
        self._register_providers()
        self._register_runtimes()
        self._register_channels()
        log.info(
            "gateway_booted",
            providers=self.provider_registry.list_ids(),
            runtimes=self.runtime_registry.list(),
            channels=self.channel_registry.list_ids(),
            tools=self.tool_registry.names(),
            default_provider=self.default_provider,
            default_model=self.default_model,
        )

    def _load_sessions(self) -> None:
        # session_store 保存 session 元数据，例如状态、token 用量、最近通道路由等。
        # transcript 的正文内容由 TranscriptManager 管理，这里只恢复 session 索引。
        try:
            self.session_store.load()
            log.info("sessions_loaded", count=self.session_store.count)
        except Exception as e:
            log.warning("sessions_load_failed", error=str(e))

    def _register_providers(self) -> None:
        # provider 注册是按环境变量自动启用的：有 key 才注册对应供应商。
        # DeepSeek API key 获取和provider注册逻辑
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            self.provider_registry.register(DeepSeekProvider(deepseek_key))
            log.info("provider_registered", provider="deepseek")
        # 这样同一份配置可以在不同机器上按可用 key 自动裁剪能力。
        dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if dashscope_key:
            self.provider_registry.register(DashScopeProvider(dashscope_key))
            log.info("provider_registered", provider="dashscope")
        if openai_key:
            self.provider_registry.register(OpenAIProvider(openai_key))
            log.info("provider_registered", provider="openai")
        if anthropic_key:
            self.provider_registry.register(AnthropicProvider(anthropic_key))
            log.info("provider_registered", provider="anthropic")
        if not self.provider_registry.list_ids():
            log.warning("no_provider_api_keys_found")

        # 下面这段用于确定默认 provider/model。
        # 优先级：
        # 1. 配置里明确写 provider，且该 provider 已注册。
        # 2. 配置模型名能推断 provider，且该 provider 已注册。
        # 3. 有任意已注册 provider 时，选一个稳定的字母序兜底。
        # 4. 模型名和 provider 匹配时使用配置模型，否则使用该 provider 的默认模型。
        agents_defaults = {}
        if self.config.agents and self.config.agents.defaults:
            agents_defaults = self.config.agents.defaults.model_dump(
                exclude_none=True,
                by_alias=True,
            )
        configured_model = agents_defaults.get("model")
        configured_provider = agents_defaults.get("provider") or agents_defaults.get(
            "modelProvider"
        )
        registered = set(self.provider_registry.list_ids())
        inferred_provider = None
        configured_model_id = None
        if isinstance(configured_model, str):
            # 同时支持纯模型名和 provider 前缀写法，例如 qwen3.6 或 dashscope:qwen3.6。
            model_provider, configured_model_id = _split_configured_model(configured_model)
            inferred_provider = _infer_provider_from_model(configured_model_id)
            if model_provider in registered:
                # 显式 provider 前缀比模型名前缀推断更可信。
                inferred_provider = model_provider
        if isinstance(configured_provider, str) and configured_provider in registered:
            self.default_provider = configured_provider
        elif inferred_provider in registered:
            self.default_provider = inferred_provider
        elif registered:
            self.default_provider = sorted(registered)[0]
        if configured_model_id and inferred_provider == self.default_provider:
            self.default_model = configured_model_id
        elif self.default_provider == "deepseek":
            self.default_model = "deepseek-chat"
        elif self.default_provider == "dashscope":
            self.default_model = "qwen-max"
        elif self.default_provider == "openai":
            self.default_model = "gpt-4o"
        elif self.default_provider == "anthropic":
            self.default_model = "claude-sonnet-4-6"

    def _register_runtimes(self) -> None:
        # EmbeddedRuntime 是当前内置 agent 执行器，负责：
        # - 组装模型 messages。
        # - 调 provider 流式接口。
        # - 识别 tool_call。
        # - 调 tool_loop 执行工具并把结果回填给模型。
        embedded = EmbeddedRuntime(
            provider_registry=self.provider_registry,
            tool_registry=self.tool_registry,
            session_store=self.session_store,
            transcript_manager=self.transcript_manager,
            compaction_store=self.compaction_store,
        )
        self.runtime_registry.register(embedded, default=True)
        # Harness 是更高层的 agent 执行抽象；目前用内置 harness 包一层 embedded runtime。
        harness = BuiltinHarness(embedded)
        self.harness_registry.register(harness)

    def _register_channels(self) -> None:
        # Channel 是外部消息入口/出口的抽象。
        # WebChatPlugin 处理本地前端聊天；FeishuChannelPlugin 处理飞书机器人消息。
        self.channel_registry.register(WebChatPlugin())
        # 飞书插件收到消息后不会自己跑模型，而是通过 on_inbound 回调交给 GatewayRuntime。
        feishu = FeishuChannelPlugin(on_inbound=self._handle_inbound)
        self.channel_registry.register(feishu)

    # ── 共享 Agent 执行逻辑 ───────────────────────────────────────

    async def run_agent_for_session(
        self,
        session_key: str,
        user_message: str,
        channel: str | None = None,
        sender_id: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        system_prompt: str = DEFAULT_WATCHLIGHT_IDENTITY,
        on_text_delta: Any = None,
    ) -> AgentRunResult:
        """为指定 session 执行一次 agent run。

        这条路径同时服务两种入口：
        - 飞书等 channel 入站消息。
        - 前端本地 WebChat 的 sessions.send。

        这也是 Gateway 层最核心的“消息到模型”主线：
        1. 根据 session_key 找到会话。
        2. 读取历史 transcript 并写入当前 user 消息。
        3. 根据入口选择工具策略和 system prompt。
        4. 创建 AgentRunRequest 并交给 runtime。
        5. 收集模型输出、工具事件、token 用量和最终回复。
        6. 写 assistant transcript，并更新 session 状态。

        返回值会收集最终文本、token 用量、错误信息，以及工具指定的 preferred reply。
        """
        result = AgentRunResult()
        # run_id 是一次运行的短链路 id，用于把 runtime.event、日志和最终回复对应起来。
        run_id = str(uuid.uuid4())[:8] # 生成一个 8位随机字符串 ，用于唯一标识一次 Agent 运行。
        result.run_id = run_id

        if channel and channel != "feishu":
            # 非飞书入口在这里补发“收到消息”事件；飞书入口会提前发，方便回复阶段复用同一个 run id。
            await self._emit_runtime_event(
                "runtime.channel.inbound",
                layer="channel",
                session_key=session_key,
                run_id=run_id,
                title="Inbound message",
                detail=user_message,
                data={
                    "channel": channel,
                    "senderId": sender_id,
                    "conversationId": conversation_id,
                    "message": user_message,
                },
            )

        # 会话按 sender/conversation 分开建档，避免不同用户或不同群聊共享 transcript。
        # session_key 通常来自 resolve_session_key，例如 feishu:<conversation>:<sender>。
        entry = self.session_store.get(session_key)
        if entry is None:
            # 第一次收到这个用户/会话的消息时创建 session，后续 transcript 会挂在该 session_id 下。
            entry = self.session_store.create(session_key, channel=channel)

        # 先把 session 标记为运行中，这样前端和后续诊断能看到当前任务状态。
        run_patch = start_run(session_key, {})
        self.session_store.update(session_key, run_patch)
        self.session_store.save()
        run_start_ms = int(time.time() * 1000)

        # 只把模型能理解的 role 放回上下文；工具轨迹单独通过 runtime event 展示给前端。
        # 这里没有把历史里的 tool 消息重新塞回模型，是为了避免旧工具结果污染下一轮普通对话。
        history: list[dict[str, Any]] = []
        if entry.session_id:
            raw = self.transcript_manager.read_raw(entry.session_id)
            history = [h for h in raw if h.get("role") in ("user", "assistant", "system")]
        await self._emit_runtime_event(
            "runtime.session.loaded",
            layer="session",
            session_key=session_key,
            run_id=run_id,
            title="Session loaded",
            detail=f"{len(history)} 条历史消息",
            data={
                "sessionId": entry.session_id,
                "historyCount": len(history),
                "sessionKey": session_key,
            },
        )

        # 用户原始输入必须先落 transcript，后续同一 session 才能延续上下文。
        # 即使后面模型调用失败，这条用户消息也应该保留下来，方便排查失败现场。
        user_line: dict[str, Any] = {
            "role": "user",
            "content": user_message,
            "ts": int(time.time() * 1000),
        }
        if sender_id:
            user_line["senderId"] = sender_id
        if user_id:
            user_line["userId"] = user_id
        self.transcript_manager.append(entry.session_id, user_line)

        # runtime 是真正执行模型循环和工具调用的组件；这里拿不到就只能提前结束。
        # 正常情况下 boot() 已经注册 EmbeddedRuntime，因此这里为空通常意味着启动装配失败。
        runtime = self.runtime_registry.get()
        if runtime is None:
            result.error = "no runtime available"
            self.session_store.update(session_key, {"status": "done"})
            self.session_store.save()
            return result

        # 飞书等远程消息入口使用更保守的 messaging 工具集；本地入口可使用完整工具集。
        # 这里是安全边界之一：远程聊天入口默认不应该拥有 shell、文件写入等高风险本地能力。
        tool_profile = "messaging" if channel else "full"
        effective_system_prompt = build_system_prompt(
            identity=system_prompt,
            tool_instructions=_tool_prompt_instructions(self.tool_registry, tool_profile),
        )
        # initial_messages 是本次发给 runtime 的完整模型上下文快照。
        # 前端工作台展示它，可以帮助确认 system、history、user 是否按预期组合。
        initial_messages = [
            {"role": "system", "content": effective_system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]
        # current_messages 是“运行中视角”的上下文副本，会随着模型 delta 和工具结果持续追加。
        # 它不直接写回 transcript，只用于 runtime.event 观察完整执行链路。
        current_messages = list(initial_messages)
        current_assistant_index: int | None = None

        await self._emit_runtime_event(
            "runtime.run.started",
            layer="gateway",
            session_key=session_key,
            run_id=run_id,
            title="Run started",
            detail=f"{self.default_provider}:{self.default_model}",
            data={
                "channel": channel or "webchat",
                "senderId": sender_id,
                "conversationId": conversation_id,
                "provider": self.default_provider,
                "model": self.default_model,
            },
        )
        await self._emit_runtime_event(
            "runtime.messages.initial",
            layer="runtime",
            session_key=session_key,
            run_id=run_id,
            title="Initial messages",
            detail=f"{len(initial_messages)} messages prepared for runtime",
            data={"messages": _message_snapshot(initial_messages)},
        )
        request = AgentRunRequest(
            run_id=run_id,
            session_key=session_key,
            provider_id=self.default_provider,
            model_id=self.default_model,
            system_prompt=effective_system_prompt,
            user_message=user_message,
            history=history,
            metadata={
                "channel": channel,
                "senderId": sender_id,
                "conversationId": conversation_id,
                "userId": user_id,
                "toolProfile": tool_profile,
            },
        )

        # 下面把 runtime 的细粒度事件翻译成前端可展示的运行轨迹。
        # abort_signal 预留给未来取消运行；当前这里创建但不会主动 set。
        abort_signal = asyncio.Event()
        try:
            async for event in runtime.run(request, abort_signal):
                if event.type == AgentEventType.TEXT_DELTA and event.text:
                    # 如果工具已经给了 preferred_response，例如飞书文档链接，
                    # 后续模型继续输出的正文就不再进入最终聊天回复，避免刷屏。
                    if result.preferred_response:
                        continue
                    if current_assistant_index is None:
                        # 第一次收到模型文本时创建一个 assistant 消息；
                        # 后续 delta 继续拼到同一条 assistant 消息上，前端看到的是同一轮流式输出。
                        current_messages.append({"role": "assistant", "content": ""})
                        current_assistant_index = len(current_messages) - 1
                    content = str(current_messages[current_assistant_index].get("content", ""))
                    current_messages[current_assistant_index]["content"] = content + event.text
                    result.texts.append(event.text)
                    await self._emit_runtime_event(
                        "runtime.model.delta",
                        layer="provider",
                        session_key=session_key,
                        run_id=run_id,
                        title="Model output",
                        detail=event.text,
                        data={
                            "text": event.text,
                            "provider": self.default_provider,
                            "model": self.default_model,
                        },
                    )
                    if on_text_delta:
                        # WebChat 等本地调用方可以传入回调，把模型 delta 直接流式推给前端。
                        await on_text_delta(event.text)
                elif event.type == AgentEventType.USAGE:
                    # token 用量可能分多次上报，因此这里累加而不是覆盖。
                    result.input_tokens += event.input_tokens
                    result.output_tokens += event.output_tokens
                    await self._emit_runtime_event(
                        "runtime.usage",
                        layer="runtime",
                        session_key=session_key,
                        run_id=run_id,
                        title="Usage",
                        detail=f"{event.input_tokens + event.output_tokens} tokens",
                        data={
                            "inputTokens": event.input_tokens,
                            "outputTokens": event.output_tokens,
                        },
                    )
                elif event.type == AgentEventType.TOOL_CALL_START:
                    # 模型提出 tool_call 时，先把“助手请求调用工具”的意图放进 current_messages。
                    # 这能帮助前端还原：模型不是直接得到工具结果，而是先发起调用。
                    current_messages.append(
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_call": {
                                "name": event.tool_name,
                                "params": event.tool_params,
                            },
                        }
                    )
                    current_assistant_index = None
                    await self._emit_runtime_event(
                        "runtime.tool.started",
                        layer="tools",
                        session_key=session_key,
                        run_id=run_id,
                        title=f"Tool started: {event.tool_name}",
                        detail=str(event.tool_name or ""),
                        data={"tool": event.tool_name, "params": event.tool_params or {}},
                    )
                    log.info(
                        "agent_tool_call_start",
                        session_key=session_key,
                        tool=event.tool_name,
                    )
                elif event.type == AgentEventType.TOOL_CALL_RESULT:
                    # 工具执行完成后，检查它是否提供了更适合最终回复用户的文本。
                    # 典型例子：feishu_docs_create_with_content 返回 reply_text，只包含文档链接。
                    reply_text = _extract_tool_reply_text(event.tool_result)
                    if reply_text:
                        # 文档创建这类工具更适合最终只回链接，因此用 reply_text 覆盖模型草稿。
                        result.preferred_response = reply_text
                    # role=tool 消息只进入 current_messages 观察快照；
                    # runtime 内部是否继续把工具结果喂给模型，由 EmbeddedRuntime/tool_loop 负责。
                    current_messages.append(
                        {
                            "role": "tool",
                            "name": event.tool_name,
                            "content": str(event.tool_result or ""),
                        }
                    )
                    await self._emit_runtime_event(
                        "runtime.tool.finished",
                        layer="tools",
                        session_key=session_key,
                        run_id=run_id,
                        status="done",
                        title=f"Tool finished: {event.tool_name}",
                        detail=str(event.tool_name or ""),
                        data={
                            "tool": event.tool_name,
                            "result": event.tool_result,
                            "messages": _message_snapshot(current_messages),
                        },
                    )
                    log.info(
                        "agent_tool_call_result",
                        session_key=session_key,
                        tool=event.tool_name,
                        result=str(event.tool_result or "")[:200],
                    )
                elif event.type == AgentEventType.ERROR:
                    # runtime 已经把错误转成 AgentEventType.ERROR 时，在这里统一记录并广播失败事件。
                    result.error = event.error
                    await self._emit_runtime_event(
                        "runtime.run.failed",
                        layer="runtime",
                        session_key=session_key,
                        run_id=run_id,
                        status="failed",
                        title="Run failed",
                        detail=event.error or "",
                    )
                    log.error("agent_error", error=event.error, session_key=session_key)
        except Exception as e:
            # 捕获 runtime.run 迭代过程中未被转换成 AgentEventType.ERROR 的异常。
            # 这样 Gateway 不会因为某一次模型或工具异常直接崩掉整个服务。
            result.error = str(e)
            await self._emit_runtime_event(
                "runtime.run.failed",
                layer="runtime",
                session_key=session_key,
                run_id=run_id,
                status="failed",
                title="Run failed",
                detail=str(e),
            )
            log.error("agent_run_failed", error=str(e), session_key=session_key)

        if result.preferred_response:
            # preferred_response 是面向最终用户的回复文本；一旦存在，就覆盖模型 delta 片段。
            # 例如创建文档后，聊天里只发链接，文档正文留在飞书文档中。
            result.texts = [result.preferred_response]

        # transcript 只保存最终助手回复；完整工具过程已经通过 runtime event 暴露给前端。
        response_text = "".join(result.texts) or "[No response]"
        if result.preferred_response:
            # current_messages 是给前端看的运行快照；这里补上一条最终 assistant 回复，
            # 让工具结果到最终回复之间的关系更清楚。
            current_messages.append(
                {
                    "role": "assistant",
                    "content": response_text,
                }
            )
        self.transcript_manager.append(
            entry.session_id,
            {
                "role": "assistant",
                "content": response_text,
                "ts": int(time.time() * 1000),
            },
        )

        # 运行结束后统一更新 token、模型、耗时和状态，供列表页和诊断接口读取。
        # end_run 会生成 session store patch，避免这里直接散落修改多个字段。
        status = "failed" if result.error else "done"
        runtime_ms = int(time.time() * 1000) - run_start_ms
        end_patch = end_run(
            session_key,
            status=status,
            input_tokens=(entry.input_tokens or 0) + result.input_tokens,
            output_tokens=(entry.output_tokens or 0) + result.output_tokens,
            model=self.default_model,
            model_provider=self.default_provider,
            channel=channel,
            runtime_ms=runtime_ms,
        )
        self.session_store.update(session_key, end_patch)
        self.session_store.save()

        await self._emit_runtime_event(
            "runtime.run.completed",
            layer="runtime",
            session_key=session_key,
            run_id=run_id,
            status=status,
            title="Run completed" if status == "done" else "Run failed",
            detail=response_text[:300],
            data={
                "responseText": response_text,
                "inputTokens": result.input_tokens,
                "outputTokens": result.output_tokens,
                "runtimeMs": runtime_ms,
                "messages": _message_snapshot(current_messages),
            },
        )

        log.info(
            "agent_response",
            session_key=session_key,
            tokens=result.input_tokens + result.output_tokens,
            text=response_text[:80],
        )
        return result

    def record_session_exchange(
        self,
        session_key: str,
        user_message: str,
        assistant_message: str,
        *,
        channel: str | None = None,
        sender_id: str | None = None,
        user_id: str | None = None,
        route_patch: dict[str, Any] | None = None,
    ) -> None:
        """Persist a deterministic chat reply that bypassed the model runtime."""
        entry = self.session_store.get(session_key)
        if entry is None:
            entry = self.session_store.create(session_key, channel=channel)
        timestamp = int(time.time() * 1000)
        user_line: dict[str, Any] = {
            "role": "user",
            "content": user_message,
            "ts": timestamp,
        }
        if sender_id:
            user_line["senderId"] = sender_id
        if user_id:
            user_line["userId"] = user_id
        self.transcript_manager.append(entry.session_id, user_line)
        self.transcript_manager.append(
            entry.session_id,
            {"role": "assistant", "content": assistant_message, "ts": timestamp},
        )
        session_patch: dict[str, Any] = dict(route_patch or {})
        if channel:
            session_patch["channel"] = channel
        self.session_store.update(session_key, session_patch)
        self.session_store.save()

    # ── 通道入站消息处理 ─────────────────────────────────────────

    async def _handle_inbound(self, message: InboundMessage) -> None:
        """处理任意通道标准化后的入站消息，并在完成后回写到原通道。

        注意这里接收的已经不是飞书原始事件，而是 channel plugin 转换后的 InboundMessage。
        因此 Gateway 后续逻辑可以统一处理 WebChat、飞书或未来其他通道。
        """
        session_key = resolve_session_key(message)
        route_patch = build_last_route_patch(message)
        user_id: str | None = None
        if self.watchlight_mvp is not None:
            raw = message.raw or {}
            display_name = raw.get("sender_name") or raw.get("senderName")
            identity = self.watchlight_mvp.identity.resolve_or_register(
                message.channel,
                message.sender_id,
                display_name=str(display_name) if display_name else None,
            )
            if identity.user_id is None:
                status_text = "正在绑定" if identity.status == "pending" else "已解绑"
                await self._send_channel_text(
                    message,
                    f"当前渠道身份{status_text}，暂时不能访问原账号数据，请完成身份绑定。",
                )
                return
            user_id = identity.user_id
            message.raw = {**(message.raw or {}), "user_id": user_id}
            task_flow = self.watchlight_mvp.nl_tasks
            if hasattr(task_flow, "handle_async"):
                nl_reply = await task_flow.handle_async(
                    user_id,
                    message.channel,
                    message.text or "",
                    conversation_id=session_key,
                )
            else:
                nl_reply = task_flow.handle(
                    user_id,
                    message.channel,
                    message.text or "",
                    conversation_id=session_key,
                )
            if nl_reply is not None:
                self.record_session_exchange(
                    session_key,
                    message.text or "",
                    nl_reply,
                    channel=message.channel,
                    sender_id=message.sender_id,
                    user_id=user_id,
                    route_patch=route_patch,
                )
                await self._send_channel_text(message, nl_reply)
                return

        # session_key 是通道消息进入 session 系统的路由键。
        # 它决定本条消息会读写哪份 transcript，也决定最终运行事件归属到哪个会话。
        log.info(
            "inbound_message",
            channel=message.channel,
            sender=message.sender_id,
            session_key=session_key,
            text=(message.text or "")[:100],
        )
        # 飞书入口会先在这里广播入站事件；run_agent_for_session 会复用同一个 session_key 继续广播。
        await self._emit_runtime_event(
            "runtime.channel.inbound",
            layer="channel",
            session_key=session_key,
            title="Inbound message",
            detail=message.text or "",
            data={
                "channel": message.channel,
                "chatType": message.chat_type,
                "senderId": message.sender_id,
                "conversationId": message.conversation_id,
                "message": message.text or "",
            },
        )

        # 记录最近通道路由，后续会话操作才能知道应回到哪个 channel/conversation。
        # 例如某些本地 session 操作需要知道“上一次这条会话来自飞书哪个 conversation”。
        self.session_store.update(session_key, route_patch)

        # 进入统一 agent 主线。这里不关心飞书细节，只传入标准字段：
        # user_message、channel、sender_id、conversation_id。
        result = await self.run_agent_for_session(
            session_key=session_key,
            user_message=message.text or "",
            channel=message.channel,
            sender_id=message.sender_id,
            conversation_id=message.conversation_id,
            user_id=user_id,
        )

        response_text = "".join(result.texts) or "[No response]"

        # 具体回复方式交给 channel plugin 处理，例如飞书会根据 replyToId 选择回复或发新消息。
        channel_plugin = self.channel_registry.get(message.channel)
        if channel_plugin:
            # reply_to 对飞书很重要：有 message_id 时可以回复原消息，群聊里上下文更清楚。
            reply_to = message.raw.get("message_id") if message.raw else None
            outbound = OutboundMessage(text=response_text, replyToId=reply_to)
            try:
                # account_id 支持一个 channel 下多个账号；没有显式账号时使用 default。
                account_id = message.raw.get("account_id", "default") if message.raw else "default"
                await channel_plugin.send(account_id, message.conversation_id, outbound)
                await self._emit_runtime_event(
                    "runtime.channel.reply_sent",
                    layer="reply",
                    session_key=session_key,
                    run_id=result.run_id,
                    status="done",
                    title="Reply sent",
                    detail=response_text[:300],
                    data={
                        "channel": message.channel,
                        "conversationId": message.conversation_id,
                        "replyTo": reply_to,
                        "text": response_text,
                    },
                )
                log.info("reply_sent", channel=message.channel)
            except Exception as e:
                await self._emit_runtime_event(
                    "runtime.channel.reply_failed",
                    layer="reply",
                    session_key=session_key,
                    run_id=result.run_id,
                    status="failed",
                    title="Reply failed",
                    detail=str(e),
                    data={"channel": message.channel},
                )
                log.error("reply_failed", error=str(e), channel=message.channel)

    async def _send_channel_text(self, message: InboundMessage, text: str) -> None:
        channel_plugin = self.channel_registry.get(message.channel)
        if channel_plugin is None:
            return
        raw = message.raw or {}
        await channel_plugin.send(
            str(raw.get("account_id", message.account_id or "default")),
            message.conversation_id,
            OutboundMessage(text=text, replyToId=raw.get("message_id")),
        )

    async def handle_feishu_sidecar_event(
        self, account_id: str, event_data: dict[str, Any]
    ) -> bool:
        """处理内部接口或未来 sidecar 转发过来的飞书事件。"""
        # 这个方法是飞书事件的备用入口：
        # - 当前可用于内部 HTTP 回调或本地测试。
        # - 未来如果改成 Node/TypeScript 官方 SDK sidecar，也可以由 sidecar 转发事件到这里。
        channel_plugin = self.channel_registry.get("feishu")
        handle_event = getattr(channel_plugin, "handle_event", None)
        if not callable(handle_event):
            return False
        return bool(await handle_event(account_id, event_data))

    # ── 通道生命周期 ─────────────────────────────────────────────

    async def start_channels(self) -> None:
        # start_channels 在 FastAPI lifespan 启动阶段调用。
        # 它会把配置中启用的通道真正启动起来，例如飞书长连接开始等待事件。
        config_dict = self.config.model_dump(exclude_none=True, by_alias=True)
        for channel_id in self.channel_registry.list_ids():
            channel = self.channel_registry.get(channel_id)
            if channel is None:
                continue
            channels_cfg = config_dict.get("channels", {})
            channel_cfg = channels_cfg.get(channel_id, {})
            if channel_cfg.get("enabled") is False:
                # 配置明确 disabled 的通道不启动，但仍允许它保留在 registry 中。
                continue
            for account_id in channel.list_account_ids(config_dict):
                try:
                    # 一个通道可以配置多个账号；逐个启动，单个账号失败不阻塞其他账号。
                    await channel.start(account_id, config_dict)
                    log.info("channel_started", channel=channel_id, account=account_id)
                except Exception as e:
                    log.error(
                        "channel_start_failed",
                        channel=channel_id,
                        account=account_id,
                        error=str(e),
                    )

    async def stop_channels(self) -> None:
        # stop_channels 在服务关闭时调用，尽量让每个通道释放后台连接。
        # 关闭失败只记录日志，不向外抛出，避免影响其他通道的清理流程。
        for channel_id in self.channel_registry.list_ids():
            channel = self.channel_registry.get(channel_id)
            if channel:
                try:
                    for account_id in channel.list_account_ids({}):
                        await channel.stop(account_id)
                except Exception as e:
                    log.error("channel_stop_failed", channel=channel_id, error=str(e))
