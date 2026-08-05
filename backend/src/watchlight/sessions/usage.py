# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 usage 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Token usage tracking."""

from watchlight.contracts.session.entry import SessionEntry


def get_usage_summary(entry: SessionEntry) -> dict[str, int]:
    return {
        "inputTokens": entry.input_tokens or 0,
        "outputTokens": entry.output_tokens or 0,
        "totalTokens": entry.total_tokens or 0,
    }
