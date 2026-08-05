# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 depth 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Subagent depth limiting."""

MAX_SPAWN_DEPTH = 5


class MaxDepthExceededError(Exception):
    pass


def check_depth(current_depth: int) -> None:
    if current_depth >= MAX_SPAWN_DEPTH:
        raise MaxDepthExceededError(f"Maximum subagent spawn depth ({MAX_SPAWN_DEPTH}) exceeded")
