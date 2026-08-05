# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 ref 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Model reference parsing."""


def parse_model_ref(ref: str) -> tuple[str | None, str]:
    """Parse 'provider:model' → (provider, model). Plain model → (None, model)."""
    if ":" in ref:
        provider, model = ref.split(":", 1)
        return provider, model
    return None, ref
