# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 auth rotation 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Auth profile rotation — cycle through API keys on failure."""

from dataclasses import dataclass

from watchlight.core.logging import get_logger

log = get_logger("agent.auth_rotation")


@dataclass
class AuthProfile:
    provider_id: str
    api_key: str
    label: str = ""


class AuthProfileRotator:
    """Rotate through auth profiles on auth/rate-limit errors."""

    def __init__(self, profiles: list[AuthProfile] | None = None) -> None:
        self._profiles = profiles or []
        self._index = 0
        self._overload_rotations = 0
        self._rate_limit_rotations = 0
        self.overload_rotation_limit = 1
        self.rate_limit_rotation_limit = 1

    @property
    def current(self) -> AuthProfile | None:
        if not self._profiles:
            return None
        return self._profiles[self._index % len(self._profiles)]

    @property
    def count(self) -> int:
        return len(self._profiles)

    def rotate(self, reason: str) -> bool:
        """Rotate to next profile. Returns False if limit reached for this reason."""
        if not self._profiles or len(self._profiles) <= 1:
            return False

        if reason == "overloaded":
            if self._overload_rotations >= self.overload_rotation_limit:
                return False
            self._overload_rotations += 1
        elif reason == "rate_limit":
            if self._rate_limit_rotations >= self.rate_limit_rotation_limit:
                return False
            self._rate_limit_rotations += 1

        old_idx = self._index
        self._index = (self._index + 1) % len(self._profiles)
        log.info(
            "auth_profile_rotated",
            reason=reason,
            from_idx=old_idx,
            to_idx=self._index,
            label=self._profiles[self._index].label,
        )
        return True

    def reset(self) -> None:
        self._index = 0
        self._overload_rotations = 0
        self._rate_limit_rotations = 0

    def max_iterations(self) -> int:
        """Calculate max retry iterations based on profile count."""
        base = 24
        per_profile = 8
        total = base + len(self._profiles) * per_profile
        return max(32, min(total, 160))
