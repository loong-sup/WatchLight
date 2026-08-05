# 文件说明：本文件属于 命令行层。
# 主要职责：处理模型相关接口。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""CLI models command."""

import typer

models_app = typer.Typer()


@models_app.command("list")
def list_models() -> None:
    from watchlight.agents.providers.catalog import default_model_catalog

    for m in default_model_catalog():
        typer.echo(f"  {m['id']:30s} {m['provider']:15s} {m.get('label', '')}")
