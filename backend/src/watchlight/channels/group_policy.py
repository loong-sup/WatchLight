# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 group policy 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Group policy — control bot behavior in group chats."""

from watchlight.core.logging import get_logger

log = get_logger("channel.group_policy")


class GroupPolicy:
    """Policy for group chat behavior."""

    def __init__(
        self,
        allowed_groups: list[str] | None = None,
        denied_groups: list[str] | None = None,
        session_mode: str = "per-sender",  # "shared" | "per-sender"
        admin_only: bool = False,
    ) -> None:
        self._allowed = set(allowed_groups) if allowed_groups else None
        self._denied = set(denied_groups) if denied_groups else set()
        self.session_mode = session_mode
        self.admin_only = admin_only

    def is_group_allowed(self, group_id: str) -> bool:
        if group_id in self._denied:
            return False
        if self._allowed is not None:
            return group_id in self._allowed
        return True

    def resolve_session_key(self, channel: str, group_id: str, sender_id: str) -> str:
        if self.session_mode == "shared":
            return f"group:{channel}:{group_id}"
        return f"group:{channel}:{group_id}:{sender_id}"
