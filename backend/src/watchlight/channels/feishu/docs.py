# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 docs 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Feishu cloud docs OpenAPI client."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlparse

import httpx

from watchlight.channels.feishu.auth import FeishuAuth
from watchlight.core.env import is_truthy_env

FEISHU_OPENAPI_BASE = "https://open.feishu.cn/open-apis"
MAX_TEXT_RESPONSE_CHARS = 50000

DOCS_API_PREFIXES = (
    "/open-apis/doc/",
    "/open-apis/docx/",
    "/open-apis/drive/",
    "/open-apis/wiki/",
    "/open-apis/sheets/",
    "/open-apis/sheet/",
    "/open-apis/bitable/",
    "/open-apis/mindnote/",
    "/open-apis/slides/",
    "/open-apis/suite/docs-api/",
)

READ_ONLY_POST_PATHS = (
    "/open-apis/suite/docs-api/search/",
    "/open-apis/drive/v1/files/search",
)


def normalize_feishu_docs_path(path: str) -> tuple[str, dict[str, str]]:
    """Normalize a Feishu docs path or URL to an /open-apis path."""
    raw = path.strip()
    if not raw:
        raise ValueError("path is required")

    parsed = urlparse(raw)
    query: dict[str, str] = {}
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != "https" or parsed.netloc != "open.feishu.cn":
            raise ValueError("only https://open.feishu.cn URLs are allowed")
        normalized = parsed.path
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    else:
        normalized = raw

    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if not normalized.startswith("/open-apis/"):
        normalized = f"/open-apis{normalized}"

    return normalized, query


def is_docs_api_path(path: str) -> bool:
    """Return whether a normalized path belongs to Feishu cloud docs APIs."""
    return any(path.startswith(prefix) for prefix in DOCS_API_PREFIXES)


def is_mutation_request(method: str, path: str) -> bool:
    """Return whether the request can mutate cloud-docs data."""
    normalized_method = method.upper()
    if normalized_method in {"GET", "HEAD", "OPTIONS"}:
        return False
    return not any(path.startswith(prefix) for prefix in READ_ONLY_POST_PATHS)


class FeishuDocsClient:
    """Small tenant-token based client for Feishu cloud docs APIs."""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self._auth = FeishuAuth(app_id, app_secret)

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | list[Any] | None = None,
        write_enabled: bool = False,
    ) -> dict[str, Any]:
        """Call any supported Feishu cloud docs JSON OpenAPI."""
        normalized_path, path_query = normalize_feishu_docs_path(path)
        if not is_docs_api_path(normalized_path):
            raise ValueError(f"unsupported Feishu docs API path: {normalized_path}")

        normalized_method = method.upper()
        if is_mutation_request(normalized_method, normalized_path) and not write_enabled:
            raise RuntimeError(
                "Feishu docs write APIs are disabled. "
                "Set WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED=true to enable them."
            )

        merged_query: dict[str, Any] = {**path_query}
        if query:
            merged_query.update(query)

        token = await self._auth.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        url = f"{FEISHU_OPENAPI_BASE}{normalized_path.removeprefix('/open-apis')}"

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.request(
                normalized_method,
                url,
                headers=headers,
                params=merged_query or None,
                json=body,
            )

        content_type = resp.headers.get("content-type", "")
        result: dict[str, Any] = {
            "status": resp.status_code,
            "method": normalized_method,
            "path": normalized_path,
        }
        if "application/json" in content_type:
            result["json"] = resp.json()
        else:
            result["contentType"] = content_type
            result["text"] = resp.text[:MAX_TEXT_RESPONSE_CHARS]
        return result


def feishu_docs_write_enabled(env: dict[str, str] | None = None) -> bool:
    raw_env = env or {}
    value = raw_env.get("WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED")
    if value is None:
        import os

        value = os.environ.get("WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED")
    return is_truthy_env(value)
