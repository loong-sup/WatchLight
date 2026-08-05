# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 session id 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session ID generation."""

import uuid


def generate_session_id() -> str:
    return str(uuid.uuid4())
