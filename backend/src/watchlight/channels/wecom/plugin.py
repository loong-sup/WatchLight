"""企业微信智能机器人 API 模式渠道插件。"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from watchlight.channels.wecom.client import WeComResponseClient
from watchlight.channels.wecom.crypto import WeComCrypto, WeComCryptoError
from watchlight.channels.wecom.message import parse_inbound
from watchlight.contracts.channel.plugin import (
    ChannelCapabilities,
    ChannelMeta,
    OutboundMessage,
)
from watchlight.core.logging import get_logger

log = get_logger("channel.wecom")
MESSAGE_DEDUPE_TTL_SECONDS = 600.0
RESPONSE_URL_TTL_SECONDS = 3600.0


@dataclass
class _PendingResponse:
    url: str
    conversation_id: str
    created_at: float


class WeComChannelPlugin:
    """接收智能机器人加密回调，并通过临时 response_url 异步回复。"""

    def __init__(self, on_inbound: Any = None) -> None:
        self._on_inbound = on_inbound
        self._configs: dict[str, dict[str, Any]] = {}
        self._cryptos: dict[str, WeComCrypto] = {}
        self._clients: dict[str, WeComResponseClient] = {}
        self._seen_message_ids: dict[str, float] = {}
        self._responses: dict[str, _PendingResponse] = {}
        self._latest_by_conversation: dict[str, str] = {}
        self._tasks: set[asyncio.Task[Any]] = set()
        self._last_error: dict[str, str] = {}

    @property
    def id(self) -> str:
        return "wecom"

    @property
    def meta(self) -> ChannelMeta:
        return ChannelMeta(
            id="wecom",
            label="企业微信",
            selectionLabel="WeCom",
            docsPath="docs/channels/wecom",
            blurb="企业微信智能机器人 — 群聊 @ 与单聊",
            markdownCapable=True,
        )

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(chatTypes=["dm", "group"], reply=True, media=True)

    def list_account_ids(self, config: dict[str, Any]) -> list[str]:
        wecom_cfg = config.get("channels", {}).get("wecom", {})
        if wecom_cfg.get("enabled") is False:
            return []
        accounts = wecom_cfg.get("accounts", {})
        enabled_accounts = [
            account_id
            for account_id, account_cfg in accounts.items()
            if isinstance(account_cfg, dict) and account_cfg.get("enabled") is not False
        ]
        if enabled_accounts:
            return enabled_accounts
        return ["default"] if self._resolve_account_config(config, "default") else []

    def get_status(self) -> dict[str, Any]:
        accounts = sorted(self._configs)
        return {
            "configured": bool(accounts),
            "running": bool(accounts),
            "accounts": accounts,
            "lastError": dict(self._last_error),
        }

    def _resolve_account_config(
        self, config: dict[str, Any], account_id: str
    ) -> dict[str, Any] | None:
        wecom_cfg = config.get("channels", {}).get("wecom", {})
        accounts = wecom_cfg.get("accounts", {})
        account_cfg = accounts.get(account_id, {}) if isinstance(accounts, dict) else {}
        if not isinstance(account_cfg, dict):
            account_cfg = {}
        merged = {**wecom_cfg, **account_cfg}
        token = merged.get("token") or os.environ.get("WECOM_TOKEN", "")
        aes_key = merged.get("encodingAESKey") or os.environ.get(
            "WECOM_ENCODING_AES_KEY", ""
        )
        if not token or not aes_key:
            return None
        merged["token"] = token
        merged["encodingAESKey"] = aes_key
        merged["receiveId"] = merged.get("receiveId") or os.environ.get(
            "WECOM_RECEIVE_ID", ""
        )
        merged["botName"] = merged.get("botName") or os.environ.get("WECOM_BOT_NAME", "")
        return merged

    async def start(self, account_id: str, config: dict[str, Any]) -> None:
        account_cfg = self._resolve_account_config(config, account_id)
        if not account_cfg:
            self._last_error[account_id] = "missing token or EncodingAESKey"
            log.error("wecom_missing_credentials", account_id=account_id)
            return
        try:
            crypto = WeComCrypto(
                str(account_cfg["token"]),
                str(account_cfg["encodingAESKey"]),
                str(account_cfg.get("receiveId") or ""),
            )
        except WeComCryptoError as exc:
            self._last_error[account_id] = str(exc)
            raise
        self._configs[account_id] = account_cfg
        self._cryptos[account_id] = crypto
        self._clients[account_id] = WeComResponseClient(
            timeout=float(account_cfg.get("timeoutSeconds", 15.0))
        )
        self._last_error.pop(account_id, None)
        log.info(
            "wecom_channel_started",
            account_id=account_id,
            callback_path=f"/api/channels/wecom/{account_id}/events",
        )

    async def stop(self, account_id: str) -> None:
        self._configs.pop(account_id, None)
        self._cryptos.pop(account_id, None)
        self._clients.pop(account_id, None)
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        log.info("wecom_channel_stopped", account_id=account_id)

    def verify_url(
        self,
        account_id: str,
        *,
        signature: str,
        timestamp: str,
        nonce: str,
        echo_str: str,
    ) -> str:
        crypto = self._require_crypto(account_id)
        crypto.verify_signature(signature, timestamp, nonce, echo_str)
        return crypto.decrypt(echo_str)

    async def handle_encrypted_callback(
        self,
        account_id: str,
        *,
        signature: str,
        timestamp: str,
        nonce: str,
        body: bytes,
    ) -> bool:
        crypto = self._require_crypto(account_id)
        try:
            envelope = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WeComCryptoError("callback body is not JSON") from exc
        if not isinstance(envelope, dict) or not isinstance(envelope.get("encrypt"), str):
            raise WeComCryptoError("callback body is missing encrypt")
        encrypted = envelope["encrypt"]
        crypto.verify_signature(signature, timestamp, nonce, encrypted)
        payload = crypto.decrypt_json(encrypted)
        return await self.handle_event(account_id, payload)

    async def handle_event(self, account_id: str, payload: dict[str, Any]) -> bool:
        message_id = str(payload.get("msgid") or "")
        if message_id and self._is_duplicate(message_id):
            log.info("wecom_duplicate_message_ignored", message_id=message_id)
            return False
        account_cfg = self._configs.get(account_id, {})
        message = parse_inbound(
            payload,
            account_id=account_id,
            bot_name=str(account_cfg.get("botName") or ""),
        )
        if message is None:
            log.info(
                "wecom_event_ignored",
                account_id=account_id,
                msg_type=payload.get("msgtype"),
            )
            return False
        response_url = payload.get("response_url")
        if isinstance(response_url, str) and response_url:
            self._remember_response(message_id, message.conversation_id, response_url)
        if message_id:
            self._seen_message_ids[message_id] = time.monotonic()
        if self._on_inbound:
            task = asyncio.create_task(self._on_inbound(message))
            self._tasks.add(task)
            task.add_done_callback(self._on_task_done)
        return True

    async def send(
        self, account_id: str, conversation_id: str, message: OutboundMessage
    ) -> None:
        text = (message.text or "").strip()
        if not text:
            return
        self._prune_state()
        response_key = message.reply_to_id or self._latest_by_conversation.get(conversation_id)
        pending = self._responses.get(str(response_key or ""))
        if pending is None:
            raise RuntimeError(
                "WeCom intelligent bot can only reply through a recent inbound response_url"
            )
        client = self._clients.get(account_id) or self._clients.get("default")
        if client is None:
            raise RuntimeError("WeCom client is not initialized")
        await client.send_markdown(pending.url, text)
        self._responses.pop(str(response_key), None)
        if self._latest_by_conversation.get(pending.conversation_id) == response_key:
            self._latest_by_conversation.pop(pending.conversation_id, None)

    def _require_crypto(self, account_id: str) -> WeComCrypto:
        crypto = self._cryptos.get(account_id) or self._cryptos.get("default")
        if crypto is None:
            raise WeComCryptoError(f"WeCom account is not configured: {account_id}")
        return crypto

    def _remember_response(self, message_id: str, conversation_id: str, url: str) -> None:
        if not message_id:
            return
        self._responses[message_id] = _PendingResponse(
            url=url,
            conversation_id=conversation_id,
            created_at=time.monotonic(),
        )
        self._latest_by_conversation[conversation_id] = message_id

    def _is_duplicate(self, message_id: str) -> bool:
        self._prune_state()
        return message_id in self._seen_message_ids

    def _prune_state(self) -> None:
        now = time.monotonic()
        expired_messages = [
            key
            for key, seen_at in self._seen_message_ids.items()
            if now - seen_at > MESSAGE_DEDUPE_TTL_SECONDS
        ]
        for key in expired_messages:
            self._seen_message_ids.pop(key, None)
        expired_responses = [
            key
            for key, pending in self._responses.items()
            if now - pending.created_at > RESPONSE_URL_TTL_SECONDS
        ]
        for key in expired_responses:
            pending = self._responses.pop(key)
            if self._latest_by_conversation.get(pending.conversation_id) == key:
                self._latest_by_conversation.pop(pending.conversation_id, None)

    def _on_task_done(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error:
            log.error("wecom_inbound_task_failed", error=str(error))
