# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：处理认证和 token 获取。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Provider auth resolution."""

import os


def resolve_api_key(provider_id: str, env: dict[str, str] | None = None) -> str | None:
    raw_env = env or dict(os.environ)
    key_map = {
        "anthropic": ["ANTHROPIC_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "dashscope": ["DASHSCOPE_API_KEY"],
    }
    for var in key_map.get(provider_id, []):
        if var in raw_env:
            return raw_env[var]
    return None
