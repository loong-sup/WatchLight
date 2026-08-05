from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

import httpx

from watchlight.collector.errors import ErrorClassifier

USER_AGENT = "Watchlight/0.1 (+https://github.com/watchlight; public-change-monitor)"


@dataclass(frozen=True, slots=True)
class FetchResponse:
    url: str
    status_code: int
    text: str
    headers: dict[str, str]


class FetchClient(Protocol):
    async def fetch(self, url: str) -> FetchResponse: ...


def is_safe_public_url(url: str, *, resolve_dns: bool = True) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        return False
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        if not resolve_dns:
            return True
        try:
            addresses = [
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
            ]
        except OSError:
            return False
    return all(address.is_global for address in addresses)


class HttpxFetchClient:
    def __init__(self, *, timeout_seconds: float = 30, resolve_dns: bool = True) -> None:
        self.timeout_seconds = timeout_seconds
        self.resolve_dns = resolve_dns
        self.classifier = ErrorClassifier()

    async def fetch(self, url: str) -> FetchResponse:
        if not is_safe_public_url(url, resolve_dns=self.resolve_dns):
            raise PermissionError("blocked_non_public_url")
        delay = 5.0
        last_error: BaseException | None = None
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            for attempt in range(1, 4):
                try:
                    response = await client.get(url)
                    decision = self.classifier.classify(http_status=response.status_code)
                    if decision.retryable and attempt < decision.max_attempts:
                        retry_after = response.headers.get("Retry-After")
                        wait = (
                            float(retry_after)
                            if retry_after and retry_after.isdigit()
                            else delay
                        )
                        await asyncio.sleep(min(wait, 60))
                        delay = min(delay * 2, 60)
                        continue
                    return FetchResponse(
                        str(response.url),
                        response.status_code,
                        response.text,
                        dict(response.headers),
                    )
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt < 3:
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, 60)
                        continue
                    raise
        assert last_error is not None
        raise last_error
