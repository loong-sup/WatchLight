# 文件说明：本文件属于 通道接入层。
# 主要职责：把外部能力适配为统一插件。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""飞书通道插件：把飞书事件和发送接口适配成 Watchlight 的 ChannelPlugin。"""

import os
import time
from typing import Any

from watchlight.channels.feishu.auth import FeishuAuth
from watchlight.channels.feishu.client import FeishuClient
from watchlight.channels.feishu.events import FeishuEventSubscriber
from watchlight.channels.feishu.message import (
    format_outbound,
    markdown_to_plain_text,
    parse_inbound,
)
from watchlight.contracts.channel.plugin import (
    ChannelCapabilities,
    ChannelMeta,
    OutboundMessage,
)
from watchlight.core.logging import get_logger

log = get_logger("channel.feishu")
MESSAGE_DEDUPE_TTL_SECONDS = 600.0


class FeishuChannelPlugin:
    """飞书通道实现，当前支持长连接接收事件和纯文本回复。"""

    def __init__(self, on_inbound: Any = None) -> None:
        self._auths: dict[str, FeishuAuth] = {}
        self._clients: dict[str, FeishuClient] = {}
        self._subscribers: dict[str, FeishuEventSubscriber] = {}
        self._configs: dict[str, dict[str, Any]] = {}
        self._last_error: dict[str, str] = {}
        # 飞书可能因网络或 ack 时序重投同一消息；这里保留短期内存去重窗口。
        self._seen_message_ids: dict[str, float] = {}
        self._on_inbound = on_inbound  # 解析出入站消息后回调 Gateway 继续执行 agent。

    @property
    def id(self) -> str:
        return "feishu"

    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="feishu",
            label="飞书",
            selectionLabel="Feishu",
            docsPath="docs/channels/feishu",
            blurb="飞书机器人 — WebSocket 长连接",
            markdownCapable=True,
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(chatTypes=["dm", "group"])

    def list_account_ids(self, config: dict[str, Any]) -> "list[str]":
        channels_cfg = config.get("channels", {})
        feishu_cfg = channels_cfg.get("feishu", {})
        if feishu_cfg.get("enabled") is False:
            return []
        accounts = feishu_cfg.get("accounts", {})
        enabled_accounts = [
            account_id
            for account_id, account_cfg in accounts.items()
            if isinstance(account_cfg, dict) and account_cfg.get("enabled") is not False
        ]
        if enabled_accounts:
            return enabled_accounts
        if self._resolve_account_config(config, "default"):
            return ["default"]
        return []

    def get_status(self) -> dict[str, Any]:
        running_accounts = sorted(self._subscribers.keys())
        configured_accounts = sorted(self._configs.keys())
        return {
            "configured": bool(configured_accounts),
            "running": bool(running_accounts),
            "accounts": configured_accounts or running_accounts,
            "runningAccounts": running_accounts,
            "lastError": dict(self._last_error),
        }

    def _resolve_account_config(
        self, config: dict[str, Any], account_id: str
    ) -> dict[str, Any] | None:
        channels_cfg = config.get("channels", {})
        feishu_cfg = channels_cfg.get("feishu", {})
        accounts = feishu_cfg.get("accounts", {})
        account_cfg = accounts.get(account_id, {}) if isinstance(accounts, dict) else {}
        if not isinstance(account_cfg, dict):
            account_cfg = {}
        merged = {**feishu_cfg, **account_cfg}
        # 账号级配置优先；没有写配置时再从环境变量读取，方便本地单账号开发。
        app_id = merged.get("appId") or os.environ.get("FEISHU_APP_ID", "")
        app_secret = merged.get("appSecret") or os.environ.get("FEISHU_APP_SECRET", "")
        if not app_id or not app_secret:
            return None
        merged["appId"] = app_id
        merged["appSecret"] = app_secret
        return merged

    async def start(self, account_id: str, config: dict[str, Any]) -> None:
        """启动指定飞书账号；长连接模式下会建立事件订阅。"""
        account_cfg = self._resolve_account_config(config, account_id)

        if not account_cfg:
            log.error("feishu_missing_credentials", account_id=account_id)
            self._last_error[account_id] = "missing credentials"
            return

        self._configs[account_id] = account_cfg
        auth = FeishuAuth(account_cfg["appId"], account_cfg["appSecret"])
        self._auths[account_id] = auth
        self._clients[account_id] = FeishuClient(auth)

        async def on_event(event_data: dict[str, Any]) -> None:
            await self.handle_event(account_id, event_data)

        connection_mode = account_cfg.get("connectionMode", "websocket")
        if connection_mode in ("websocket", "long_connection", "longConnection"):
            # 长连接模式不需要公网 webhook 地址，适合本地开发和内网环境直接接收事件。
            subscriber = FeishuEventSubscriber(auth, on_event)
            self._subscribers[account_id] = subscriber
            subscriber.start()
            log.info("feishu_channel_started", account_id=account_id, mode=connection_mode)
        else:
            log.info(
                "feishu_channel_ready_without_inbound_transport",
                account_id=account_id,
                mode=connection_mode,
            )

    async def stop(self, account_id: str) -> None:
        subscriber = self._subscribers.pop(account_id, None)
        if subscriber:
            subscriber.stop()
        log.info("feishu_channel_stopped", account_id=account_id)

    async def handle_event(self, account_id: str, event_data: dict[str, Any]) -> bool:
        account_cfg = self._configs.get(account_id, {})
        configured_bot_open_id = account_cfg.get("botOpenId")
        bot_open_id = (
            str(configured_bot_open_id).strip() if configured_bot_open_id else None
        )
        msg = parse_inbound(
            {**event_data, "account_id": account_id}, bot_open_id=bot_open_id
        )
        if msg is None:
            log.info(
                "feishu_event_ignored",
                account_id=account_id,
                event_type=event_data.get("event_type") or event_data.get("eventType"),
            )
            return False

        if bot_open_id and msg.sender_id == bot_open_id:
            log.info("feishu_self_message_ignored", account_id=account_id)
            return False

        message_id = str((msg.raw or {}).get("message_id") or "")
        if message_id and self._is_duplicate_message(message_id):
            log.info(
                "feishu_duplicate_message_ignored",
                account_id=account_id,
                message_id=message_id,
            )
            return False

        group_policy = account_cfg.get("groupPolicy", "mention")
        if msg.chat_type == "group" and group_policy != "open":
            # 群聊默认只处理明确 @ 机器人的消息，避免机器人读取和回复普通群聊噪声。
            mentioned = bool((msg.raw or {}).get("mentioned_bot"))
            if not mentioned:
                log.info(
                    "feishu_group_message_ignored_no_mention",
                    account_id=account_id,
                    conversation_id=msg.conversation_id,
                )
                return False

        if message_id:
            self._seen_message_ids[message_id] = time.monotonic()
        if self._on_inbound:
            await self._on_inbound(msg)
        return True

    def _is_duplicate_message(self, message_id: str) -> bool:
        now = time.monotonic()
        # 去重缓存很小，采用惰性清理即可，避免额外维护一个后台定时任务。
        expired = [
            seen_id
            for seen_id, seen_at in self._seen_message_ids.items()
            if now - seen_at > MESSAGE_DEDUPE_TTL_SECONDS
        ]
        for seen_id in expired:
            self._seen_message_ids.pop(seen_id, None)
        return message_id in self._seen_message_ids

    async def send(self, account_id: str, conversation_id: str, message: OutboundMessage) -> None:
        """向飞书发送可渲染 Markdown；卡片不可用时安全降级为纯文本。"""
        client = self._clients.get(account_id) or self._clients.get("default")
        if not client:
            log.error("feishu_client_not_initialized")
            return
        text = format_outbound(message)
        if not text:
            return

        # 有原消息 id 时优先回复原消息；没有时退化为向会话直接发送文本。
        if message.reply_to_id:
            result = await client.reply_markdown(message.reply_to_id, text)
            if result.get("code") != 0:
                result = await client.reply_text(
                    message.reply_to_id, markdown_to_plain_text(text)
                )
        else:
            result = await client.send_markdown(conversation_id, text)
            if result.get("code") != 0:
                result = await client.send_text(
                    conversation_id, markdown_to_plain_text(text)
                )
        if result.get("code") != 0:
            raise RuntimeError(f"Feishu send failed: {result.get('code')} {result.get('msg')}")
