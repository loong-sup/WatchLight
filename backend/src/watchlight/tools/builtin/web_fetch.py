# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 web fetch 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""网页读取工具：打开公开 URL，并提取可给模型阅读的正文和基础元信息。"""

from __future__ import annotations

import ipaddress
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from watchlight.tools.types import ToolDefinition

DEFAULT_MAX_CHARS = 50000
MAX_ALLOWED_CHARS = 200000
MAX_LINKS = 40
TEXT_CONTENT_TYPES = (
    "text/",
    "application/json",
    "application/xml",
    "application/xhtml+xml",
    "application/rss+xml",
    "application/atom+xml",
)
BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
WEB_FETCH_PROMPT_INSTRUCTIONS = (
    "Use web_fetch after web_search when the user asks for deep research, paper analysis, "
    "source-backed reports, or a Feishu document based on current external material. Prefer "
    "fetching official, primary, paper, documentation, GitHub, arXiv, or publisher URLs from "
    "the search results before writing. Use fetched title, description, final_url, text, and "
    "links as evidence. If the fetched page is unavailable, paywalled, blocked, or only a "
    "secondary summary, say that limitation clearly in the final document. Do not invent "
    "citations or leave placeholders."
)


def _clamp_max_chars(value: Any) -> int:
    try:
        max_chars = int(value)
    except (TypeError, ValueError):
        max_chars = DEFAULT_MAX_CHARS
    return max(1000, min(max_chars, MAX_ALLOWED_CHARS))


def _validate_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must start with http:// or https://")
    if not parsed.hostname:
        raise ValueError("url must include a hostname")
    hostname = parsed.hostname.lower()
    if hostname in BLOCKED_HOSTS or hostname.endswith(".local"):
        raise ValueError("local hostnames are not allowed")
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return parsed.geturl()
    # 远程聊天消息不能变成本机内网探测工具，因此禁止访问私网、回环和保留地址。
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise ValueError(
            "private, loopback, link-local, reserved, or multicast IPs are not allowed"
        )
    return parsed.geturl()


def _is_text_content_type(content_type: str) -> bool:
    normalized = content_type.lower().split(";", 1)[0].strip()
    return any(normalized.startswith(prefix) for prefix in TEXT_CONTENT_TYPES)


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


class ReadableHTMLParser(HTMLParser):
    """轻量 HTML 解析器，不引入额外依赖，提取标题、描述、正文和可选链接。"""

    def __init__(self, base_url: str, extract_links: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.extract_links = extract_links
        self.title = ""
        self.description = ""
        self.text_parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._skip_depth = 0
        self._capture_title = False
        self._capture_anchor = False
        self._anchor_href = ""
        self._anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas"}:
            # 脚本、样式和图形内容不适合给模型阅读，跳过后只保留正文附近的文字。
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._capture_title = True
            return
        if tag == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.description = self.description or _collapse_ws(attr_map.get("content", ""))
            return
        if tag == "a" and self.extract_links:
            href = attr_map.get("href", "").strip()
            if href:
                # 页面里的相对链接先转成绝对链接，模型后续才能直接继续 fetch。
                self._capture_anchor = True
                self._anchor_href = urljoin(self.base_url, href)
                self._anchor_parts = []
            return
        if tag in {"p", "br", "div", "section", "article", "header", "footer", "li"}:
            self.text_parts.append("\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.text_parts.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._capture_title = False
            self.title = _collapse_ws(self.title)
            return
        if tag == "a" and self._capture_anchor:
            label = _collapse_ws("".join(self._anchor_parts))
            if label and len(self.links) < MAX_LINKS:
                self.links.append({"text": label, "url": self._anchor_href})
            self._capture_anchor = False
            self._anchor_href = ""
            self._anchor_parts = []
            return
        if tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._capture_title:
            self.title += data
            return
        if self._capture_anchor:
            self._anchor_parts.append(data)
        text = _collapse_ws(data)
        if text:
            self.text_parts.append(text)
            self.text_parts.append(" ")

    def readable_text(self) -> str:
        text = "".join(self.text_parts)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def extract_text(html: str) -> str:
    """兼容旧调用的 HTML 到纯文本提取入口。"""
    parser = ReadableHTMLParser("", extract_links=False)
    parser.feed(html)
    parser.close()
    return parser.readable_text()[:DEFAULT_MAX_CHARS]


def _extract_html(html: str, base_url: str, max_chars: int, extract_links: bool) -> dict[str, Any]:
    parser = ReadableHTMLParser(base_url, extract_links=extract_links)
    parser.feed(html)
    parser.close()
    text = parser.readable_text()
    return {
        "title": parser.title,
        "description": parser.description,
        "content": text[:max_chars],
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
        "content_length": len(text),
        "links": parser.links if extract_links else [],
    }


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    raw_url = str(params.get("url") or "")
    raw = bool(params.get("raw", False))
    extract_links = bool(params.get("extract_links", params.get("links", False)))
    max_chars = _clamp_max_chars(params.get("max_chars", params.get("max_content_length")))

    try:
        url = _validate_url(raw_url)
    except ValueError as e:
        return {"ok": False, "error": str(e), "url": raw_url}

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; Watchlight/0.1; "
                        "+https://github.com/Watchlight/Watchlight)"
                    ),
                    "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,"
                    "application/json;q=0.9,*/*;q=0.8",
                },
            )
    except Exception as e:
        return {"ok": False, "error": f"Fetch failed: {e}", "url": raw_url}

    content_type = resp.headers.get("content-type", "")
    final_url = str(resp.url)
    result: dict[str, Any] = {
        "ok": 200 <= resp.status_code < 400,
        "url": raw_url,
        "final_url": final_url,
        "status": resp.status_code,
        "content_type": content_type,
    }
    if not _is_text_content_type(content_type):
        # 这个工具只负责文本网页读取，二进制下载需要单独的文件沙箱设计。
        result.update(
            {
                "content": "",
                "text": "",
                "truncated": False,
                "content_length": 0,
                "error": f"Unsupported non-text content type: {content_type or 'unknown'}",
            }
        )
        return result

    if "text/html" in content_type.lower() and not raw:
        # 默认提取可读正文；raw 模式主要用于调试或确实需要查看网页源码时。
        result.update(_extract_html(resp.text, final_url, max_chars, extract_links))
        return result

    text = resp.text
    result.update(
        {
            "title": "",
            "description": "",
            "content": text[:max_chars],
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
            "content_length": len(text),
            "links": [],
        }
    )
    return result


def create_web_fetch_tool() -> ToolDefinition:
    return ToolDefinition(
        name="web_fetch",
        description=(
            "Fetch a public HTTP/HTTPS URL and return readable page text plus metadata. Use this "
            "after web_search to inspect primary sources, papers, docs, GitHub pages, or official "
            "announcements before producing source-backed analysis. No API key is required."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Public http:// or https:// URL to fetch.",
                },
                "raw": {
                    "type": "boolean",
                    "default": False,
                    "description": "Return raw text/HTML instead of readable HTML extraction.",
                },
                "max_chars": {
                    "type": "integer",
                    "default": DEFAULT_MAX_CHARS,
                    "description": "Maximum characters to return, clamped to 1,000-200,000.",
                },
                "extract_links": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include up to 40 links discovered on the page.",
                },
            },
            "required": ["url"],
        },
        prompt_instructions=WEB_FETCH_PROMPT_INSTRUCTIONS,
        handler=_handler,
    )
