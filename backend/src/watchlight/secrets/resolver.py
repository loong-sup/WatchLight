# 文件说明：本文件属于 密钥管理层。
# 主要职责：实现 resolver 相关能力。
# 阅读提示：解析和存储敏感配置。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""SecretRef resolution — resolve secrets from env, file, or exec."""

import os
import subprocess
from pathlib import Path
from typing import Any

from watchlight.core.errors import ConfigError


def resolve_secret(ref: dict[str, Any] | str, env: dict[str, str] | None = None) -> str:
    """Resolve a secret reference to its value.

    Supports:
    - Plain string: returned as-is
    - {"env": "VAR_NAME"}: read from environment
    - {"file": "/path/to/secret"}: read from file
    - {"exec": "command"}: execute command and use stdout
    """
    if isinstance(ref, str):
        return ref

    raw_env = env if env is not None else dict(os.environ)

    if "env" in ref:
        var_name = ref["env"]
        if var_name not in raw_env:
            raise ConfigError(f"Secret env var not found: {var_name}")
        return raw_env[var_name]

    if "file" in ref:
        path = Path(ref["file"]).expanduser()
        if not path.exists():
            raise ConfigError(f"Secret file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    if "exec" in ref:
        try:
            result = subprocess.run(
                ref["exec"], shell=True, capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise ConfigError(f"Secret exec failed: {result.stderr}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired as e:
            raise ConfigError("Secret exec timed out") from e

    raise ConfigError(f"Unknown secret ref type: {ref}")
