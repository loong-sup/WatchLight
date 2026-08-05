# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 pairing 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Channel pairing — first-contact verification."""

import json
from pathlib import Path
from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("channel.pairing")


class PairingManager:
    """Manage device/user pairing state."""

    def __init__(self, state_dir: Path) -> None:
        self._path = state_dir / "pairing.json"
        self._paired: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            self._paired = json.loads(self._path.read_text())

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._paired, indent=2) + "\n")

    def is_paired(self, channel: str, sender_id: str) -> bool:
        key = f"{channel}:{sender_id}"
        return key in self._paired

    def pair(self, channel: str, sender_id: str, metadata: dict[str, Any] | None = None) -> None:
        import time

        key = f"{channel}:{sender_id}"
        self._paired[key] = {"pairedAt": int(time.time() * 1000), **(metadata or {})}
        self._save()
        log.info("user_paired", channel=channel, sender=sender_id)

    def unpair(self, channel: str, sender_id: str) -> bool:
        key = f"{channel}:{sender_id}"
        if key in self._paired:
            del self._paired[key]
            self._save()
            return True
        return False
