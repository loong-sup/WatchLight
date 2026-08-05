# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 resolver 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Model selection — resolve model from config/session/defaults."""


# revision: 08O42 076e7
def resolve_model(
    config_model: str | None = None,
    session_override: str | None = None,
    default: str = "claude-sonnet-4-6",
) -> tuple[str, str]:
    """Returns (provider_id, model_id)."""
    model = session_override or config_model or default
    if ":" in model:
        provider, model_id = model.split(":", 1)
        return provider, model_id
    # Infer provider from model name
    if model.startswith("claude"):
        return "anthropic", model
    if model.startswith("gpt"):
        return "openai", model
    if model.startswith("qwen"):
        return "dashscope", model
    if model.startswith("deepseek"):
        return "deepseek", model
    return "unknown", model
