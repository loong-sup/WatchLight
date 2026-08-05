from __future__ import annotations

from watchlight.collector.content_guard import ContentKind, classify
from watchlight.collector.fetch import is_safe_public_url


def test_url_policy_blocks_local_and_metadata_addresses() -> None:
    assert not is_safe_public_url("http://127.0.0.1/private")
    assert not is_safe_public_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe_public_url("file:///etc/passwd")
    assert is_safe_public_url("https://example.com/page", resolve_dns=False)


def test_content_guard_rejects_login_captcha_and_paywall() -> None:
    assert classify("请登录后查看", 200) is ContentKind.LOGIN_WALL
    assert classify("Please complete CAPTCHA", 200) is ContentKind.CAPTCHA
    assert classify("Subscribe to continue", 200) is ContentKind.PAYWALL
    assert classify("actual article", 200) is ContentKind.TARGET
