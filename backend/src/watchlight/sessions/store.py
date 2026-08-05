# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 store 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""SessionStore — CRUD operations on sessions.json."""

import json
import time
from pathlib import Path
from typing import Any

from watchlight.contracts.session.entry import SessionEntry
from watchlight.sessions.paths import sessions_json_path
from watchlight.sessions.session_id import generate_session_id


class SessionStore:
    """Manages the sessions.json file."""

    def __init__(self, state_dir: Path, agent_id: str = "main") -> None:
        self.state_dir = state_dir
        self.agent_id = agent_id
        self._path = sessions_json_path(state_dir, agent_id)
        self._data: dict[str, SessionEntry] = {}

    def load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._data = {k: SessionEntry.model_validate(v) for k, v in raw.items()}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        raw = {
            k: json.loads(v.model_dump_json(exclude_none=True, by_alias=True))
            for k, v in self._data.items()
        }
        self._path.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def get(self, key: str) -> SessionEntry | None:
        return self._data.get(key)

    def list(self, limit: int | None = None, offset: int = 0) -> list[tuple[str, SessionEntry]]:
        items = sorted(self._data.items(), key=lambda x: x[1].updated_at, reverse=True)
        if offset:
            items = items[offset:]
        if limit:
            items = items[:limit]
        return items

    def create(
        self, key: str, label: str | None = None, channel: str | None = None
    ) -> SessionEntry:
        entry = SessionEntry.model_validate(
            {
                "sessionId": generate_session_id(),
                "updatedAt": int(time.time() * 1000),
                "label": label,
                "channel": channel,
            }
        )
        self._data[key] = entry
        return entry

    def update(self, key: str, patch: dict[str, Any]) -> SessionEntry | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        raw = json.loads(entry.model_dump_json(exclude_none=True, by_alias=True))
        raw.update(patch)
        raw["updatedAt"] = int(time.time() * 1000)
        self._data[key] = SessionEntry.model_validate(raw)
        return self._data[key]

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def reset(self, key: str) -> SessionEntry | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        new_entry = self.create(key, label=entry.label, channel=entry.channel)
        return new_entry

    @property
    def count(self) -> int:
        return len(self._data)
