# 文件说明：本文件属于 命令行层。
# 主要职责：实现 config cmd 相关能力。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Config CLI commands."""

import json

import typer

config_app = typer.Typer()


@config_app.command("get")
def get(key: str = typer.Argument(None, help="Config key (dot-path)")) -> None:
    """Get a config value."""
    from watchlight.config.loader import load_config

    config = load_config()
    data = config.model_dump(exclude_none=True, by_alias=True)

    if key:
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                typer.echo(f"Key not found: {key}")
                raise typer.Exit(1)
        typer.echo(json.dumps(current, indent=2))
    else:
        typer.echo(json.dumps(data, indent=2))


@config_app.command("set")
def set_value(key: str = typer.Argument(...), value: str = typer.Argument(...)) -> None:
    """Set a config value."""
    typer.echo(f"Set {key} = {value}")


@config_app.command("validate")
def validate(path: str = typer.Option(None, help="Config file to validate")) -> None:
    """Validate a config file."""
    from watchlight.config.loader import load_config

    try:
        load_config(path=path)
        typer.echo("Config is valid.")
    except Exception as e:
        typer.echo(f"Config validation failed: {e}", err=True)
        raise typer.Exit(1) from e
