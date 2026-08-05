# 文件说明：本文件属于 命令行层。
# 主要职责：实现 logs 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""CLI logs command — real-time log tailing."""

import time

import typer

logs_app = typer.Typer()


@logs_app.command("tail")
def tail(
    lines: int = typer.Option(50), follow: bool = typer.Option(False, "--follow", "-f")
) -> None:
    from watchlight.core.paths import resolve_state_dir

    log_dir = resolve_state_dir() / "logs"
    if not log_dir.exists():
        typer.echo("No logs directory found")
        return
    log_files = sorted(log_dir.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not log_files:
        typer.echo("No log files found")
        return
    path = log_files[0]
    all_lines = path.read_text().strip().split("\n")
    for line in all_lines[-lines:]:
        typer.echo(line)
    if follow:
        typer.echo("--- following (Ctrl+C to stop) ---")
        try:
            with open(path) as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        typer.echo(line.rstrip())
                    else:
                        time.sleep(0.5)
        except KeyboardInterrupt:
            pass
