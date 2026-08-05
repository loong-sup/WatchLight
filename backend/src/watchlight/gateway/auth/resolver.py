# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 resolver 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Resolve gateway auth config."""

from watchlight.contracts.config.types_gateway import GatewayAuthConfig
from watchlight.contracts.config.types_watchlight import WatchlightConfig


def resolve_gateway_auth(config: WatchlightConfig) -> GatewayAuthConfig | None:
    if config.gateway and config.gateway.auth:
        return config.gateway.auth
    return None
