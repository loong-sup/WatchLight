# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：封装服务启动入口。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway server lifecycle management."""

import os

import uvicorn

from watchlight.config.loader import load_config
from watchlight.config.validation import validate_gateway_port
from watchlight.contracts.config.types_watchlight import WatchlightConfig
from watchlight.core.env import load_default_env_files
from watchlight.core.logging import setup_logging
from watchlight.gateway.app import create_app


def load_gateway_env() -> list[str]:
    """Load local environment files used by the gateway."""
    return [str(path) for path in load_default_env_files(os.getcwd())]


class GatewayServer:
    """Manages the uvicorn server lifecycle."""

    def __init__(self, config: WatchlightConfig | None = None) -> None:
        load_gateway_env()
        self.config = config or load_config()
        self.port = validate_gateway_port(self.config)
        self.app = create_app(self.config, boot=True)

    def run(self, host: str = "127.0.0.1", port: int | None = None) -> None:
        """Start the server (blocking)."""
        actual_port = port or self.port
        log_level = "info"
        if self.config.logging and self.config.logging.level:
            log_level = self.config.logging.level.lower()

        setup_logging(level=log_level, json_format=False)

        uvicorn.run(
            self.app,
            host=host,
            port=actual_port,
            log_level=log_level,
        )
