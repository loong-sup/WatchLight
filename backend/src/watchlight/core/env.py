# 文件说明：本文件属于 基础设施层。
# 主要职责：实现 env 相关能力。
# 阅读提示：提供日志、路径、错误等基础能力。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Environment variable utilities."""

import os
import shlex
from pathlib import Path


def is_truthy_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in ("1", "true", "yes", "on")


def normalize_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Return a normalized copy of environment variables."""
    raw = env if env is not None else dict(os.environ)
    result = dict(raw)
    # Normalize ZAI_API_KEY → Watchlight aliases
    aliases = {
        "ZAI_API_KEY": "WATCHLIGHT_API_KEY",
    }
    for src, dst in aliases.items():
        if src in result and dst not in result:
            result[dst] = result[src]
    return result


def get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def parse_env_assignment(line: str) -> tuple[str, str] | None:
    """Parse a simple KEY=VALUE or export KEY=VALUE line."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None

    key, _, raw_value = stripped.partition("=")
    key = key.strip()
    if not key.isidentifier():
        return None

    value = raw_value.strip()
    try:
        parts = shlex.split(value, comments=False, posix=True)
    except ValueError:
        parts = []
    if len(parts) == 1:
        value = parts[0]
    elif value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        value = value[1:-1]
    return key, value


def load_env_file(path: Path | str, *, override: bool = False) -> int:
    """Load simple environment assignments from a file into os.environ."""
    env_path = Path(path)
    if not env_path.exists():
        return 0

    loaded = 0
    for line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = parse_env_assignment(line)
        if parsed is None:
            continue
        key, value = parsed
        if override or key not in os.environ:
            os.environ[key] = value
            loaded += 1
    return loaded


def load_default_env_files(cwd: Path | str | None = None) -> list[Path]:
    """Load local .env files and legacy process.md files for local development."""
    base = Path(cwd or os.getcwd()).expanduser().resolve()
    candidates = [
        base / ".env",
        base.parent / ".env",
        base / "watchlight-py" / ".env",
        base.parent / "watchlight-py" / ".env",
        base / "process.md",
        base.parent / "process.md",
        base.parent.parent / "process.md",
    ]

    loaded: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        path = candidate.expanduser().resolve(strict=False)
        if path in seen:
            continue
        seen.add(path)
        if not path.exists():
            continue
        if load_env_file(path, override=False):
            loaded.append(path)
    return loaded
