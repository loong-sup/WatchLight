# 文件说明：本文件属于 插件管理层。
# 主要职责：实现 marketplace 相关能力。
# 阅读提示：处理插件发现、安装和注册。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Plugin marketplace — remote catalog discovery."""

from typing import Any

import httpx

from watchlight.core.logging import get_logger

log = get_logger("plugins.marketplace")


class PluginMarketplace:
    """Optional remote plugin catalog."""

    def __init__(self, catalog_url: str | None = None) -> None:
        self._url = catalog_url

    async def search(self, query: str = "") -> list[dict[str, Any]]:
        if not self._url:
            return []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self._url, params={"q": query})
                data: dict[str, Any] = resp.json()
                result: list[dict[str, Any]] = data.get("plugins", [])
                return result
        except Exception as e:
            log.error("marketplace_search_failed", error=str(e))
            return []

    async def get_info(self, plugin_id: str) -> dict[str, Any] | None:
        if not self._url:
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._url}/{plugin_id}")
                result: dict[str, Any] = resp.json()
                return result
        except Exception:
            return None
