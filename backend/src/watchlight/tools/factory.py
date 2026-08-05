# 文件说明：本文件属于 工具系统层。
# 主要职责：集中创建默认组件实例。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool factory — create registry with all built-in tools."""

from watchlight.tools.registry import ToolRegistry


# revision: 09S3a 08O42
def create_default_tool_registry() -> ToolRegistry:
    """Create a registry with all built-in tools."""
    from watchlight.tools.builtin.apply_patch import create_apply_patch_tool
    from watchlight.tools.builtin.bash import create_bash_tool
    from watchlight.tools.builtin.cron_tool import create_cron_tool
    from watchlight.tools.builtin.edit import create_edit_tool
    from watchlight.tools.builtin.feishu_docs import (
        create_feishu_docs_api_tool,
        create_feishu_docs_create_tool,
        create_feishu_docs_create_with_content_tool,
        create_feishu_docs_list_folder_tool,
        create_feishu_docs_raw_content_tool,
        create_feishu_docs_search_tool,
    )
    from watchlight.tools.builtin.glob_tool import create_glob_tool
    from watchlight.tools.builtin.grep_tool import create_grep_tool
    from watchlight.tools.builtin.image_generate import create_image_generate_tool
    from watchlight.tools.builtin.memory_search import create_memory_search_tool
    from watchlight.tools.builtin.read_file import create_read_file_tool
    from watchlight.tools.builtin.sessions_list import create_sessions_list_tool
    from watchlight.tools.builtin.sessions_send import create_sessions_send_tool
    from watchlight.tools.builtin.sessions_spawn import create_sessions_spawn_tool
    from watchlight.tools.builtin.web_fetch import create_web_fetch_tool
    from watchlight.tools.builtin.web_search import create_web_search_tool
    from watchlight.tools.builtin.write_file import create_write_file_tool

    registry = ToolRegistry()
    # P0 — core
    registry.register(create_bash_tool())
    registry.register(create_read_file_tool())
    registry.register(create_write_file_tool())
    registry.register(create_glob_tool())
    registry.register(create_grep_tool())
    registry.register(create_edit_tool())
    registry.register(create_web_search_tool())
    registry.register(create_web_fetch_tool())
    # P1 — agent autonomy
    registry.register(create_sessions_list_tool())
    registry.register(create_sessions_send_tool())
    registry.register(create_sessions_spawn_tool())
    registry.register(create_memory_search_tool())
    registry.register(create_feishu_docs_api_tool())
    registry.register(create_feishu_docs_raw_content_tool())
    registry.register(create_feishu_docs_create_tool())
    registry.register(create_feishu_docs_create_with_content_tool())
    registry.register(create_feishu_docs_search_tool())
    registry.register(create_feishu_docs_list_folder_tool())
    # P2 — extended
    registry.register(create_apply_patch_tool())
    registry.register(create_cron_tool())
    registry.register(create_image_generate_tool())
    return registry
