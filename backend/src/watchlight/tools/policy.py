# 文件说明：本文件属于 工具系统层。
# 主要职责：定义安全策略和允许规则。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool policy — profile-based access control."""

PROFILES: dict[str, dict[str, list[str] | None]] = {
    "minimal": {
        "allow": ["read_file", "glob", "grep", "web_search", "web_fetch"],
        "deny": None,
    },
    "coding": {
        "allow": None,  # All tools allowed
        "deny": ["sessions_spawn"],  # Except subagent spawning
    },
    "messaging": {
        "allow": [
            "read_file",
            "web_search",
            "web_fetch",
            "sessions_list",
            "sessions_send",
            "memory_search",
            "watch_tasks_list",
            "feishu_docs_api",
            "feishu_docs_raw_content",
            "feishu_docs_create",
            "feishu_docs_create_with_content",
            "feishu_docs_search",
            "feishu_docs_list_folder",
        ],
        "deny": ["bash", "write_file", "edit", "apply_patch"],
    },
    "full": {
        "allow": None,
        "deny": None,
    },
}


class ToolPolicy:
    def __init__(
        self,
        allow: list[str] | None = None,
        deny: list[str] | None = None,
        profile: str | None = None,
    ) -> None:
        if profile and profile in PROFILES:
            p = PROFILES[profile]
            self._allow = set(p["allow"]) if p["allow"] else None
            self._deny = set(p["deny"]) if p["deny"] else set()
        else:
            self._allow = set(allow) if allow else None
            self._deny = set(deny) if deny else set()

    def is_allowed(self, tool_name: str) -> bool:
        if tool_name in self._deny:
            return False
        if self._allow is not None:
            return tool_name in self._allow
        return True
