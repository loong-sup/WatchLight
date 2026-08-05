# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 web search 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""联网搜索工具：优先使用 Bocha，没有 API Key 时降级到 DuckDuckGo HTML 搜索。"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import unquote

import httpx

from watchlight.tools.types import ToolDefinition

BOCHA_WEB_SEARCH_URL = "https://api.bocha.cn/v1/web-search"
DEFAULT_RESULT_COUNT = 8
MAX_RESULT_COUNT = 20
WEB_SEARCH_PROMPT_INSTRUCTIONS = (
    "Use web_search for deep exploration, current or changing information, niche topics, "
    "fact verification, and source-backed answers. For requests asking for a detailed analysis "
    "of a concept that may require external context, search first, then synthesize using the "
    "returned sources. When search results will be used in a report or document, use the actual "
    "returned titles, URLs, snippets, summaries, and publication dates; never invent citations "
    "or leave placeholders such as URL_1, source TBD, 指标A, or 待补充. If the search result does "
    "not provide official or primary material, say that clearly in the generated content. Do not "
    "call web_search for simple stable facts or purely local tasks."
)


def _clamp_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = DEFAULT_RESULT_COUNT
    return max(1, min(count, MAX_RESULT_COUNT))


def _bocha_result(item: dict[str, Any]) -> dict[str, str]:
    # Bocha 返回字段和内部工具字段不完全一致，这里统一成模型稳定可读的结果结构。
    title = item.get("name") or item.get("title") or ""
    snippet = item.get("snippet") or item.get("summary") or ""
    return {
        "title": str(title),
        "url": str(item.get("url") or ""),
        "snippet": str(snippet),
        "summary": str(item.get("summary") or ""),
        "site_name": str(item.get("siteName") or item.get("site_name") or ""),
        "date_published": str(item.get("datePublished") or item.get("date_published") or ""),
    }


async def _bocha_search(params: dict[str, Any], api_key: str) -> dict[str, Any]:
    query = str(params.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")

    count = _clamp_count(params.get("count", params.get("max_results", DEFAULT_RESULT_COUNT)))
    freshness = str(params.get("freshness") or "noLimit")
    summary = bool(params.get("summary", True))
    body: dict[str, Any] = {
        "query": query,
        "freshness": freshness,
        "summary": summary,
        "count": count,
    }
    for key in ("include", "exclude"):
        value = params.get(key)
        if isinstance(value, list) and value:
            # include/exclude 是可选域名过滤器；空列表不传，减少不同 API 版本兼容问题。
            body[key] = [str(item) for item in value]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            BOCHA_WEB_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    if resp.status_code != 200:
        return {
            "query": query,
            "provider": "bocha",
            "results": [],
            "error": f"Bocha search failed: HTTP {resp.status_code}",
        }

    payload = resp.json()
    raw_data = payload.get("data") if isinstance(payload, dict) else {}
    data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    raw_web_pages = data.get("webPages")
    web_pages: dict[str, Any] = raw_web_pages if isinstance(raw_web_pages, dict) else {}
    raw_items = web_pages.get("value")
    items: list[Any] = raw_items if isinstance(raw_items, list) else []
    # 搜索结果里偶发异常 item 时直接跳过，避免一个坏条目导致整次搜索失败。
    results = [_bocha_result(item) for item in items if isinstance(item, dict)]

    return {
        "query": query,
        "provider": "bocha",
        "freshness": freshness,
        "summary": summary,
        "results": results[:count],
    }


async def _duckduckgo_search(params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    count = _clamp_count(params.get("count", params.get("max_results", DEFAULT_RESULT_COUNT)))

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.post("https://html.duckduckgo.com/html/", data={"q": query})
            html = resp.text
    except Exception as e:
        return {
            "query": query,
            "provider": "duckduckgo",
            "error": f"Search failed: {e}",
            "results": [],
        }

    results: list[dict[str, str]] = []
    links = re.findall(r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>', html)
    snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

    for index, (href, title) in enumerate(links[:count]):
        title_clean = re.sub(r"<[^>]+>", "", title).strip()
        snippet = re.sub(r"<[^>]+>", "", snippets[index]).strip() if index < len(snippets) else ""
        actual_url = href
        uddg_match = re.search(r"uddg=([^&]+)", href)
        if uddg_match:
            # DuckDuckGo HTML 结果会把真实目标地址包在 uddg 参数里，需要解包。
            actual_url = unquote(uddg_match.group(1))
        results.append({"title": title_clean, "url": actual_url, "snippet": snippet})

    return {"query": query, "provider": "duckduckgo", "results": results}


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    api_key = os.environ.get("BOCHA_API_KEY", "").strip()
    if api_key:
        return await _bocha_search(params, api_key)
    return await _duckduckgo_search(params)


def create_web_search_tool() -> ToolDefinition:
    return ToolDefinition(
        name="web_search",
        description=(
            "Search the web for current, factual, or deep-research information. Uses Bocha "
            "Web Search API when BOCHA_API_KEY is configured, otherwise falls back to DuckDuckGo. "
            "Use returned result fields directly as evidence; do not fabricate citations."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "count": {
                    "type": "integer",
                    "default": DEFAULT_RESULT_COUNT,
                    "description": "Number of results to return, 1-20.",
                },
                "max_results": {
                    "type": "integer",
                    "default": DEFAULT_RESULT_COUNT,
                    "description": "Backward-compatible alias for count.",
                },
                "freshness": {
                    "type": "string",
                    "enum": ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"],
                    "default": "noLimit",
                },
                "summary": {"type": "boolean", "default": True},
                "include": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional domains to include.",
                },
                "exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional domains to exclude.",
                },
            },
            "required": ["query"],
        },
        prompt_instructions=WEB_SEARCH_PROMPT_INSTRUCTIONS,
        handler=_handler,
    )
