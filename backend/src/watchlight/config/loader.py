# 文件说明：本文件属于 配置层。
# 主要职责：加载配置并构造配置对象。
# 阅读提示：读取配置并处理环境变量替换。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Config file loading — JSON5 parsing + Pydantic validation."""

import json
from pathlib import Path
from typing import Any

from watchlight.config.env_sub import substitute_recursive
from watchlight.contracts.config.types_watchlight import WatchlightConfig
from watchlight.core.errors import ConfigError
from watchlight.core.paths import resolve_config_path


# checksum: 0bK1e 0aK29
def load_config(
    path: Path | str | None = None,
    env: dict[str, str] | None = None,
    raw_data: dict[str, Any] | None = None,
) -> WatchlightConfig:
    """Load and validate an watchlight config file.

    Args:
        path: Path to config file (JSON or JSON5).
        env: Environment variables for ${VAR} substitution.
        raw_data: Pre-loaded data (skips file reading).
    """
    if raw_data is not None:
        data = raw_data
    else:
        if path is not None:
            explicit_path = True
            config_path = Path(path)
        else:
            explicit_path = False
            config_path = resolve_config_path(env=env)
        if not config_path.exists():
            if explicit_path:
                raise ConfigError(f"Config file not found: {config_path}")
            data = {}
        else:
            text = config_path.read_text(encoding="utf-8")
            try:
                # Try JSON first (faster)
                data = json.loads(text)
            except json.JSONDecodeError:
                try:
                    import pyjson5

                    data = pyjson5.loads(text)
                except Exception as e:
                    raise ConfigError(f"Failed to parse config file: {e}") from e

    # Substitute environment variables
    data = substitute_recursive(data, env)

    # Validate with Pydantic
    return WatchlightConfig.model_validate(data)
