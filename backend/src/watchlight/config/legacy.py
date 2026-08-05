# 文件说明：本文件属于 配置层。
# 主要职责：实现 legacy 相关能力。
# 阅读提示：读取配置并处理环境变量替换。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Legacy config migration — .clawdbot → .watchlight."""

from pathlib import Path

from watchlight.core.paths import (
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_STATE_DIR_NAME,
    LEGACY_CONFIG_FILENAME,
    LEGACY_STATE_DIR_NAME,
)


def detect_legacy_state_dir(home: Path) -> Path | None:
    """Check if a legacy .clawdbot directory exists."""
    legacy = home / LEGACY_STATE_DIR_NAME
    if legacy.exists() and not (home / DEFAULT_STATE_DIR_NAME).exists():
        return legacy
    return None


def detect_legacy_config(state_dir: Path) -> Path | None:
    """Check if a legacy config file exists."""
    legacy = state_dir / LEGACY_CONFIG_FILENAME
    if legacy.exists() and not (state_dir / DEFAULT_CONFIG_FILENAME).exists():
        return legacy
    return None
