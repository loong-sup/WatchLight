# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 health 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
