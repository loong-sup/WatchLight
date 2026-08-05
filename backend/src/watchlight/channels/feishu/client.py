# 文件说明：本文件属于 通道接入层。
# 主要职责：封装外部 API 请求。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Feishu Open API client — send messages."""

from typing import Any

import httpx

from watchlight.channels.feishu.auth import FeishuAuth
from watchlight.channels.feishu.message import markdown_to_feishu_markdown
from watchlight.core.logging import get_logger

log = get_logger("channel.feishu.client")

FEISHU_MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"


def build_markdown_card(text: str) -> dict[str, Any]:
    """Build a Feishu interactive card that renders the supported Markdown subset."""
    return {
        "config": {"wide_screen_mode": True},
        "elements": [
            {"tag": "markdown", "content": markdown_to_feishu_markdown(text)}
        ],
    }


class FeishuClient:
    """Feishu Open API client for sending messages."""

    def __init__(self, auth: FeishuAuth) -> None:
        self.auth = auth

    async def send_text(self, chat_id: str, text: str, msg_type: str = "chat_id") -> dict[str, Any]:
        """Send a plain text message to a chat."""
        token = await self.auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        import json

        body = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                FEISHU_MESSAGE_URL,
                headers=headers,
                json=body,
                params={"receive_id_type": msg_type},
            )
            data: dict[str, Any] = resp.json()

        if data.get("code") != 0:
            log.error("feishu_send_failed", code=data.get("code"), msg=data.get("msg"))
        return data

    async def reply_text(self, message_id: str, text: str) -> dict[str, Any]:
        """Reply to a specific message."""
        token = await self.auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        import json

        body = {
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }

        url = f"{FEISHU_MESSAGE_URL}/{message_id}/reply"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=body)
            result: dict[str, Any] = resp.json()

        if result.get("code") != 0:
            log.error("feishu_reply_failed", code=result.get("code"), msg=result.get("msg"))
        return result

    async def send_markdown(
        self, chat_id: str, text: str, msg_type: str = "chat_id"
    ) -> dict[str, Any]:
        """Send Markdown in a Feishu interactive card."""
        token = await self.auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        import json

        body = {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(build_markdown_card(text), ensure_ascii=False),
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                FEISHU_MESSAGE_URL,
                headers=headers,
                json=body,
                params={"receive_id_type": msg_type},
            )
            result: dict[str, Any] = response.json()
        return result

    async def reply_markdown(self, message_id: str, text: str) -> dict[str, Any]:
        """Reply to a message with a Markdown interactive card."""
        token = await self.auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        import json

        body = {
            "msg_type": "interactive",
            "content": json.dumps(build_markdown_card(text), ensure_ascii=False),
        }
        url = f"{FEISHU_MESSAGE_URL}/{message_id}/reply"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=body)
            result: dict[str, Any] = response.json()
        return result
