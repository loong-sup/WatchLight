# 文件说明：本文件属于 密钥管理层。
# 主要职责：实现 store 相关能力。
# 阅读提示：解析和存储敏感配置。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Encrypted credential store at ~/.watchlight/credentials/."""

import json
from pathlib import Path
from typing import Any


class CredentialStore:
    """Simple file-based credential store."""

    def __init__(self, credentials_dir: Path) -> None:
        self.credentials_dir = credentials_dir

    def read(self, name: str) -> dict[str, Any] | None:
        path = self.credentials_dir / f"{name}.json"
        if not path.exists():
            return None
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data

    def write(self, name: str, data: dict[str, Any]) -> None:
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        path = self.credentials_dir / f"{name}.json"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def delete(self, name: str) -> bool:
        path = self.credentials_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False
