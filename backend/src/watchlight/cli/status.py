# 文件说明：本文件属于 命令行层。
# 主要职责：实现 status 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Status CLI — channel and session status."""

import typer

status_app = typer.Typer()


@status_app.callback(invoke_without_command=True)
def status(ctx: typer.Context) -> None:
    """Show channel and session status."""
    if ctx.invoked_subcommand is not None:
        return

    typer.echo("Watchlight Status\n")

    # Try to connect to running gateway
    import socket

    from watchlight.core.paths import DEFAULT_GATEWAY_PORT

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(("127.0.0.1", DEFAULT_GATEWAY_PORT))
    s.close()

    if result == 0:
        typer.echo(f"  Gateway: running on port {DEFAULT_GATEWAY_PORT}")
    else:
        typer.echo("  Gateway: not running")
        typer.echo("  Start with: watchlight gateway run")
