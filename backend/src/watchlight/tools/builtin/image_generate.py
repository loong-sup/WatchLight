# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 image generate 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Image generation tool — placeholder for external API integration."""

from typing import Any

from watchlight.tools.types import ToolDefinition


async def _handler(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    prompt = params.get("prompt", "")
    return {"prompt": prompt, "note": "image_generate - needs provider integration (DALL-E, etc.)"}


def create_image_generate_tool() -> ToolDefinition:
    return ToolDefinition(
        name="image_generate",
        description="Generate an image from a text prompt",
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description"},
                "size": {"type": "string", "default": "1024x1024"},
            },
            "required": ["prompt"],
        },
        handler=_handler,
    )
