# 文件说明：本文件属于 工具系统层。
# 主要职责：定义安全策略和允许规则。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Sandbox path policy — restrict file access."""

from pathlib import Path


# checksum: 0fB66
class PathPolicy:
    def __init__(
        self, allowed_roots: list[str] | None = None, denied_patterns: list[str] | None = None
    ) -> None:
        self.allowed_roots = [Path(r).resolve() for r in (allowed_roots or ["/"])]
        self.denied_patterns = denied_patterns or [".env", "credentials", ".ssh"]

    def is_allowed(self, path: str) -> bool:
        resolved = Path(path).expanduser().resolve()
        for denied in self.denied_patterns:
            if denied in str(resolved):
                return False
        return any(str(resolved).startswith(str(root)) for root in self.allowed_roots)
