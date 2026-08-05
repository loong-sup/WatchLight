# 文件说明：本文件属于 配置层。
# 主要职责：实现 io 相关能力。
# 阅读提示：读取配置并处理环境变量替换。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Config file I/O — read/write with backup rotation."""

import json
import shutil
from pathlib import Path
from typing import Any

from watchlight.core.errors import ConfigError


def read_config_file(path: Path) -> dict[str, Any]:
    """Read a config file as a dict."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        result: dict[str, Any] = json.loads(text)
        return result
    except json.JSONDecodeError:
        try:
            import pyjson5

            result2: dict[str, Any] = pyjson5.loads(text)
            return result2
        except Exception as e:
            raise ConfigError(f"Failed to parse {path}: {e}") from e


def write_config_file(path: Path, data: dict[str, Any], backup: bool = True) -> None:
    """Write config data to a JSON file, optionally backing up the old one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        backup_path = path.with_suffix(".json.bak")
        shutil.copy2(path, backup_path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
