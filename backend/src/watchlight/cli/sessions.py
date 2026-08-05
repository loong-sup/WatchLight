# 文件说明：本文件属于 命令行层。
# 主要职责：处理会话相关接口。
# 阅读提示：提供本地启动、诊断和管理命令。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""CLI sessions commands."""

import typer

from watchlight.core.paths import resolve_state_dir
from watchlight.sessions.store import SessionStore

sessions_app = typer.Typer()


@sessions_app.command("list")
def list_sessions(limit: int = typer.Option(20)) -> None:
    store = SessionStore(resolve_state_dir())
    store.load()
    for key, entry in store.list(limit=limit):
        tokens = entry.total_tokens or 0
        typer.echo(
            f"  {key:40s} {entry.channel or '-':10s} {entry.status or '-':8s} {tokens:>8d} tokens"
        )


@sessions_app.command("preview")
def preview(session_key: str = typer.Argument(...)) -> None:
    from watchlight.sessions.transcript import TranscriptManager

    store = SessionStore(resolve_state_dir())
    store.load()
    entry = store.get(session_key)
    if not entry:
        typer.echo(f"Session not found: {session_key}")
        raise typer.Exit(1)
    tm = TranscriptManager(resolve_state_dir())
    for msg in tm.read_raw(entry.session_id)[-10:]:
        role = msg.get("role", "?")
        content = str(msg.get("content", ""))[:200]
        typer.echo(f"  [{role}] {content}")


@sessions_app.command("delete")
def delete(session_key: str = typer.Argument(...)) -> None:
    store = SessionStore(resolve_state_dir())
    store.load()
    if store.delete(session_key):
        store.save()
        typer.echo(f"Deleted: {session_key}")
    else:
        typer.echo(f"Not found: {session_key}")


@sessions_app.command("compact")
def compact(session_key: str = typer.Argument(...)) -> None:
    typer.echo(f"Compacting {session_key}... (requires running gateway)")
