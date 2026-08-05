# 文件说明：本文件属于 命令行层。
# 主要职责：实现 gateway 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway CLI commands."""

import typer

from watchlight.core.paths import DEFAULT_GATEWAY_PORT

gateway_app = typer.Typer()


@gateway_app.command("run")
def run(
    port: int = typer.Option(DEFAULT_GATEWAY_PORT, help="Gateway port"),
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    config_path: str = typer.Option(None, "--config", help="Config file path"),
    log_level: str = typer.Option("info", "--log-level", help="Log level"),
) -> None:
    """Start the watchlight gateway server."""
    from watchlight.config.loader import load_config
    from watchlight.gateway.server import GatewayServer, load_gateway_env

    load_gateway_env()
    config = load_config(path=config_path) if config_path else load_config()
    server = GatewayServer(config=config)
    typer.echo(f"Starting Watchlight Gateway on {host}:{port}")
    server.run(host=host, port=port)
