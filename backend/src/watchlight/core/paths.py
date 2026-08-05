# 文件说明：本文件属于 基础设施层。
# 主要职责：实现 paths 相关能力。
# 阅读提示：提供日志、路径、错误等基础能力。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Path resolution for Watchlight state, config, and session directories."""

import os
from pathlib import Path

DEFAULT_STATE_DIR_NAME = ".watchlight"
LEGACY_STATE_DIR_NAME = ".clawdbot"
DEFAULT_CONFIG_FILENAME = "watchlight.json"
LEGACY_CONFIG_FILENAME = "clawdbot.json"
DEFAULT_GATEWAY_PORT = 18789


def resolve_state_dir(env: dict[str, str] | None = None) -> Path:
    """Resolve the state directory (~/.watchlight by default)."""
    raw_env = env if env is not None else dict(os.environ)

    # Explicit override
    if explicit := raw_env.get("WATCHLIGHT_STATE_DIR"):
        return Path(explicit).expanduser().resolve()

    home = Path(raw_env.get("HOME", Path.home()))

    # Default path
    default_path = home / DEFAULT_STATE_DIR_NAME
    if default_path.exists():
        return default_path

    # Legacy fallback
    legacy_path = home / LEGACY_STATE_DIR_NAME
    if legacy_path.exists():
        return legacy_path

    # Create default
    return default_path


def resolve_config_path(state_dir: Path | None = None, env: dict[str, str] | None = None) -> Path:
    """Resolve the config file path."""
    raw_env = env if env is not None else dict(os.environ)

    # Explicit override
    if explicit := raw_env.get("WATCHLIGHT_CONFIG_PATH"):
        return Path(explicit).expanduser().resolve()

    if state_dir is None:
        state_dir = resolve_state_dir(raw_env)

    # Default
    default_path = state_dir / DEFAULT_CONFIG_FILENAME
    if default_path.exists():
        return default_path

    # Legacy
    legacy_path = state_dir / LEGACY_CONFIG_FILENAME
    if legacy_path.exists():
        return legacy_path

    return default_path


def resolve_sessions_dir(state_dir: Path, agent_id: str = "main") -> Path:
    """Resolve the sessions directory for an agent."""
    return state_dir / "agents" / agent_id


def resolve_credentials_dir(state_dir: Path) -> Path:
    """Resolve the credentials directory."""
    return state_dir / "credentials"
