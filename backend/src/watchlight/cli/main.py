# 文件说明：本文件属于 命令行层。
# 主要职责：实现 main 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Watchlight CLI — main entry point."""

import typer

from watchlight.cli.backup import backup_app
from watchlight.cli.config_cmd import config_app
from watchlight.cli.doctor import doctor_app
from watchlight.cli.gateway import gateway_app
from watchlight.cli.logs import logs_app
from watchlight.cli.models import models_app
from watchlight.cli.onboard import onboard_app
from watchlight.cli.sessions import sessions_app
from watchlight.cli.setup import setup_app
from watchlight.cli.status import status_app

app = typer.Typer(name="Watchlight", help="Watchlight — Multi-channel AI Gateway")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("Watchlight v0.1.0 — use --help for commands")


app.add_typer(gateway_app, name="gateway", help="Gateway server management")
app.add_typer(config_app, name="config", help="Configuration management")
app.add_typer(sessions_app, name="sessions", help="Session management")
app.add_typer(models_app, name="models", help="Model information")
app.add_typer(doctor_app, name="doctor", help="Diagnostics")
app.add_typer(status_app, name="status", help="Status information")
app.add_typer(setup_app, name="setup", help="Channel setup wizard")
app.add_typer(onboard_app, name="onboard", help="First-time setup")
app.add_typer(logs_app, name="logs", help="Log management")
app.add_typer(backup_app, name="backup", help="Backup and restore")


if __name__ == "__main__":
    app()
