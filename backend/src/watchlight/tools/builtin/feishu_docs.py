# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 feishu docs 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""飞书云文档工具集合：封装文档读取、搜索、创建和正文写入。"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlparse

from watchlight.channels.feishu.docs import FeishuDocsClient, feishu_docs_write_enabled
from watchlight.tools.types import ToolDefinition

MAX_BLOCK_TEXT_CHARS = 1800
MAX_BLOCKS_PER_REQUEST = 50
# 匹配行内公式，支持 \( ... \) 和单美元符号 Markdown 语法两种常见写法。
INLINE_MATH_RE = re.compile(r"(\\\((.+?)\\\)|(?<!\\)\$([^\n$]+?)(?<!\\)\$)")

CODE_LANGUAGE_ENUMS = {
    "text": 1,
    "plain": 1,
    "plaintext": 1,
    "c": 12,
    "css": 17,
    "dockerfile": 19,
    "go": 20,
    "html": 21,
    "java": 22,
    "javascript": 23,
    "js": 23,
    "python": 40,
    "py": 40,
    "rust": 44,
    "shell": 46,
    "bash": 46,
    "sh": 46,
    "sql": 47,
    "typescript": 49,
    "ts": 49,
}

DOC_WRITE_VERBS = (
    "创建",
    "新建",
    "建一个",
    "建个",
    "生成",
    "写入",
    "写到",
    "整理到",
    "输出到",
    "create",
    "generate",
    "write",
)
DOC_TARGET_TERMS = ("飞书文档", "云文档", "文档", "docx", "doc")
FEISHU_DOCS_PROMPT_INSTRUCTIONS = (
    "Feishu docs creation rules:\n"
    "1. If the user explicitly asks to create, generate, write, or organize content into "
    "a 飞书文档, 云文档, 文档, docx, or doc, the next action must be a call to "
    "feishu_docs_create_with_content.\n"
    "2. Do not output the document body in chat before calling the tool.\n"
    "3. Put the document title in title and the complete final Markdown/plain-text body in "
    "content. The content must be ready to publish and must not contain placeholders such as "
    "URL_1, TBD, 待补充, 指标A, or 示例数据.\n"
    "4. If search/research tools were used first, still call feishu_docs_create_with_content "
    "after search is complete. Use the actual searched titles, URLs, snippets, summaries, and "
    "dates as citations or references instead of inventing source labels.\n"
    "5. After the tool returns, reply only with reply_text from the tool result. Do not repeat "
    "or summarize the document body."
)


def _client_from_env() -> FeishuDocsClient:
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError("FEISHU_APP_ID and FEISHU_APP_SECRET are required")
    return FeishuDocsClient(app_id, app_secret)


