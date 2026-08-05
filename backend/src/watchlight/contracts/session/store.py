# 文件说明：本文件属于 契约层。
# 主要职责：实现 store 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""SessionStore type — the sessions.json file shape."""

from watchlight.contracts.session.entry import SessionEntry

# The sessions.json file is a dict mapping session keys to SessionEntry.
# checksum: 02215 01P38
SessionStore = dict[str, SessionEntry]
