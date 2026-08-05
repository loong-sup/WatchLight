from __future__ import annotations

from enum import StrEnum


class ContentKind(StrEnum):
    TARGET = "target"
    LOGIN_WALL = "login_wall"
    CAPTCHA = "captcha"
    PAYWALL = "paywall"
    ERROR_PAGE = "error_page"


_MARKERS: tuple[tuple[ContentKind, tuple[str, ...]], ...] = (
    (ContentKind.CAPTCHA, ("captcha", "验证码", "人机验证", "verify you are human")),
    (ContentKind.LOGIN_WALL, ("请登录", "登录后查看", "sign in to continue", "login required")),
    (ContentKind.PAYWALL, ("订阅后阅读", "付费阅读全文", "subscribe to continue", "paywall")),
    (ContentKind.ERROR_PAGE, ("404 not found", "403 forbidden", "access denied")),
)


def classify(content: str, http_status: int) -> ContentKind:
    if http_status >= 400:
        return ContentKind.ERROR_PAGE
    lowered = content.lower()[:20000]
    for kind, markers in _MARKERS:
        if any(marker in lowered for marker in markers):
            return kind
    return ContentKind.TARGET
