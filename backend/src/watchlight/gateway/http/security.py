# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：实现 security 相关能力。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Security middleware — CORS, headers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_security(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production
        allow_methods=["*"],
        allow_headers=["*"],
    )
