"""企业微信智能机器人消息与 Watchlight 通用消息之间的转换。"""

from __future__ import annotations

import re
from typing import Any

from watchlight.contracts.channel.plugin import InboundMessage


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _media_attachment(payload: dict[str, Any], msg_type: str) -> dict[str, Any] | None:
    media = _dict(payload.get(msg_type))
    url = media.get("url")
    if not isinstance(url, str) or not url:
        return None
    return {"type": msg_type, "url": url, "encrypted": True}


def _mixed_content(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    mixed = _dict(payload.get("mixed"))
    items = mixed.get("msg_item")
    if not isinstance(items, list):
        return "", []
    texts: list[str] = []
    attachments: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("msgtype") or "")
        if item_type == "text":
            content = _dict(item.get("text")).get("content")
            if isinstance(content, str) and content.strip():
                texts.append(content.strip())
        elif item_type in {"image", "file", "video"}:
            attachment = _media_attachment(item, item_type)
            if attachment:
                attachments.append(attachment)
    return "\n".join(texts), attachments


def _message_content(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    msg_type = str(payload.get("msgtype") or "")
    if msg_type == "text":
        content = _dict(payload.get("text")).get("content")
        return (content if isinstance(content, str) else ""), []
    if msg_type == "voice":
        content = _dict(payload.get("voice")).get("content")
        return (content if isinstance(content, str) else ""), []
    if msg_type == "mixed":
        return _mixed_content(payload)
    if msg_type in {"image", "file", "video"}:
        attachment = _media_attachment(payload, msg_type)
        label = {"image": "[图片]", "file": "[文件]", "video": "[视频]"}[msg_type]
        return label, [attachment] if attachment else []
    return "", []


def _strip_mention(text: str, bot_name: str) -> str:
    if not bot_name:
        return text.strip()
    pattern = re.compile(rf"^\s*@{re.escape(bot_name)}(?:\s+|$)")
    return pattern.sub("", text, count=1).strip()


def parse_inbound(
    payload: dict[str, Any], *, account_id: str, bot_name: str = ""
) -> InboundMessage | None:
    """解析智能机器人文本、语音、图文和基础媒体消息。"""
    msg_type = str(payload.get("msgtype") or "")
    if msg_type in {"event", "stream"}:
        return None
    sender = _dict(payload.get("from"))
    sender_id = sender.get("userid")
    if not isinstance(sender_id, str) or not sender_id:
        return None
    chat_type_raw = str(payload.get("chattype") or "single")
    chat_type = "group" if chat_type_raw == "group" else "dm"
    chat_id = payload.get("chatid") if chat_type == "group" else sender_id
    if not isinstance(chat_id, str) or not chat_id:
        return None
    text, attachments = _message_content(payload)
    if chat_type == "group":
        text = _strip_mention(text, bot_name)
    if not text and not attachments:
        return None
    message_id = str(payload.get("msgid") or "")
    raw = {
        **payload,
        "account_id": account_id,
        "message_id": message_id,
        "mentioned_bot": chat_type == "group",
    }
    return InboundMessage(
        channel="wecom",
        accountId=account_id,
        senderId=sender_id,
        conversationId=chat_id,
        text=text,
        attachments=attachments or None,
        chatType=chat_type,
        raw=raw,
    )
