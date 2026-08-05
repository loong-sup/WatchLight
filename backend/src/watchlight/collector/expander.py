from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class SourcePlan:
    url: str
    origin: str


class SearchProvider(Protocol):
    async def search(self, query: str, *, limit: int) -> list[str]: ...


class BuiltinSearchProvider:
    """Adapter around the Gateway's existing Bocha/DuckDuckGo search capability."""

    async def search(self, query: str, *, limit: int) -> list[str]:
        from watchlight.tools.builtin.web_search import create_web_search_tool

        tool = create_web_search_tool()
        if tool.handler is None:
            return []
        payload = await tool.handler({"query": query, "count": limit})
        if not isinstance(payload, dict):
            return []
        results = payload.get("results", [])
        return [
            str(item["url"])
            for item in results
            if isinstance(item, dict) and item.get("url")
        ]


class SourceExpander:
    def __init__(
        self, search_provider: SearchProvider | None = None, *, max_sources: int = 20
    ) -> None:
        self.search_provider = search_provider
        self.max_sources = max_sources

    async def expand(self, source_scope: dict[str, Any]) -> list[SourcePlan]:
        include = {str(item).lower() for item in source_scope.get("include_domains", [])}
        exclude = {str(item).lower() for item in source_scope.get("exclude_domains", [])}
        plans = [SourcePlan(str(url), "url") for url in source_scope.get("urls", [])]
        if self.search_provider:
            for keyword in source_scope.get("keywords", []):
                urls = await self.search_provider.search(str(keyword), limit=self.max_sources)
                plans.extend(SourcePlan(url, f"search:{keyword}") for url in urls)
        unique: dict[str, SourcePlan] = {}
        from urllib.parse import urlparse

        for plan in plans:
            host = (urlparse(plan.url).hostname or "").lower()
            if include and host not in include:
                continue
            if host in exclude:
                continue
            unique.setdefault(plan.url, plan)
            if len(unique) >= self.max_sources:
                break
        return list(unique.values())
