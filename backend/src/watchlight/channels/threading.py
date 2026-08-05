# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 threading 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Thread/topic routing — map threads to sessions."""

from watchlight.core.logging import get_logger

log = get_logger("channel.threading")


class ThreadRouter:
    """Route thread/topic messages to appropriate sessions."""

    def __init__(self) -> None:
        self._bindings: dict[str, str] = {}  # thread_id → session_key

    def resolve(self, channel: str, conversation_id: str, thread_id: str | None) -> str:
        if thread_id:
            key = f"{channel}:{conversation_id}:{thread_id}"
            if key in self._bindings:
                return self._bindings[key]
            session_key = f"thread:{channel}:{thread_id}"
            self._bindings[key] = session_key
            return session_key
        return f"{channel}:{conversation_id}"

    def bind(self, channel: str, conversation_id: str, thread_id: str, session_key: str) -> None:
        key = f"{channel}:{conversation_id}:{thread_id}"
        self._bindings[key] = session_key
        log.info("thread_bound", thread_id=thread_id, session_key=session_key)
