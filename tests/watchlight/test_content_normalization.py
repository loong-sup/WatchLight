from pathlib import Path

from watchlight.collector.snapshot import normalize_content


def test_wordpress_css_and_script_content_are_removed() -> None:
    html = Path("fixtures/watchlight/sources/wordpress_css_v1.html").read_text(
        encoding="utf-8"
    )

    normalized = normalize_content(html)

    assert normalized == "小米汽车动态\n本轮页面正文没有发生变化。"
    assert "--wp--preset" not in normalized
    assert "themeVersion" not in normalized


def test_presentation_only_wordpress_change_is_stable() -> None:
    fixtures = Path("fixtures/watchlight/sources")
    before = normalize_content((fixtures / "wordpress_css_v1.html").read_text(encoding="utf-8"))
    after = normalize_content((fixtures / "wordpress_css_v2.html").read_text(encoding="utf-8"))

    assert before == after


def test_ignored_nodes_comments_entities_and_malformed_html() -> None:
    html = """
    <article><h2>Research &amp; Development</h2>
    <!-- hidden --><p>可读正文<strong>继续</article>
    <noscript>enable scripts</noscript><template>template payload</template>
    <svg><text>vector label</text></svg>
    """

    normalized = normalize_content(html)

    assert normalized == "Research & Development\n可读正文继续"


def test_plain_text_preserves_comparison_symbols_and_lines() -> None:
    content = "Model score: 3 < 5 and 8 > 2\n中文内容保持可读"

    assert normalize_content(content) == content
