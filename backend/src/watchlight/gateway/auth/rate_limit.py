# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 rate limit 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Auth rate limiting."""

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    max_attempts: int = 5
    window_ms: int = 60000
    lockout_ms: int = 300000
    _attempts: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    _locked: dict[str, float] = field(default_factory=dict)

    def check(self, client_ip: str) -> bool:
        """Returns True if the client is allowed, False if rate-limited."""
        now = time.time() * 1000
        if client_ip in self._locked:
            if now < self._locked[client_ip]:
                return False
            del self._locked[client_ip]

        window_start = now - self.window_ms
        self._attempts[client_ip] = [t for t in self._attempts[client_ip] if t > window_start]
        return len(self._attempts[client_ip]) < self.max_attempts

    def record_failure(self, client_ip: str) -> None:
        now = time.time() * 1000
        self._attempts[client_ip].append(now)
        if len(self._attempts[client_ip]) >= self.max_attempts:
            self._locked[client_ip] = now + self.lockout_ms
