from __future__ import annotations

from typing import TYPE_CHECKING, Any

from watchlight.scheduler.presentation import task_to_view
from watchlight.scheduler.service import TaskService
from watchlight.tools.types import ToolContext, ToolDefinition

if TYPE_CHECKING:
    from watchlight.storage.store import Store


def create_watch_tasks_list_tool(store: Store) -> ToolDefinition:
    tasks = TaskService(store)

    async def handler(params: dict[str, Any], context: ToolContext | None = None) -> dict[str, Any]:
        del params
        if context is None or not context.user_id:
            raise ValueError("authenticated Watchlight user identity is required")
        views = [task_to_view(task) for task in tasks.list(context.user_id)]
        return {"count": len(views), "tasks": views}

    return ToolDefinition(
        name="watch_tasks_list",
        description="List the authenticated user's persisted Watchlight tasks",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        prompt_instructions=(
            "Use this tool when the user asks whether a Watchlight task exists or asks to "
            "review/list their tasks. Never use sessions_list or memory_search as a substitute. "
            "If this tool fails, report the query failure instead of claiming there are no tasks."
        ),
        handler=handler,
    )
