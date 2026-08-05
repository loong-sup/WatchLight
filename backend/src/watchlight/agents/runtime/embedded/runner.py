# 文件说明：本文件属于 Agent 模型运行层，是 Watchlight 内置 agent runtime 的核心执行器。
# 主要职责：
# 1. 接收 Gateway 组装好的 AgentRunRequest。
# 2. 选择对应模型 provider，并把 messages/system/tools 交给模型。
# 3. 解析模型流式输出，把文本、工具调用、token 用量转换成 AgentEvent。
# 4. 当模型提出 tool_call 时，调用 tool_loop 执行工具，并把工具结果追加回 messages。
# 5. 在上下文过长时执行截断或压缩，避免模型调用超过上下文限制。
# 6. 支持运行中的 abort，以及会话级 compaction 写回。
# 阅读主线：
# GatewayRuntime.run_agent_for_session -> EmbeddedRuntime.run -> run_with_retry
# -> _single_attempt -> provider.create_stream -> run_tool_loop -> AgentEvent
# 运行影响：以下注释只用于源码阅读，不改变运行逻辑。

"""EmbeddedRuntime — complete agent execution engine with retry loop, tool loop, compaction.

Matches TS pi-embedded-runner run.ts execution flow.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from watchlight.agents.runtime.embedded.compaction import compact_messages, should_compact
from watchlight.agents.runtime.embedded.overflow import (
    check_overflow,
    truncate_oversized_tool_results,
)
from watchlight.agents.runtime.embedded.retry_loop import run_with_retry
from watchlight.agents.runtime.embedded.tool_loop import run_tool_loop
from watchlight.contracts.agent.runtime import (
    AgentEvent,
    AgentEventType,
    AgentRunRequest,
    CompactionResult,
)
from watchlight.core.logging import get_logger
from watchlight.tools.policy import ToolPolicy
from watchlight.tools.types import ToolContext

log = get_logger("agent.embedded")

MAX_TOOL_TURNS = 25


class EmbeddedRuntime:
    """Built-in agent runtime — complete execution engine."""

    # runtime_id 会被 RuntimeRegistry 用来标识这个 runtime。
    # 当前项目默认使用 embedded，意思是模型调用、工具循环、压缩都在本 Python 进程里完成。
    runtime_id = "embedded"

    def __init__(
        self,
        provider_registry: Any = None,
        tool_registry: Any = None,
        session_store: Any = None,
        transcript_manager: Any = None,
        compaction_store: Any = None,
    ) -> None:
        # provider_registry：模型供应商目录，例如 dashscope/openai/anthropic。
        # _single_attempt 会根据 request.provider_id 从这里取出真正要调用的 provider。
        self._provider_registry = provider_registry
        # tool_registry：工具目录，例如 web_search、web_fetch、feishu_docs_create_with_content。
        # 模型只能看到 tool_policy 允许的工具。
        self._tool_registry = tool_registry
        # session_store/transcript_manager/compaction_store 主要服务自动压缩和会话写回。
        # 普通模型调用只需要 provider_registry 和 tool_registry 就能跑。
        self._session_store = session_store
        self._transcript_manager = transcript_manager
        self._compaction_store = compaction_store
        # 默认工具策略是 full；如果 Gateway 在 request.metadata 中传了 toolProfile，
        # _single_attempt 会按该 profile 重新创建 ToolPolicy。
        self._tool_policy = ToolPolicy()
        # _active_runs 保存 run_id -> abort_signal，用于外部调用 abort(run_id) 取消运行。
        self._active_runs: dict[str, asyncio.Event] = {}

    async def run(
        self,
        request: AgentRunRequest,
        abort_signal: asyncio.Event,
    ) -> AsyncIterator[AgentEvent]:
        """Execute agent turn with retry loop, tool loop, and compaction."""
        # 一个 run 开始时先登记 abort_signal。
        # Gateway 或未来控制接口可以通过 run_id 找到这个 signal 并 set()。
        self._active_runs[request.run_id] = abort_signal

        try:
            # run_with_retry 是外层容错框架：
            # - 真正单次尝试由 _single_attempt 完成。
            # - 如果遇到可恢复问题，可以触发 compact_fn 或 fallback_model 等机制。
            # - 当前 fallback_model/auth_rotator 传 None，说明本项目暂不做模型降级和 key 轮换。
            async for event in run_with_retry(
                run_fn=self._single_attempt,
                request=request,
                abort_signal=abort_signal,
                compact_fn=self._compact_for_session,
                fallback_model=None,
                auth_rotator=None,
            ):
                yield event
        finally:
            # 无论正常完成、异常返回还是被取消，都要清掉 active run，避免内存里残留旧 signal。
            self._active_runs.pop(request.run_id, None)

    async def _single_attempt(
        self,
        request: AgentRunRequest,
        abort_signal: asyncio.Event,
    ) -> AsyncIterator[AgentEvent]:
        """Single inference attempt with tool loop."""
        # 先根据 request.provider_id 找到模型供应商。
        # 例如飞书链路里 Gateway 会把 provider_id 设成 dashscope，model_id 为 qwen3.6-max-preview。
        provider = None
        if self._provider_registry:
            provider = self._provider_registry.get(request.provider_id)

        if provider is None:
            # 没有 provider 时走 mock 回显，便于无 API Key 的本地开发和协议联调。
            # 真实飞书运行不应该走到这里；如果走到这里，说明 provider 注册或配置有问题。
            yield AgentEvent(
                type=AgentEventType.TEXT_DELTA, text=f"[mock] Echo: {request.user_message}"
            )
            yield AgentEvent(type=AgentEventType.USAGE, input_tokens=5, output_tokens=10)
            yield AgentEvent(type=AgentEventType.COMPLETE)
            return

        # Gateway 传进来的 request.history 已经是筛选后的历史消息。
        # 这里再追加当前用户消息，形成传给 provider 的基础 messages。
        # system prompt 不放在 messages 里，而是单独通过 provider.create_stream(system=...) 传入。
        messages: list[dict[str, Any]] = list(request.history) + [
            {"role": "user", "content": request.user_message}
        ]

        # toolProfile 决定本轮允许模型看到哪些工具。
        # 飞书等远程入口通常是 messaging，本地入口可能是 full。
        profile = request.metadata.get("toolProfile")
        tool_policy = (
            ToolPolicy(profile=profile)
            if isinstance(profile, str) and profile
            else self._tool_policy
        )
        # tool_defs 是暴露给模型的工具 schema。
        # 这里只筛 allowed 工具，不在这里执行工具；真正执行在 run_tool_loop。
        tool_defs: list[dict[str, Any]] = []
        if self._tool_registry:
            tool_defs = [
                tool
                for tool in self._tool_registry.catalog()
                if tool_policy.is_allowed(str(tool.get("name", "")))
            ]
        # ToolContext 是工具执行时需要的上下文。
        # 例如飞书文档工具可能需要知道本轮来自 feishu，或者后续工具要记录 session_key。
        tool_context = ToolContext(
            session_key=request.session_key,
            channel=str(request.metadata.get("channel") or "") or None,
            sender_id=str(request.metadata.get("senderId") or "") or None,
            conversation_id=str(request.metadata.get("conversationId") or "") or None,
            user_message=request.user_message,
            user_id=str(request.metadata.get("userId") or "") or None,
        )

        total_input = 0
        total_output = 0

        # 一个 agent run 可能包含多轮“模型 -> 工具 -> 模型”循环。
        # MAX_TOOL_TURNS 是安全上限，避免模型无限调用工具导致死循环。
        for turn in range(MAX_TOOL_TURNS):
            if abort_signal.is_set():
                # abort 只产出 COMPLETE 事件并带 metadata，不再继续调用模型或工具。
                yield AgentEvent(type=AgentEventType.COMPLETE, metadata={"aborted": True})
                return

            # Pre-call context governance: truncate → compact → hard truncate
            if check_overflow(messages):
                # 每次调用模型前都先检查上下文长度。
                # 工具结果尤其容易很长，所以优先处理过大的 tool result。
                log.warning("pre_call_overflow", turn=turn, messages=len(messages))
                # Step 1: Truncate oversized tool results
                truncated = truncate_oversized_tool_results(messages)
                # Step 2: If still over, try agent-aware compaction
                if truncated == 0 and should_compact(messages):
                    # 如果没有可截断的大工具结果，并且整体历史仍然过长，就尝试总结压缩。
                    from watchlight.agents.runtime.embedded.compaction import (
                        compute_compaction_reason,
                    )

                    reason = compute_compaction_reason(messages)
                    summarize = self._build_summarize_fn()
                    if summarize:
                        # 有可用模型时，使用模型总结历史，尽量保留任务目标和关键事实。
                        await compact_messages(
                            messages,
                            summarize_fn=summarize,
                            reason=reason,
                        )
                    else:
                        # 如果没有可用于总结的 provider，只能退化成硬截断最近若干条历史。
                        from watchlight.agents.runtime.embedded.history import truncate_history

                        messages[:] = truncate_history(messages, max_messages=20)

            # Call provider
            # full_text 收集本轮模型产生的文本。
            # 如果本轮还产生 tool_calls，full_text 会作为 assistant message 的 content 保留。
            full_text = ""
            # tool_calls 暂存模型提出的工具调用意图。
            # 注意：这里还没执行工具，只是收集 provider 解析出来的 tool_call chunk。
            tool_calls: list[dict[str, Any]] = []

            try:
                # provider.create_stream 是模型供应商适配层。
                # 对 DashScope/OpenAI，统一 SSE chunk 为 text_delta/tool_call/usage/error。
                async for chunk in provider.create_stream(
                    model=request.model_id,
                    messages=messages,
                    system=request.system_prompt,
                    tools=tool_defs if tool_defs else None,
                ):
                    if abort_signal.is_set():
                        # 即使模型正在流式返回，中途也允许取消。
                        yield AgentEvent(type=AgentEventType.COMPLETE, metadata={"aborted": True})
                        return

                    ct = chunk.get("type", "")
                    if ct == "text_delta":
                        # 文本增量会立即转成 AgentEvent 往上游抛。
                        # Gateway 收到后会继续广播 runtime.model.delta，也可能流式推给前端。
                        text = chunk.get("text", "")
                        full_text += text
                        yield AgentEvent(type=AgentEventType.TEXT_DELTA, text=text)
                    elif ct == "tool_call":
                        # 模型请求调用工具时，先缓存；等本次模型流结束后统一执行工具。
                        tool_calls.append(chunk)
                    elif ct == "usage":
                        # usage 可能在流的末尾出现，也可能按 provider 实现多次出现，所以这里累加。
                        total_input += chunk.get("input_tokens", 0)
                        total_output += chunk.get("output_tokens", 0)
                    elif ct == "error":
                        # provider 把 HTTP 错误或模型错误标准化成 error chunk；
                        # 这里抛出异常，再统一转成 AgentEventType.ERROR。
                        raise RuntimeError(chunk.get("error", "Provider error"))
            except Exception as e:
                # 单次尝试里的任何 provider 异常都变成 ERROR 事件。
                # run_with_retry 是否继续重试，由外层 retry_loop 决定。
                yield AgentEvent(type=AgentEventType.ERROR, error=str(e))
                return

            if not tool_calls:
                # 没有工具调用，说明模型已经给出最终回答，本轮 agent run 可以结束。
                break

            # Add assistant message with tool calls
            # OpenAI-compatible 协议要求：工具结果之前需要有一条 assistant message 声明 tool_calls。
            # 因此这里把模型刚才提出的 tool_calls 追加回 messages。
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": full_text}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.get("id", f"call_{turn}_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": json.dumps(tc.get("params") or tc.get("input") or {}),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ]
            messages.append(assistant_msg)

            # Execute tools
            if self._tool_registry:
                # run_tool_loop 会检查 tool_policy、执行工具，并返回 role=tool 消息。
                # 它同时产出 TOOL_CALL_START/TOOL_CALL_RESULT 事件，供 Gateway 和前端展示。
                async for tool_results, events in run_tool_loop(
                    tool_calls, self._tool_registry, tool_policy, tool_context
                ):
                    for event in events:
                        yield event
                    # 工具结果必须追加到 messages，下一轮模型调用才能看到工具输出。
                    messages.extend(tool_results)
            else:
                # 没有 tool_registry 时无法执行工具，只能结束循环。
                break

        if total_input > 0 or total_output > 0:
            # 所有模型轮次的 usage 汇总成一个 USAGE 事件，Gateway 会写入 session 统计。
            yield AgentEvent(
                type=AgentEventType.USAGE, input_tokens=total_input, output_tokens=total_output
            )
        # COMPLETE 表示 runtime 已结束事件流。
        # 它不代表一定有文本输出；如果前面发生 ERROR，调用方会根据 error 决定失败状态。
        yield AgentEvent(type=AgentEventType.COMPLETE)

    def _build_summarize_fn(self) -> Any:
        """Build an LLM-based summarization function using available provider."""
        # 压缩历史需要一个模型来做总结；如果没有 provider_registry，就无法构建总结函数。
        if not self._provider_registry:
            return None
        # Try dashscope first, then any available provider
        # 优先 DashScope 是因为当前项目默认模型链路主要走 DashScope，且 qwen-max 做总结比较稳定。
        provider = self._provider_registry.get("dashscope")
        if provider is None:
            # 如果没有 DashScope，就退而求其次使用任意已注册 provider。
            for pid in self._provider_registry.list_ids():
                provider = self._provider_registry.get(pid)
                if provider:
                    break
        if provider is None:
            return None

        from watchlight.agents.runtime.embedded.compaction import COMPACTION_SYSTEM_PROMPT

        async def summarize(text: str) -> str:
            # summarize 是一个闭包：它捕获上面选出的 provider。
            # compact_messages 调它时，只需要传入待总结文本。
            parts: list[str] = []
            async for chunk in provider.create_stream(
                model="qwen-max",
                messages=[{"role": "user", "content": text}],
                system=COMPACTION_SYSTEM_PROMPT,
            ):
                if chunk.get("type") == "text_delta":
                    # 总结也走流式接口，这里把所有 delta 拼成完整 summary。
                    parts.append(chunk.get("text", ""))
            return "".join(parts)

        return summarize

    async def _compact_for_session(self, session_key: str, reason: str) -> None:
        """Compaction callback for retry loop — loads transcript, compacts, writes back.

        This is the real system-level compaction path triggered by overflow/timeout.
        """
        # 会话级压缩需要同时读写 session 元数据和 transcript。
        # 如果 runtime 是轻量构造出来的，没有这些存储对象，就不能做写回压缩。
        if not self._session_store or not self._transcript_manager:
            log.warning("compact_no_session_store", session_key=session_key)
            return

        # 通过 session_key 找 session entry，entry.session_id 才是 transcript 文件的实际索引。
        entry = self._session_store.get(session_key)
        if entry is None:
            log.warning("compact_session_not_found", session_key=session_key)
            return

        # Load transcript
        # 这里读的是完整 transcript，而不是某一次 request.history。
        # 因为自动压缩要把会话长期历史写回本地状态。
        messages = self._transcript_manager.read_raw(entry.session_id)
        if len(messages) <= 12:
            # 消息太少时没必要压缩，避免过早丢失上下文细节。
            return

        # Backup for rollback
        # 压缩会原地修改 messages；先备份，方便质量过低或异常时回滚。
        backup = list(messages)

        summarize = self._build_summarize_fn()
        try:
            # compact_messages 会把多条历史总结成更短的上下文，并在消息上写入 _compaction 元数据。
            result = await compact_messages(
                messages,
                summarize_fn=summarize,
                reason=reason,
            )

            # Validate result — rollback if quality is bad
            # 压缩质量低时宁可不写回，也不要污染 transcript。
            compaction_meta = {}
            if messages and isinstance(messages[0], dict):
                compaction_meta = messages[0].get("_compaction", {})
            quality = compaction_meta.get("quality_score", 1.0)

            if quality < 0.2:
                log.error(
                    "compact_quality_too_low_rollback", quality=quality, session_key=session_key
                )
                messages.clear()
                messages.extend(backup)
                return

            # Write back to transcript
            # 质量检查通过后，清空原 transcript，再把压缩后的 messages 顺序写回。
            self._transcript_manager.clear(entry.session_id)
            for msg in messages:
                self._transcript_manager.append(entry.session_id, msg)

            # Persist checkpoint
            # compaction checkpoint 用于审计和回看：为什么压缩、压缩前后多少条、质量如何。
            count = (entry.compaction_count or 0) + 1
            if self._compaction_store:
                from watchlight.agents.runtime.embedded.compaction import (
                    build_compaction_checkpoint,
                )

                checkpoint = build_compaction_checkpoint(
                    result,
                    reason=reason,
                    quality=quality,
                )
                self._compaction_store.append(entry.session_id, checkpoint)

            self._session_store.update(
                session_key,
                {
                    # session store 只记录压缩次数等元数据，正文仍然在 transcript 中。
                    "compactionCount": count,
                },
            )
            self._session_store.save()

            log.info(
                "auto_compact_written_back",
                session_key=session_key,
                reason=reason,
                before=result.messages_before,
                after=result.messages_after,
                quality=quality,
                checkpoint_saved=self._compaction_store is not None,
            )

        except Exception as e:
            log.error("auto_compact_failed_rollback", error=str(e), session_key=session_key)
            # Rollback — don't corrupt transcript
            # 出错时恢复内存中的 messages；由于写回发生在 try 内后半段，异常时尽量避免半成品污染。
            messages.clear()
            messages.extend(backup)

    async def compact(self, session_key: str, reason: str) -> CompactionResult | None:
        """External compaction API — called by sessions.compact gateway method."""
        log.info("compact_requested", session_key=session_key, reason=reason)
        # The gateway method handles transcript load/write directly
        # This is for cases where the caller manages messages themselves
        # 当前这个方法只是保留 runtime 协议入口，不直接处理 transcript 写回。
        # 真正的 Gateway 会话压缩路径通常走 sessions.compact 或 _compact_for_session。
        summarize = self._build_summarize_fn()
        if summarize is None:
            return None
        return CompactionResult(
            messages_before=0,
            messages_after=0,
            summary="Use _compact_for_session() or sessions.compact instead",
        )

    async def abort(self, run_id: str) -> None:
        # 外部只需要提供 run_id，就能找到对应 asyncio.Event 并触发取消。
        # 实际停止点在 _single_attempt 的循环里检查 abort_signal.is_set()。
        signal = self._active_runs.get(run_id)
        if signal:
            signal.set()

    async def dispose(self) -> None:
        # 服务关闭或 runtime 被销毁时，通知所有活跃 run 尽快停止。
        for signal in self._active_runs.values():
            signal.set()
        self._active_runs.clear()
