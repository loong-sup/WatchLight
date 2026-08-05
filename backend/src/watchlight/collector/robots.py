from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from watchlight.collector.fetch import USER_AGENT

if TYPE_CHECKING:
    from watchlight.collector.fetch import FetchClient


class RobotsCache:
    def __init__(self, fetch_client: FetchClient) -> None:
        self.fetch_client = fetch_client
        self._cache: dict[str, RobotFileParser | None] = {}

    async def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._cache:
            try:
                response = await self.fetch_client.fetch(urljoin(origin, "/robots.txt"))
            except Exception:
                self._cache[origin] = None
            else:
                parser = RobotFileParser()
                parser.set_url(urljoin(origin, "/robots.txt"))
                parser.parse(response.text.splitlines())
                self._cache[origin] = parser
        cached = self._cache[origin]
        return True if cached is None else cached.can_fetch(USER_AGENT, url)
