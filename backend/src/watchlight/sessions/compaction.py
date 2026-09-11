# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 compaction 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session compaction checkpoint store — persistent compaction history."""

import json
from dataclasses import asdict
from pathlib import Path

from watchlight.agents.runtime.embedded.compaction import CompactionCheckpoint
from watchlight.core.logging import get_logger

log = get_logger("sessions.compaction")


class CompactionStore:
    """Persistent store for compaction checkpoints per session."""

    def __init__(self, state_dir: Path, agent_id: str = "main") -> None:
        self._dir = state_dir / "agents" / agent_id / "compaction"

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.jsonl"

    def append(self, session_id: str, checkpoint: CompactionCheckpoint) -> None:
        """Append a compaction checkpoint to the session's history."""
        path = self._path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(checkpoint), ensure_ascii=False) + "\n")
        log.info("checkpoint_saved", session_id=session_id, version=checkpoint.version)

    def list_checkpoints(self, session_id: str) -> list[CompactionCheckpoint]:
        """Load all checkpoints for a session."""
        path = self._path(session_id)
        if not path.exists():
            return []
        checkpoints = []
        for line in path.read_text().strip().split("\n"):
            if line:
                data = json.loads(line)
                checkpoints.append(CompactionCheckpoint(**data))
        return checkpoints

    def latest(self, session_id: str) -> CompactionCheckpoint | None:
        """Get the most recent checkpoint."""
        cps = self.list_checkpoints(session_id)
        return cps[-1] if cps else None

    def count(self, session_id: str) -> int:
        """Number of compactions for a session."""
        return len(self.list_checkpoints(session_id))

    def clear(self, session_id: str) -> None:
        """Delete all persisted compaction checkpoints for a session."""
        path = self._path(session_id)
        if path.exists():
            path.unlink()
