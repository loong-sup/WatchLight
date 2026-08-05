# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 session key 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session key parsing and normalization."""


def normalize_session_key(key: str) -> str:
    return key.lower().strip()


def parse_session_key(key: str) -> tuple[str, str]:
    """Parse 'agent:<agentId>:<localKey>' → (agentId, localKey).
    If no prefix, returns ('main', key).
    """
    normalized = normalize_session_key(key)
    if normalized.startswith("agent:"):
        parts = normalized.split(":", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return "main", normalized


def build_session_key(agent_id: str, local_key: str) -> str:
    if agent_id == "main":
        return local_key
    return f"agent:{agent_id}:{local_key}"
