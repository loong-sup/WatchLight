# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 replay 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Replay state tracking — detect side effects for safe replay."""

from dataclasses import dataclass

SIDE_EFFECT_TOOLS = {"bash", "write_file", "edit", "apply_patch", "sessions_send", "sessions_spawn"}


@dataclass
class ReplayState:
    replay_invalid: bool = False
    had_potential_side_effects: bool = False

    def observe_tool_call(self, tool_name: str) -> None:
        if tool_name in SIDE_EFFECT_TOOLS:
            self.had_potential_side_effects = True
            self.replay_invalid = True
