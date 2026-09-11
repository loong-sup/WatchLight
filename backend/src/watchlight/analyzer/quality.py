from __future__ import annotations

import re
from dataclasses import dataclass

_CSS_CUSTOM_PROPERTY = re.compile(r"--[a-zA-Z0-9_-]+\s*:")
_CSS_DECLARATION = re.compile(
    r"\b[a-zA-Z-]+\s*:\s*(?:#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|var\(|"
    r"linear-gradient\(|-?\d+(?:\.\d+)?(?:px|rem|em|vh|vw|%)\b)"
)
_JAVASCRIPT_TOKEN = re.compile(
    r"\b(?:const|let|var|function|return|class|new|throw|await|async)\b|"
    r"(?:window|document|console)\.[a-zA-Z_$]",
    re.IGNORECASE,
)
_MARKUP_TAG = re.compile(r"</?[a-zA-Z][^>]{0,200}>")
_SERIALIZED_KEY = re.compile(r"""["'][^"']{1,80}["']\s*:""")


@dataclass(frozen=True, slots=True)
class ContentQuality:
    safe: bool
    reason: str | None = None


def classify_content_quality(text: str) -> ContentQuality:
    value = text.strip()
    if not value:
        return ContentQuality(False, "empty")

    length = len(value)
    braces = value.count("{") + value.count("}")
    semicolons = value.count(";")
    structural_ratio = sum(value.count(char) for char in "{};<>[]") / length

    custom_properties = len(_CSS_CUSTOM_PROPERTY.findall(value))
    css_declarations = len(_CSS_DECLARATION.findall(value))
    if custom_properties >= 2 or (
        css_declarations >= 3 and braces >= 2 and semicolons >= 3
    ):
        return ContentQuality(False, "css")

    javascript_tokens = len(_JAVASCRIPT_TOKEN.findall(value))
    if javascript_tokens >= 3 and braces >= 2 and semicolons >= 2:
        return ContentQuality(False, "javascript")

    markup_tags = len(_MARKUP_TAG.findall(value))
    if markup_tags >= 3 and structural_ratio >= 0.04:
        return ContentQuality(False, "markup")

    serialized_keys = len(_SERIALIZED_KEY.findall(value))
    if serialized_keys >= 3 and value[:1] in {"{", "["} and structural_ratio >= 0.04:
        return ContentQuality(False, "serialized")

    if length >= 200 and structural_ratio >= 0.12:
        return ContentQuality(False, "structure_dominant")
    return ContentQuality(True)
