# 文件说明：本文件属于 配置层。
# 主要职责：实现 env sub 相关能力。
# 阅读提示：读取配置并处理环境变量替换。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Environment variable substitution in config values."""

import os
import re
from typing import Any

from watchlight.core.errors import ConfigError

_ENV_PATTERN = re.compile(r"(?<!\$)\$\{([^}]+)\}")
_ESCAPED_PATTERN = re.compile(r"\$\$\{([^}]+)\}")


def env_substitute(value: str, env: dict[str, str] | None = None) -> str:
    """Replace ${VAR} with environment values. $${VAR} is escaped to ${VAR}."""
    raw_env = env if env is not None else dict(os.environ)

    # First, replace escaped $${VAR} with a placeholder
    placeholder = "\x00ESCAPED\x00"
    temp = _ESCAPED_PATTERN.sub(lambda m: placeholder + m.group(1) + "}", value)

    # Then substitute real ${VAR}
    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name not in raw_env:
            raise ConfigError(f"Missing environment variable: {var_name}")
        return raw_env[var_name]

    result = _ENV_PATTERN.sub(replacer, temp)

    # Restore escaped patterns as literal ${VAR}
    result = result.replace(placeholder, "${")
    return result


def substitute_recursive(data: Any, env: dict[str, str] | None = None) -> Any:
    """Recursively substitute ${VAR} in all string values."""
    if isinstance(data, str):
        return env_substitute(data, env)
    if isinstance(data, dict):
        return {k: substitute_recursive(v, env) for k, v in data.items()}
    if isinstance(data, list):
        return [substitute_recursive(item, env) for item in data]
    return data
