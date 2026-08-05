# 文件说明：本文件属于 通道接入层。
# 主要职责：处理消息格式转换。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""飞书消息格式转换：把飞书事件转成统一 InboundMessage，并格式化出站文本。"""

import json
import re
from typing import Any

from watchlight.contracts.channel.plugin import InboundMessage, OutboundMessage

_AT_TAG_RE = re.compile(r"<at\s+[^>]*>.*?</at>")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)]\((https?://[^)]+)\)")
_MARKDOWN_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+")
_MARKDOWN_HEADING_LINE_RE = re.compile(r"(?m)^#{1,6}[ \t]+(.+?)[ \t]*$")
_MARKDOWN_FENCE_LINE_RE = re.compile(r"(?m)^```[^\r\n]*\r?\n?")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_sender_id(sender: dict[str, Any]) -> str:
    sender_id = _as_dict(sender.get("sender_id"))
    # 优先使用飞书 open_id；user_id/union_id 主要兼容 sidecar 或测试 payload。
    for key in ("open_id", "user_id", "union_id"):
        value = sender_id.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _read_text(content_str: Any) -> str:
    if not isinstance(content_str, str):
        return ""
    try:
        # 飞书文本消息的 content 通常是 JSON 字符串，例如 {"text": "..."}。
        content = json.loads(content_str)
    except json.JSONDecodeError:
        return content_str
    if not isinstance(content, dict):
        return content_str
    text = content.get("text")
    return text if isinstance(text, str) else ""


def _mention_open_id(mention: dict[str, Any]) -> str:
    mention_id = mention.get("id")
    if isinstance(mention_id, dict):
        for key in ("open_id", "user_id", "union_id"):
            value = mention_id.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return mention_id.strip() if isinstance(mention_id, str) else ""


def _message_mentions(message: dict[str, Any]) -> list[dict[str, Any]]:
    mentions = message.get("mentions")
    if not isinstance(mentions, list):
        return []
    return [mention for mention in mentions if isinstance(mention, dict)]


def _bot_mention(
    message: dict[str, Any], bot_open_id: str | None
) -> dict[str, Any] | None:
    mentions = _message_mentions(message)
    if bot_open_id:
        return next(
            (
                mention
                for mention in mentions
                if _mention_open_id(mention) == bot_open_id
            ),
            None,
        )
    # group_at_msg 事件至少包含机器人提及；未配置 botOpenId 时，飞书将触发
    # 该事件的机器人作为第一个 mention 返回。
    return mentions[0] if mentions else None


def _normalize_mentions(
    message: dict[str, Any], text: str, bot_open_id: str | None
) -> str:
    bot_mention = _bot_mention(message, bot_open_id)
    value = text
    for mention in _message_mentions(message):
        key = mention.get("key")
        if not isinstance(key, str) or not key:
            continue
        if mention is bot_mention:
            replacement = ""
        else:
            name = mention.get("name")
            replacement = f"@{name}" if isinstance(name, str) and name.strip() else "@用户"
        value = value.replace(key, replacement)
    value = _AT_TAG_RE.sub("", value)
    return re.sub(r"[ \t]{2,}", " ", value).strip()


def _mentioned_bot(
    message: dict[str, Any], text: str, bot_open_id: str | None = None
) -> bool:
    mentions = message.get("mentions")
    if isinstance(mentions, list) and mentions:
        return _bot_mention(message, bot_open_id) is not None
    # 有些事件不会填 mentions，但会把原始 <at ...> 标签留在 text 里。
    return bool(_AT_TAG_RE.search(text))


def _unwrap_event(event_data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    """兼容飞书原始事件、SDK 包装事件和内部 sidecar 事件，返回统一三元组。"""
    payload = event_data
    if isinstance(event_data.get("event"), dict):
        payload = event_data["event"]
    event = _as_dict(payload)
    message = _as_dict(event.get("message"))
    event_type = str(event_data.get("event_type") or event_data.get("eventType") or "")
    if not event_type:
        header = _as_dict(event_data.get("header"))
        event_type = str(header.get("event_type") or "")
    return event, message, event_type


def parse_inbound(
    event_data: dict[str, Any], *, bot_open_id: str | None = None
) -> InboundMessage | None:
    """把飞书文本消息事件解析成 Watchlight 内部统一的入站消息。"""
    event, message, event_type = _unwrap_event(event_data)
    msg_type = event_data.get("msg_type") or message.get("message_type")
    if msg_type != "text":
        # 当前只支持文本消息；图片、文件、音频等需要设计解析和安全边界后再接入。
        return None

    text = _read_text(event_data.get("content", message.get("content", "{}")))
    sender = _as_dict(event.get("sender"))
    sender_id = event_data.get("sender_id")
    if not isinstance(sender_id, str) or not sender_id.strip():
        sender_id = _read_sender_id(sender)
    chat_id = event_data.get("chat_id", message.get("chat_id", ""))
    chat_type = event_data.get("chat_type", message.get("chat_type", "p2p"))
    message_id = event_data.get("message_id", message.get("message_id"))
    raw = {**event_data, "event_type": event_type, "message_id": message_id}
    raw["mentioned_bot"] = _mentioned_bot(message, text, bot_open_id)

    return InboundMessage(
        channel="feishu",
        accountId=event_data.get("account_id", "default"),
        senderId=str(sender_id or ""),
        conversationId=str(chat_id or ""),
        text=_normalize_mentions(message, text, bot_open_id),
        chatType="group" if chat_type == "group" else "dm",
        raw=raw,
    )


def format_outbound(message: OutboundMessage) -> str:
    """把 Watchlight 出站消息格式化为飞书纯文本内容。"""
    return message.text or ""


def markdown_to_feishu_markdown(text: str) -> str:
    """Convert common Markdown to the subset rendered reliably by Feishu cards.

    Feishu's card Markdown element accepts bold text and lists, but heading and
    inline-code syntax can be displayed literally.  Keep the semantic emphasis
    while removing syntax known to leak into the rendered message.
    """
    value = _MARKDOWN_HEADING_LINE_RE.sub(r"**\1**", text)
    value = _MARKDOWN_FENCE_LINE_RE.sub("", value)
    return value.replace("`", "")


def markdown_to_plain_text(text: str) -> str:
    """Remove common Markdown markers while retaining readable fallback content."""
    value = _MARKDOWN_LINK_RE.sub(r"\1（\2）", text)
    value = _MARKDOWN_HEADING_RE.sub("", value)
    value = value.replace("```", "").replace("**", "").replace("__", "")
    return value.replace("`", "")
