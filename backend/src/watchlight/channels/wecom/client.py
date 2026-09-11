"""企业微信智能机器人临时 response_url 回复客户端。"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

import httpx


class WeComResponseClient:
    def __init__(self, *, timeout: float = 15.0) -> None:
        self.timeout = timeout

    @staticmethod
    def _validate_response_url(response_url: str) -> None:
        parsed = urlsplit(response_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "qyapi.weixin.qq.com"
            or parsed.port not in (None, 443)
        ):
            raise ValueError("invalid WeCom response_url host")

    async def send_markdown(self, response_url: str, content: str) -> dict[str, Any]:
        self._validate_response_url(response_url)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                response_url,
                json={"msgtype": "markdown", "markdown": {"content": content}},
            )
        response.raise_for_status()
        if not response.content:
            return {"errcode": 0, "errmsg": "ok"}
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("WeCom response was not an object")
        if data.get("errcode", 0) != 0:
            raise RuntimeError(
                f"WeCom reply failed: {data.get('errcode')} {data.get('errmsg', '')}"
            )
        return data
