# 文件说明：本文件属于 插件管理层。
# 主要职责：维护组件注册和查询逻辑。
# 阅读提示：处理插件发现、安装和注册。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Plugin registry — discover, load, manage plugins."""

import json
from pathlib import Path

from watchlight.contracts.plugin.manifest import PluginManifest
from watchlight.core.logging import get_logger

log = get_logger("plugins.registry")


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}
        self._enabled: set[str] = set()

    def discover(self, extensions_dir: Path) -> int:
        """Scan extensions directory for plugin manifests."""
        count = 0
        if not extensions_dir.exists():
            return 0
        for manifest_path in extensions_dir.glob("*/watchlight.plugin.json"):
            try:
                data = json.loads(manifest_path.read_text())
                manifest = PluginManifest.model_validate(data)
                self._plugins[manifest.id] = manifest
                if manifest.enabled_by_default:
                    self._enabled.add(manifest.id)
                count += 1
            except Exception as e:
                log.warning("plugin_manifest_error", path=str(manifest_path), error=str(e))
        log.info("plugins_discovered", count=count)
        return count

    def register(self, manifest: PluginManifest) -> None:
        self._plugins[manifest.id] = manifest

    def enable(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            self._enabled.add(plugin_id)
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        self._enabled.discard(plugin_id)
        return True

    def get(self, plugin_id: str) -> PluginManifest | None:
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[PluginManifest]:
        return list(self._plugins.values())

    def list_enabled(self) -> list[PluginManifest]:
        return [p for pid, p in self._plugins.items() if pid in self._enabled]

    def is_enabled(self, plugin_id: str) -> bool:
        return plugin_id in self._enabled