def _extract_docx_id(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    path = parsed.path if parsed.scheme else raw
    parts = [part for part in path.split("/") if part]
    for marker in ("docx", "doc"):
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    return raw


async def _api_handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    client = _client_from_env()
    method = str(params.get("method", "GET"))
    path = str(params.get("path", ""))
    query = params.get("query")
    body = params.get("body")
    if query is not None and not isinstance(query, dict):
        raise ValueError("query must be an object")
    if body is not None and not isinstance(body, dict | list):
        raise ValueError("body must be an object or array")
    return await client.request(
        method,
        path,
        query=query,
        body=body,
        write_enabled=feishu_docs_write_enabled(),
    )


async def _raw_content_handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    document_id = _extract_docx_id(str(params.get("document_id") or params.get("url") or ""))
    if not document_id:
        raise ValueError("document_id or url is required")
    client = _client_from_env()
    return await client.request(
        "GET",
        f"/docx/v1/documents/{document_id}/raw_content",
    )


async def _create_doc_handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    _ensure_explicit_feishu_doc_write_intent(context)
    title = str(params.get("title", ""))
    if not title:
        raise ValueError("title is required")
    body: dict[str, Any] = {"title": title}
    folder_token = params.get("folder_token")
    if isinstance(folder_token, str) and folder_token:
        body["folder_token"] = folder_token

    client = _client_from_env()
    return await client.request(
        "POST",
        "/docx/v1/documents",
        body=body,
        write_enabled=feishu_docs_write_enabled(),
    )


def _text_run(content: str) -> dict[str, Any]:
    return {"text_run": {"content": content}}


def _equation(content: str) -> dict[str, Any]:
    return {"equation": {"content": _clean_latex_formula(content)}}


def _clean_latex_formula(content: str) -> str:
    formula = content.strip()
    for start, end in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$")):
        has_wrapper = formula.startswith(start) and formula.endswith(end)
        if has_wrapper and len(formula) > len(start) + len(end):
            formula = formula[len(start) : -len(end)].strip()
            break
    return formula


def _text_elements_from_inline_math(content: str) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    cursor = 0
    for match in INLINE_MATH_RE.finditer(content):
        # 公式前后的普通文本要保留下来，匹配到的公式片段则转成飞书原生 equation 元素。
        if match.start() > cursor:
            elements.append(_text_run(content[cursor : match.start()]))
        formula = match.group(2) or match.group(3) or ""
        cleaned = _clean_latex_formula(formula)
        if cleaned:
            elements.append(_equation(cleaned))
        cursor = match.end()
    if cursor < len(content):
        elements.append(_text_run(content[cursor:]))
    return elements or [_text_run(content)]


def _element_length(element: dict[str, Any]) -> int:
    if "text_run" in element:
        return len(str(element["text_run"].get("content", "")))
    if "equation" in element:
        return len(str(element["equation"].get("content", "")))
    return 0


def _split_text_elements(
    elements: list[dict[str, Any]], max_chars: int = MAX_BLOCK_TEXT_CHARS
) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(current)
            current = []
            current_len = 0

    for element in elements:
        if "text_run" in element:
            # 长文本需要按飞书块限制切开，但相邻公式元素不能被拆坏。
            text = str(element["text_run"].get("content", ""))
            while text:
                remaining = max_chars - current_len
                if remaining <= 0:
                    flush()
                    remaining = max_chars
                piece = text[:remaining]
                current.append(_text_run(piece))
                current_len += len(piece)
                text = text[remaining:]
                if current_len >= max_chars:
                    flush()
            continue

        element_len = _element_length(element)
        if current and current_len + element_len > max_chars:
            flush()
        current.append(element)
        current_len += element_len
        if current_len >= max_chars:
            flush()

    flush()
    return chunks


def _rich_textual_block(
    block_type: int, key: str, elements: list[dict[str, Any]], **extra: Any
) -> dict[str, Any]:
    body: dict[str, Any] = {"elements": elements}
    body.update(extra)
    return {"block_type": block_type, key: body}


def _textual_block(
    block_type: int,
    key: str,
    content: str,
    *,
    parse_inline_math: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    elements = (
        _text_elements_from_inline_math(content) if parse_inline_math else [_text_run(content)]
    )
    return _rich_textual_block(block_type, key, elements, **extra)


def _split_text(content: str, max_chars: int = MAX_BLOCK_TEXT_CHARS) -> list[str]:
    text = content.strip()
    if not text:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        chunks.append(text[cursor : cursor + max_chars])
        cursor += max_chars
    return chunks


def _append_textual_blocks(
    blocks: list[dict[str, Any]],
    block_type: int,
    key: str,
    content: str,
    *,
    parse_inline_math: bool = True,
    **extra: Any,
) -> None:
    text = content.strip()
    if not text:
        return
    if not parse_inline_math:
        for text_chunk in _split_text(text):
            blocks.append(
                _textual_block(block_type, key, text_chunk, parse_inline_math=False, **extra)
            )
        return
    elements = _text_elements_from_inline_math(text)
    for element_chunk in _split_text_elements(elements):
        blocks.append(_rich_textual_block(block_type, key, element_chunk, **extra))


def _language_enum(language: str) -> int:
    return CODE_LANGUAGE_ENUMS.get(language.strip().lower(), 1)


def _has_explicit_doc_write_intent(message: str) -> bool:
    text = message.strip().lower()
    if not text:
        return False
    return any(term in text for term in DOC_TARGET_TERMS) and any(
        verb in text for verb in DOC_WRITE_VERBS
    )


def _ensure_explicit_feishu_doc_write_intent(context: Any = None) -> None:
    if getattr(context, "channel", None) != "feishu":
        return
    # 飞书是远程入口，写文档必须来自当前用户消息的明确意图，避免模型误触发写操作。
    user_message = getattr(context, "user_message", None)
    if isinstance(user_message, str) and _has_explicit_doc_write_intent(user_message):
        return
    raise RuntimeError(
        "当前飞书消息没有明确要求创建或写入文档，已阻止文档写入工具执行。"
    )


def _markdown_to_docx_blocks(markdown: str) -> list[dict[str, Any]]:
    """把保守的 Markdown/纯文本子集转换成飞书新版文档 block 列表。"""
    blocks: list[dict[str, Any]] = []
    paragraph: list[str] = []
    code_lines: list[str] = []
    formula_lines: list[str] = []
    code_language = ""
    in_code = False
    in_formula = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            # 连续段落行先合并再转换，避免模型输出的软换行被误拆成大量短块。
            _append_textual_blocks(blocks, 2, "text", "\n".join(paragraph))
            paragraph = []

    def flush_code() -> None:
        nonlocal code_lines, code_language
        content = "\n".join(code_lines).strip("\n")
        if content:
            for chunk in _split_text(content):
                blocks.append(
                    _textual_block(
                        14,
                        "code",
                        chunk,
                        parse_inline_math=False,
                        style={"language": _language_enum(code_language), "wrap": True},
                    )
                )
        code_lines = []
        code_language = ""

    def flush_formula() -> None:
        nonlocal formula_lines
        content = _clean_latex_formula("\n".join(formula_lines))
        if content:
            # 块级公式在飞书里用一个 text block 包裹 equation 元素，保证公式能渲染。
            blocks.append(_rich_textual_block(2, "text", [_equation(content)]))
        formula_lines = []

    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                code_language = stripped[3:].strip()
                in_code = True
            continue

        if in_code:
            code_lines.append(raw_line)
            continue

        if in_formula:
            if stripped.endswith("$$"):
                formula_lines.append(stripped[:-2])
                flush_formula()
                in_formula = False
            elif stripped == "\\]":
                flush_formula()
                in_formula = False
            else:
                formula_lines.append(raw_line)
            continue

        if stripped.startswith("$$"):
            flush_paragraph()
            rest = stripped[2:]
            if rest.endswith("$$") and len(rest) > 2:
                formula_lines.append(rest[:-2])
                flush_formula()
            else:
                formula_lines.append(rest)
                in_formula = True
            continue

        if stripped == "\\[":
            flush_paragraph()
            in_formula = True
            continue

        if not stripped:
            flush_paragraph()
            continue

        if stripped in {"---", "***", "___"}:
            flush_paragraph()
            blocks.append({"block_type": 22, "divider": {}})
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            _append_textual_blocks(blocks, 2 + level, f"heading{level}", heading.group(2))
            continue

        todo = re.match(r"^- \[([ xX])\]\s+(.+)$", stripped)
        if todo:
            flush_paragraph()
            done = todo.group(1).lower() == "x"
            _append_textual_blocks(blocks, 17, "todo", todo.group(2), style={"done": done})
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            _append_textual_blocks(blocks, 12, "bullet", bullet.group(1))
            continue

        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if ordered:
            flush_paragraph()
            _append_textual_blocks(blocks, 13, "ordered", ordered.group(1))
            continue

        quote = re.match(r"^>\s?(.+)$", stripped)
        if quote:
            flush_paragraph()
            _append_textual_blocks(blocks, 15, "quote", quote.group(1))
            continue

        paragraph.append(stripped)

    if in_code:
        flush_code()
    if in_formula:
        flush_formula()
    flush_paragraph()
    return blocks


def _ensure_feishu_ok(result: dict[str, Any], operation: str) -> None:
    status = int(result.get("status") or 0)
    payload = result.get("json") if isinstance(result.get("json"), dict) else {}
    code = payload.get("code") if isinstance(payload, dict) else None
    if status < 200 or status >= 300 or code not in (None, 0):
        msg = payload.get("msg") if isinstance(payload, dict) else ""
        raise RuntimeError(f"{operation} failed: status={status} code={code} msg={msg}")


def _extract_document_payload(result: dict[str, Any]) -> tuple[str, str]:
    raw_payload = result.get("json")
    payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
    raw_data = payload.get("data")
    data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
    raw_document = data.get("document")
    document: dict[str, Any] = raw_document if isinstance(raw_document, dict) else data
    document_id = (
        document.get("document_id")
        or document.get("token")
        or data.get("document_id")
        or data.get("token")
        or ""
    )
    url = document.get("url") or data.get("url") or ""
    if not document_id:
        raise RuntimeError(f"create document succeeded but no document id was returned: {payload}")
    return str(document_id), str(url)


def _document_url_from_env(document_id: str) -> str:
    base_url = (
        os.environ.get("FEISHU_DOCS_BASE_URL")
        or os.environ.get("FEISHU_TENANT_DOCS_BASE_URL")
        or ""
    ).strip()
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/docx/{document_id}"


def _chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


async def _create_with_content_handler(
    params: dict[str, Any], context: Any = None
) -> dict[str, Any]:
    _ensure_explicit_feishu_doc_write_intent(context)
    title = str(params.get("title", "")).strip()
    content = str(params.get("content", "")).strip()
    if not title:
        raise ValueError("title is required")
    if not content:
        raise ValueError("content is required")

    body: dict[str, Any] = {"title": title}
    folder_token = params.get("folder_token")
    if isinstance(folder_token, str) and folder_token:
        body["folder_token"] = folder_token

    client = _client_from_env()
    write_enabled = feishu_docs_write_enabled()
    create_result = await client.request(
        "POST",
        "/docx/v1/documents",
        body=body,
        write_enabled=write_enabled,
    )
    _ensure_feishu_ok(create_result, "create document")
    document_id, document_url = _extract_document_payload(create_result)

    blocks = _markdown_to_docx_blocks(content)
    for block_batch in _chunks(blocks, MAX_BLOCKS_PER_REQUEST):
        # 飞书一次追加子块数量有限，长文档必须分批写入，避免单次请求过大失败。
        append_result = await client.request(
            "POST",
            f"/docx/v1/documents/{document_id}/blocks/{document_id}/children",
            query={"document_revision_id": "-1"},
            body={"children": block_batch, "index": -1},
            write_enabled=write_enabled,
        )
        _ensure_feishu_ok(append_result, "append document blocks")

    sender_id = getattr(context, "sender_id", None) if context is not None else None
    collaborator_added = False
    collaborator_error = ""
    if isinstance(sender_id, str) and sender_id:
        try:
            # 加协作者只是便利用途；分享失败不应影响文档本身创建成功。
            collaborator_result = await client.request(
                "POST",
                f"/drive/v1/permissions/{document_id}/members",
                query={"type": "docx", "need_notification": "false"},
                body={"member_type": "openid", "member_id": sender_id, "perm": "edit"},
                write_enabled=write_enabled,
            )
            _ensure_feishu_ok(collaborator_result, "add document collaborator")
            collaborator_added = True
        except Exception as exc:
            collaborator_error = str(exc)

    url = document_url or _document_url_from_env(document_id)
    if url:
        reply_text = f"已创建飞书文档：《{title}》\n链接：{url}"
        link_status = "ready"
    else:
        reply_text = (
            f"已创建飞书文档：《{title}》\n"
            f"文档 ID：{document_id}\n"
            "当前未配置 FEISHU_DOCS_BASE_URL，无法拼出可点击链接；"
            "已尝试把你加入协作者，可在飞书云文档中搜索标题打开。"
        )
        link_status = "missing_tenant_domain"

    return {
        "document_id": document_id,
        "url": url,
        "title": title,
        "blocks_created": len(blocks),
        "collaborator_added": collaborator_added,
        "collaborator_error": collaborator_error,
        "reply_text": reply_text,
        "link_status": link_status,
        "access_hint": (
            "If link_status is missing_tenant_domain, set FEISHU_DOCS_BASE_URL to "
            "the tenant Feishu domain, e.g. https://example.feishu.cn."
        ),
    }


async def _search_handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    search_key = str(params.get("search_key") or params.get("query") or "")
    if not search_key:
        raise ValueError("search_key is required")
    body: dict[str, Any] = {
        "search_key": search_key,
        "count": int(params.get("count", 10)),
        "offset": int(params.get("offset", 0)),
    }
    docs_types = params.get("docs_types")
    if isinstance(docs_types, list) and docs_types:
        body["docs_types"] = docs_types

    client = _client_from_env()
    return await client.request(
        "POST",
        "/suite/docs-api/search/object",
        body=body,
        write_enabled=feishu_docs_write_enabled(),
    )


async def _list_folder_handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    query: dict[str, Any] = {
        "page_size": int(params.get("page_size", 50)),
    }
    for key in ("folder_token", "page_token", "order_by", "direction"):
        value = params.get(key)
        if isinstance(value, str) and value:
            query[key] = value

    client = _client_from_env()
    return await client.request("GET", "/drive/v1/files", query=query)


def create_feishu_docs_api_tool() -> ToolDefinition:
    return ToolDefinition(
        name="feishu_docs_api",
        description=(
            "Call any Feishu cloud-docs OpenAPI path under docx, doc, drive, wiki, "
            "sheets, bitable, mindnote, slides, or suite docs search."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST", "PATCH", "PUT", "DELETE"]},
                "path": {
                    "type": "string",
                    "description": "Feishu OpenAPI path, e.g. /docx/v1/documents/{id}",
                },
                "query": {"type": "object", "additionalProperties": True},
                "body": {
                    "oneOf": [
                        {"type": "object", "additionalProperties": True},
                        {"type": "array"},
                    ],
                },
            },
            "required": ["method", "path"],
        },
        handler=_api_handler,
    )


def create_feishu_docs_raw_content_tool() -> ToolDefinition:
    return ToolDefinition(
        name="feishu_docs_raw_content",
        description="Get plain text content from a Feishu docx document.",
        input_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "url": {"type": "string"},
            },
        },
        handler=_raw_content_handler,
    )


