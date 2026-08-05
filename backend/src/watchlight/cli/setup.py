# 文件说明：本文件属于 命令行层。
# 主要职责：实现 setup 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""CLI setup command — channel installation wizard."""

import typer

setup_app = typer.Typer()


@setup_app.command()
def setup(channel: str = typer.Argument(..., help="Channel to set up")) -> None:
    typer.echo(f"Setting up channel: {channel}")
    if channel == "feishu":
        app_id = typer.prompt("Feishu App ID")
        typer.prompt("Feishu App Secret", hide_input=True)
        typer.echo(f"Add to config:\n  channels.feishu.accounts.default.appId = {app_id}")
    elif channel == "telegram":
        token = typer.prompt("Telegram Bot Token", hide_input=True)
        typer.echo(f"Add to config:\n  channels.telegram.botToken = {token[:10]}...")
    else:
        typer.echo(f"No setup wizard for channel: {channel}")
