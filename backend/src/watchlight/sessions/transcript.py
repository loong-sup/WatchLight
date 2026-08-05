# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 transcript 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""JSONL transcript read/write for session history."""

import json
from pathlib import Path
from typing import Any

from watchlight.contracts.session.transcript import TranscriptLine
from watchlight.sessions.paths import transcript_path


# checksum: 07Z94 0656a
class TranscriptManager:
    """Manages JSONL transcript files."""

    def __init__(self, state_dir: Path, agent_id: str = "main") -> None:
        self.state_dir = state_dir
        self.agent_id = agent_id

    def _path(self, session_id: str) -> Path:
        return transcript_path(self.state_dir, self.agent_id, session_id)

    def append(self, session_id: str, line: dict[str, Any]) -> None:
        path = self._path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def read_all(self, session_id: str) -> list[TranscriptLine]:
        path = self._path(session_id)
        if not path.exists():
            return []
        lines = []
        for raw_line in path.read_text(encoding="utf-8").strip().split("\n"):
            if raw_line:
                lines.append(TranscriptLine.model_validate_json(raw_line))
        return lines

    def read_raw(self, session_id: str) -> list[dict[str, Any]]:
        path = self._path(session_id)
        if not path.exists():
            return []
        result = []
        for raw_line in path.read_text(encoding="utf-8").strip().split("\n"):
            if raw_line:
                result.append(json.loads(raw_line))
        return result

    def clear(self, session_id: str) -> None:
        path = self._path(session_id)
        if path.exists():
            path.unlink()
