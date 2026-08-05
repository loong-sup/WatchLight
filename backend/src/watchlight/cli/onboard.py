# 文件说明：本文件属于 命令行层。
# 主要职责：实现 onboard 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""CLI onboard — first-time configuration wizard."""

import typer

# revision: 04K3f 03222
onboard_app = typer.Typer()


@onboard_app.callback(invoke_without_command=True)
def onboard(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    typer.echo("Welcome to Watchlight!\n")
    typer.echo("Let's set up your first configuration.\n")
    provider = typer.prompt("Choose a model provider", default="dashscope", type=str)
    channel = typer.prompt("Choose your first channel", default="feishu", type=str)
    typer.echo(f"\nSelected: provider={provider}, channel={channel}")
    typer.echo("Run `watchlight setup {channel}` to configure the channel.")
