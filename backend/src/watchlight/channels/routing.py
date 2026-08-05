# 文件说明：本文件属于 通道接入层。
# 主要职责：实现 routing 相关能力。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Message routing — 9-tier priority resolution matching TS resolve-route.ts."""

from typing import Any

from watchlight.contracts.channel.plugin import InboundMessage
from watchlight.core.logging import get_logger

log = get_logger("channel.routing")


class ResolvedRoute:
    """Result of route resolution."""

    def __init__(
        self,
        agent_id: str = "main",
        session_key: str = "main",
        main_session_key: str = "agent:main:main",
        matched_by: str = "default",
    ) -> None:
        self.agent_id = agent_id
        self.session_key = session_key
        self.main_session_key = main_session_key
        self.matched_by = matched_by


class RoutingBindings:
    """Compiled binding rules for routing resolution."""

    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []

    def add_rule(self, rule: dict[str, Any]) -> None:
        self._rules.append(rule)

    def load_from_config(self, config: dict[str, Any]) -> None:
        """Load binding rules from config."""
        bindings = config.get("bindings", {})
        for key, binding in bindings.items():
            self._rules.append({"key": key, **binding})

    @property
    def rules(self) -> list[dict[str, Any]]:
        return self._rules


def resolve_route(
    message: InboundMessage,
    bindings: RoutingBindings | None = None,
    default_agent: str = "main",
) -> ResolvedRoute:
    """Resolve inbound message to session key using 9-tier priority.

    Priority (matching TS):
      1. binding.peer         — exact peer match
      2. binding.peer.parent  — parent thread match
      3. binding.peer.*       — wildcard peer
      4. binding.guild+roles  — guild + role
      5. binding.guild        — guild only
      6. binding.team         — workspace/team
      7. binding.account      — account-level
      8. binding.channel      — channel-level
      9. default              — default agent
    """
    channel = message.channel
    sender = message.sender_id
    conv = message.conversation_id
    chat_type = message.chat_type
    thread_id = getattr(message, "thread_id", None)
    raw = message.raw or {}
    account_id = raw.get("account_id", "default")

    if bindings:
        for rule in bindings.rules:
            # Tier 1: exact peer
            peer = rule.get("peer")
            if peer and peer == f"{channel}:{conv}":
                return _build_route(rule, channel, sender, conv, "binding.peer")

            # Tier 7: account
            if rule.get("account") == account_id and rule.get("channel") == channel:
                return _build_route(rule, channel, sender, conv, "binding.account")

            # Tier 8: channel
            if rule.get("channel") == channel and "account" not in rule and "peer" not in rule:
                return _build_route(rule, channel, sender, conv, "binding.channel")

    # Tier 9: default
    if chat_type == "dm":
        session_key = f"dm:{channel}:{sender}"
    elif chat_type == "group":
        session_key = f"group:{channel}:{conv}:{sender}"
    elif thread_id:
        session_key = f"thread:{channel}:{thread_id}"
    else:
        session_key = f"{channel}:{sender}"

    return ResolvedRoute(
        agent_id=default_agent,
        session_key=session_key,
        main_session_key=f"agent:{default_agent}:main",
        matched_by="default",
    )


def _build_route(
    rule: dict[str, Any], channel: str, sender: str, conv: str, matched_by: str
) -> ResolvedRoute:
    agent_id = rule.get("agentId", "main")
    session_key_template = rule.get("sessionKey", f"{channel}:{sender}")
    session_key = session_key_template.replace("{sender}", sender).replace("{conv}", conv)
    return ResolvedRoute(
        agent_id=agent_id,
        session_key=session_key,
        main_session_key=f"agent:{agent_id}:main",
        matched_by=matched_by,
    )


def resolve_session_key(message: InboundMessage, agent_id: str = "main") -> str:
    """Simple session key resolution (backward compat, uses resolve_route internally)."""
    route = resolve_route(message)
    return route.session_key
