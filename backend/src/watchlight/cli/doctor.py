# 文件说明：本文件属于 命令行层。
# 主要职责：实现 doctor 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Doctor CLI — diagnostics."""

import socket

import typer

from watchlight.core.paths import DEFAULT_GATEWAY_PORT

doctor_app = typer.Typer()


@doctor_app.callback(invoke_without_command=True)
def doctor(ctx: typer.Context) -> None:
    """Run diagnostic checks."""
    if ctx.invoked_subcommand is not None:
        return

    typer.echo("Watchlight Doctor — running checks...\n")
    issues = 0

    # 1. Config check
    try:
        from watchlight.config.loader import load_config

        load_config()
        typer.echo("  ✓ Config file: valid")
    except Exception as e:
        typer.echo(f"  ✗ Config file: {e}")
        issues += 1

    # 2. Port check
    port = DEFAULT_GATEWAY_PORT
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        if result == 0:
            typer.echo(f"  ✓ Gateway port {port}: in use (gateway running)")
        else:
            typer.echo(f"  ✓ Gateway port {port}: available")
    except Exception:
        typer.echo(f"  ✓ Gateway port {port}: available")

    # 3. State dir check
    from watchlight.core.paths import resolve_state_dir

    state_dir = resolve_state_dir()
    if state_dir.exists():
        typer.echo(f"  ✓ State directory: {state_dir}")
    else:
        typer.echo(f"  ⚠ State directory not found: {state_dir}")

    typer.echo(f"\n{'No issues found.' if issues == 0 else f'{issues} issue(s) found.'}")