def create_feishu_docs_create_tool() -> ToolDefinition:
    return ToolDefinition(
        name="feishu_docs_create",
        description=(
            "Create an empty Feishu docx document only. If the user asks to write generated "
            "content into a document, do not use this tool; use feishu_docs_create_with_content."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "folder_token": {"type": "string"},
            },
            "required": ["title"],
        },
        handler=_create_doc_handler,
    )


def create_feishu_docs_create_with_content_tool() -> ToolDefinition:
    return ToolDefinition(
        name="feishu_docs_create_with_content",
        description=(
            "Required tool for requests like 创建/新建/生成/写入/整理到飞书文档、云文档或文档. "
            "Create a Feishu docx document and write Markdown or plain text content into it. "
            "If research/search tools were used first, this tool must still be called afterward "
            "to create the requested document. "
            "Before calling this tool, do not output the document body in chat. Put the complete "
            "generated document body in the content parameter, using real source titles and URLs "
            "when research was performed. Do not pass placeholder text. After success, reply only "
            "with the returned reply_text and do not repeat or summarize the document body. "
            "Requires WATCHLIGHT_FEISHU_DOCS_WRITE_ENABLED=true."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title."},
                "content": {
                    "type": "string",
                    "description": (
                        "Complete Markdown or plain text content to write into the document. "
                        "Must be final content without placeholders such as URL_1, TBD, 待补充, "
                        "指标A, or 示例数据."
                    ),
                },
                "folder_token": {
                    "type": "string",
                    "description": "Optional Feishu Drive folder token.",
                },
            },
            "required": ["title", "content"],
        },
        prompt_instructions=FEISHU_DOCS_PROMPT_INSTRUCTIONS,
        handler=_create_with_content_handler,
    )


def create_feishu_docs_search_tool() -> ToolDefinition:
    return ToolDefinition(
        name="feishu_docs_search",
        description="Search Feishu cloud documents by keyword.",
        input_schema={
            "type": "object",
            "properties": {
                "search_key": {"type": "string"},
                "query": {"type": "string"},
                "count": {"type": "integer", "default": 10},
                "offset": {"type": "integer", "default": 0},
                "docs_types": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=_search_handler,
    )


def create_feishu_docs_list_folder_tool() -> ToolDefinition:
    return ToolDefinition(
        name="feishu_docs_list_folder",
        description="List files in a Feishu Drive folder.",
        input_schema={
            "type": "object",
            "properties": {
                "folder_token": {"type": "string"},
                "page_size": {"type": "integer", "default": 50},
                "page_token": {"type": "string"},
                "order_by": {"type": "string"},
                "direction": {"type": "string"},
            },
        },
        handler=_list_folder_handler,
    )
