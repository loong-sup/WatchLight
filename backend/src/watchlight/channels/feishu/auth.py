# 文件说明：本文件属于 通道接入层。
# 主要职责：处理认证和 token 获取。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Feishu app credential management — tenant_access_token auto-refresh with retry."""

import asyncio
import time

import httpx

from watchlight.core.logging import get_logger

log = get_logger("channel.feishu.auth")

FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MAX_RETRY = 3
RETRY_DELAYS = [1, 3, 10]  # Seconds between retries


class FeishuAuth:
    """Manages Feishu app credentials and tenant_access_token."""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._expires_at: float = 0

    async def get_token(self) -> str:
        """Get a valid tenant_access_token, refreshing if needed. Retries on failure."""
        if self._token and time.time() < self._expires_at - 300:
            return self._token

        last_error: Exception | None = None
        for attempt in range(MAX_RETRY):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        FEISHU_TOKEN_URL,
                        json={"app_id": self.app_id, "app_secret": self.app_secret},
                    )
                    resp.raise_for_status()
                    data: dict[str, object] = resp.json()

                code = data.get("code")
                if code != 0:
                    msg = data.get("msg", "unknown error")
                    log.warning("feishu_token_api_error", code=code, msg=msg, attempt=attempt + 1)
                    last_error = RuntimeError(f"Feishu auth failed: {msg}")
                else:
                    token = data.get("tenant_access_token")
                    if not isinstance(token, str) or not token:
                        last_error = RuntimeError("Empty token in response")
                    else:
                        self._token = token
                        expire = data.get("expire", 7200)
                        self._expires_at = time.time() + (
                            expire if isinstance(expire, int) else 7200
                        )
                        log.info("feishu_token_refreshed", expires_in=expire, attempt=attempt + 1)
                        return self._token

            except httpx.HTTPStatusError as e:
                log.error(
                    "feishu_token_http_error", status=e.response.status_code, attempt=attempt + 1
                )
                last_error = e
            except httpx.RequestError as e:
                log.error("feishu_token_request_error", error=str(e), attempt=attempt + 1)
                last_error = e
            except ValueError:
                log.error(
                    "feishu_token_invalid_json",
                    status=resp.status_code,
                    attempt=attempt + 1,
                )
                last_error = RuntimeError(
                    f"Feishu auth returned invalid JSON: HTTP {resp.status_code}"
                )

            if attempt < MAX_RETRY - 1:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                log.info("feishu_token_retry", delay=delay, attempt=attempt + 1)
                await asyncio.sleep(delay)

        raise RuntimeError(
            f"Feishu token refresh failed after {MAX_RETRY} attempts"
        ) from last_error

    @property
    def is_valid(self) -> bool:
        return self._token is not None and time.time() < self._expires_at - 300
