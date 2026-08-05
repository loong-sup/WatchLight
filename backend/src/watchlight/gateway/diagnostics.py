# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 diagnostics 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway diagnostics — structured health checks."""

import socket
import time
from dataclasses import dataclass, field
from typing import Any

from watchlight.contracts.config.types_watchlight import WatchlightConfig
from watchlight.core.logging import get_logger
from watchlight.core.paths import DEFAULT_GATEWAY_PORT

log = get_logger("gateway.diagnostics")


@dataclass
class DiagnosticIssue:
    category: str  # "config" | "provider" | "channel" | "session" | "network"
    severity: str  # "error" | "warning" | "info"
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiagnosticReport:
    issues: list[DiagnosticIssue] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issues": [
                {
                    "category": i.category,
                    "severity": i.severity,
                    "message": i.message,
                    "details": i.details,
                }
                for i in self.issues
            ],
            "checksRun": self.checks_run,
            "checksPassed": self.checks_passed,
            "timestamp": self.timestamp,
            "hasErrors": self.has_errors,
        }


class GatewayDiagnostics:
    def __init__(self, config: WatchlightConfig, runtime: Any = None) -> None:
        self._config = config
        self._runtime = runtime

    def check_config(self) -> list[DiagnosticIssue]:
        issues: list[DiagnosticIssue] = []
        if not self._config.gateway:
            issues.append(DiagnosticIssue("config", "warning", "No gateway config section"))
        if self._config.gateway and not self._config.gateway.auth:
            issues.append(DiagnosticIssue("config", "warning", "No gateway auth configured"))
        return issues

    def check_providers(self) -> list[DiagnosticIssue]:
        issues: list[DiagnosticIssue] = []
        if self._runtime:
            providers = self._runtime.provider_registry.list_ids()
            if not providers:
                issues.append(DiagnosticIssue("provider", "error", "No providers registered"))
            else:
                for p in providers:
                    issues.append(DiagnosticIssue("provider", "info", f"Provider registered: {p}"))
        return issues

    def check_channels(self) -> list[DiagnosticIssue]:
        issues: list[DiagnosticIssue] = []
        if self._runtime:
            channels = self._runtime.channel_registry.list_ids()
            if not channels:
                issues.append(DiagnosticIssue("channel", "warning", "No channels registered"))
            else:
                for ch in channels:
                    issues.append(DiagnosticIssue("channel", "info", f"Channel registered: {ch}"))
        return issues

    def check_sessions(self) -> list[DiagnosticIssue]:
        issues: list[DiagnosticIssue] = []
        if self._runtime:
            count = self._runtime.session_store.count
            issues.append(DiagnosticIssue("session", "info", f"Sessions loaded: {count}"))
        return issues

    def check_network(self) -> list[DiagnosticIssue]:
        issues: list[DiagnosticIssue] = []
        port = DEFAULT_GATEWAY_PORT
        if self._config.gateway and self._config.gateway.port:
            port = self._config.gateway.port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            s.close()
            if result == 0:
                issues.append(
                    DiagnosticIssue("network", "info", f"Port {port} in use (gateway running)")
                )
            else:
                issues.append(DiagnosticIssue("network", "info", f"Port {port} available"))
        except Exception:
            issues.append(DiagnosticIssue("network", "info", f"Port {port} check skipped"))
        return issues

    def run_all(self) -> DiagnosticReport:
        report = DiagnosticReport()
        checks = [
            self.check_config,
            self.check_providers,
            self.check_channels,
            self.check_sessions,
            self.check_network,
        ]
        for check in checks:
            report.checks_run += 1
            issues = check()
            if not any(i.severity == "error" for i in issues):
                report.checks_passed += 1
            report.issues.extend(issues)
        return report
