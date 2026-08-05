# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 modes 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Auth mode implementations."""

from watchlight.contracts.config.types_gateway import GatewayAuthConfig
from watchlight.core.errors import AuthError


def authenticate(auth_config: GatewayAuthConfig | None, provided: dict[str, str | None]) -> bool:
    """Validate authentication credentials against config."""
    if auth_config is None or auth_config.mode is None or auth_config.mode == "none":
        return True

    if auth_config.mode == "token":
        expected = auth_config.token
        given = provided.get("token")
        if not expected:
            return True
        if given != expected:
            raise AuthError("Invalid gateway token")
        return True

    if auth_config.mode == "password":
        expected = auth_config.password
        given = provided.get("password")
        if not expected:
            return True
        if given != expected:
            raise AuthError("Invalid gateway password")
        return True

    if auth_config.mode == "trusted-proxy":
        return True

    raise AuthError(f"Unknown auth mode: {auth_config.mode}")
