# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：处理事件接收、解码和分发。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway event names."""

TICK = "tick"
SHUTDOWN = "shutdown"
SESSION_CHANGED = "sessions.changed"
AGENT_EVENT = "agent.event"
CHANNEL_STATUS = "channels.status"
