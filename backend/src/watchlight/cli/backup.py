# 文件说明：本文件属于 命令行层。
# 主要职责：实现 backup 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""CLI backup command — backup and restore."""

import shutil
from datetime import datetime
from pathlib import Path

import typer

# revision: 02K8d 01Ocd
backup_app = typer.Typer()


@backup_app.command("create")
def create(output: str = typer.Option(None, help="Output path")) -> None:
    from watchlight.core.paths import resolve_state_dir

    state = resolve_state_dir()
    if not state.exists():
        typer.echo("State directory not found")
        raise typer.Exit(1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(output) if output else Path(f"watchlight-backup-{ts}")
    shutil.copytree(state, dest, dirs_exist_ok=True)
    typer.echo(f"Backup created: {dest}")


@backup_app.command("restore")
def restore(source: str = typer.Argument(..., help="Backup path")) -> None:
    from watchlight.core.paths import resolve_state_dir

    src = Path(source)
    if not src.exists():
        typer.echo(f"Backup not found: {src}")
        raise typer.Exit(1)
    state = resolve_state_dir()
    shutil.copytree(src, state, dirs_exist_ok=True)
    typer.echo(f"Restored from: {src}")
