# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 web search 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""联网搜索工具：优先使用 Tavily，没有 API Key 时降级到 DuckDuckGo HTML 搜索。"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from watchlight.tools.types import ToolDefinition

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
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


def _tavily_result(item: dict[str, Any]) -> dict[str, str]:
    """Normalize Tavily's result shape to Watchlight's stable search schema."""
    url = str(item.get("url") or "")
    content = str(item.get("content") or "")
    return {
        "title": str(item.get("title") or ""),
        "url": url,
        "snippet": content,
        "summary": content,
        "site_name": urlparse(url).hostname or "",
        "date_published": str(item.get("published_date") or ""),
    }


async def _tavily_search(params: dict[str, Any], api_key: str) -> dict[str, Any]:
    query = str(params.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")

    count = _clamp_count(params.get("count", params.get("max_results", DEFAULT_RESULT_COUNT)))
    freshness = str(params.get("freshness") or "noLimit")
    time_range = {
        "oneDay": "day",
        "oneWeek": "week",
        "oneMonth": "month",
        "oneYear": "year",
    }.get(freshness)
    body: dict[str, Any] = {
        "query": query,
        "max_results": count,
        "search_depth": str(params.get("search_depth") or "basic"),
        "topic": str(params.get("topic") or "general"),
        "include_answer": False,
        "include_raw_content": False,
    }
    if time_range:
        body["time_range"] = time_range
    for key in ("include", "exclude"):
        value = params.get(key)
        if isinstance(value, list) and value:
            body[f"{key}_domains"] = [str(item) for item in value]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                TAVILY_SEARCH_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
    except httpx.RequestError as exc:
        return {
            "query": query,
            "provider": "tavily",
            "results": [],
            "error": f"Tavily search request failed: {type(exc).__name__}",
        }
    if resp.status_code != 200:
        return {
            "query": query,
            "provider": "tavily",
            "results": [],
            "error": f"Tavily search failed: HTTP {resp.status_code}",
        }

    try:
        payload = resp.json()
    except ValueError:
        return {
            "query": query,
            "provider": "tavily",
            "results": [],
            "error": "Tavily search returned invalid JSON",
        }
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return {
            "query": query,
            "provider": "tavily",
            "results": [],
            "error": "Tavily search returned an invalid result schema",
        }
    results = [
        _tavily_result(item)
        for item in payload["results"]
        if isinstance(item, dict) and item.get("url")
    ]

    return {
        "query": query,
        "provider": "tavily",
        "freshness": freshness,
        "results": results[:count],
        "response_time": payload.get("response_time"),
        "request_id": payload.get("request_id"),
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
    # TAVILY_API_KEY is canonical. Keep the mixed-case spelling compatible with
    # existing local Windows .env files and case-sensitive deployment hosts.
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        api_key = next(
            (
                value.strip()
                for key, value in os.environ.items()
                if key.casefold() == "tavily_api_key" and value.strip()
            ),
            "",
        )
    if api_key:
        return await _tavily_search(params, api_key)
    return await _duckduckgo_search(params)


def create_web_search_tool() -> ToolDefinition:
    return ToolDefinition(
        name="web_search",
        description=(
            "Search the web for current, factual, or deep-research information. Uses Tavily "
            "Search API when TAVILY_API_KEY is configured, otherwise falls back to DuckDuckGo. "
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
                "topic": {
                    "type": "string",
                    "enum": ["general", "news", "finance"],
                    "default": "general",
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced", "fast", "ultra-fast"],
                    "default": "basic",
                },
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
