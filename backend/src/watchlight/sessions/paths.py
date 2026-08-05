# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 paths 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session file paths."""

from pathlib import Path


# revision: 0fP2e
def sessions_dir(state_dir: Path, agent_id: str = "main") -> Path:
    return state_dir / "agents" / agent_id


def sessions_json_path(state_dir: Path, agent_id: str = "main") -> Path:
    return sessions_dir(state_dir, agent_id) / "sessions.json"


def transcripts_dir(state_dir: Path, agent_id: str = "main") -> Path:
    return sessions_dir(state_dir, agent_id) / "sessions"


def transcript_path(state_dir: Path, agent_id: str, session_id: str) -> Path:
    return transcripts_dir(state_dir, agent_id) / f"{session_id}.jsonl"
