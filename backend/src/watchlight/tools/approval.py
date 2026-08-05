# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 approval 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tool approval flow."""

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApprovalRequest:
    id: str
    tool_name: str
    params: dict[str, Any]
    resolved: asyncio.Event = field(default_factory=asyncio.Event)
    approved: bool = False
    reason: str | None = None


class ApprovalManager:
    def __init__(self) -> None:
        self._pending: dict[str, ApprovalRequest] = {}

    async def request_approval(
        self, request_id: str, tool_name: str, params: dict[str, Any], timeout: float = 60
    ) -> bool:
        req = ApprovalRequest(id=request_id, tool_name=tool_name, params=params)
        self._pending[request_id] = req
        try:
            await asyncio.wait_for(req.resolved.wait(), timeout=timeout)
            return req.approved
        except TimeoutError:
            return False
        finally:
            self._pending.pop(request_id, None)

    def resolve(self, request_id: str, approved: bool, reason: str | None = None) -> bool:
        req = self._pending.get(request_id)
        if req is None:
            return False
        req.approved = approved
        req.reason = reason
        req.resolved.set()
        return True

    def list_pending(self) -> list[ApprovalRequest]:
        return list(self._pending.values())
