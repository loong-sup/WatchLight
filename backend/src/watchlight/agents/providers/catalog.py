# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 catalog 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Model catalog."""


def default_model_catalog() -> list[dict[str, str]]:
    return [
        {"id": "claude-sonnet-4-6", "provider": "anthropic", "label": "Claude Sonnet 4.6"},
        {"id": "claude-opus-4-6", "provider": "anthropic", "label": "Claude Opus 4.6"},
        {"id": "gpt-4o", "provider": "openai", "label": "GPT-4o"},
        {"id": "qwen-max", "provider": "dashscope", "label": "Qwen Max"},
    ]
