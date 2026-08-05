# 文件说明：本文件属于 契约层。
# 主要职责：实现 types base 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Base enums and small config types."""

from enum import StrEnum


class LogLevel(StrEnum):
    SILENT = "silent"
    FATAL = "fatal"
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


class ConsoleStyle(StrEnum):
    PRETTY = "pretty"
    COMPACT = "compact"
    JSON = "json"


class SessionScope(StrEnum):
    PER_SENDER = "per-sender"
    GLOBAL = "global"


class DmScope(StrEnum):
    MAIN = "main"
    PER_PEER = "per-peer"
    PER_CHANNEL_PEER = "per-channel-peer"
    PER_ACCOUNT_CHANNEL_PEER = "per-account-channel-peer"


class TypingMode(StrEnum):
    NEVER = "never"
    INSTANT = "instant"
    THINKING = "thinking"
    MESSAGE = "message"


class GatewayBindMode(StrEnum):
    AUTO = "auto"
    LAN = "lan"
    LOOPBACK = "loopback"
    CUSTOM = "custom"
    TAILNET = "tailnet"


class GatewayAuthMode(StrEnum):
    NONE = "none"
    TOKEN = "token"
    PASSWORD = "password"
    TRUSTED_PROXY = "trusted-proxy"


class QueueMode(StrEnum):
    STEER = "steer"
    FOLLOWUP = "followup"
    COLLECT = "collect"
    QUEUE = "queue"
    INTERRUPT = "interrupt"


class UpdateChannel(StrEnum):
    STABLE = "stable"
    BETA = "beta"
    DEV = "dev"
