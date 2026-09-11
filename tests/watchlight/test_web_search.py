from __future__ import annotations

import pytest
from watchlight.collector.expander import BuiltinSearchProvider
from watchlight.tools.builtin.web_search import TAVILY_SEARCH_URL, create_web_search_tool


@pytest.mark.asyncio
async def test_tavily_search_normalizes_results(monkeypatch, httpx_mock) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    httpx_mock.add_response(
        method="POST",
        url=TAVILY_SEARCH_URL,
        json={
            "results": [
                {
                    "title": "小米澎程发布新动态",
                    "url": "https://example.com/news/1",
                    "content": "澎程产品线公布了最新进展。",
                    "published_date": "2026-08-28",
                }
            ],
            "response_time": 0.42,
            "request_id": "request-1",
        },
    )

    tool = create_web_search_tool()
    assert tool.handler is not None
    result = await tool.handler(
        {
            "query": "小米公司的澎程汽车",
            "count": 5,
            "freshness": "oneWeek",
            "topic": "news",
        }
    )

    assert result["provider"] == "tavily"
    assert result["results"] == [
        {
            "title": "小米澎程发布新动态",
            "url": "https://example.com/news/1",
            "snippet": "澎程产品线公布了最新进展。",
            "summary": "澎程产品线公布了最新进展。",
            "site_name": "example.com",
            "date_published": "2026-08-28",
        }
    ]
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == "Bearer test-key"
    assert b'"time_range":"week"' in request.content
    assert b'"topic":"news"' in request.content


@pytest.mark.asyncio
async def test_tavily_http_error_is_not_reported_as_empty_success(
    monkeypatch, httpx_mock
) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    httpx_mock.add_response(method="POST", url=TAVILY_SEARCH_URL, status_code=403)

    tool = create_web_search_tool()
    assert tool.handler is not None
    result = await tool.handler({"query": "小米澎程"})

    assert result["results"] == []
    assert result["error"] == "Tavily search failed: HTTP 403"


@pytest.mark.asyncio
async def test_collector_search_provider_raises_on_search_api_error(
    monkeypatch, httpx_mock
) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    httpx_mock.add_response(method="POST", url=TAVILY_SEARCH_URL, status_code=429)

    with pytest.raises(RuntimeError, match="Tavily search failed: HTTP 429"):
        await BuiltinSearchProvider().search("小米澎程", limit=5)


@pytest.mark.asyncio
async def test_mixed_case_tavily_key_remains_compatible(monkeypatch, httpx_mock) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("Tavily_API_KEY", "mixed-case-key")
    httpx_mock.add_response(method="POST", url=TAVILY_SEARCH_URL, json={"results": []})

    tool = create_web_search_tool()
    assert tool.handler is not None
    result = await tool.handler({"query": "小米澎程"})

    assert result["provider"] == "tavily"
