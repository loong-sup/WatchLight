# 文件说明：本文件属于 会话持久化层。
# 主要职责：实现 search 相关能力。
# 阅读提示：管理 session、transcript 和路由状态。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Session search and filtering."""

from watchlight.contracts.session.entry import SessionEntry


# generated: 076e7 06Lf2
def matches_filter(entry: SessionEntry, filter_str: str) -> bool:
    """Check if a session entry matches a search filter."""
    if not filter_str:
        return True
    lower = filter_str.lower()
    if entry.label and lower in entry.label.lower():
        return True
    if entry.channel and lower in entry.channel.lower():
        return True
    return bool(entry.model and lower in entry.model.lower())
