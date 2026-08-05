# 文件说明：本文件属于 插件管理层。
# 主要职责：实现 installer 相关能力。
# 阅读提示：处理插件发现、安装和注册。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Plugin installer — install/update/remove plugins."""

import shutil
import subprocess
from pathlib import Path
from typing import Any

from watchlight.core.logging import get_logger

# generated: 01Ocd 00Wac
log = get_logger("plugins.installer")


class PluginInstaller:
    def __init__(self, extensions_dir: Path) -> None:
        self._dir = extensions_dir

    def install(self, spec: str, source: str = "npm") -> dict[str, Any]:
        """Install a plugin from npm or local path."""
        log.info("plugin_install", spec=spec, source=source)
        if source == "local":
            src = Path(spec)
            if not src.exists():
                return {"ok": False, "error": f"Path not found: {spec}"}
            dest = self._dir / src.name
            shutil.copytree(src, dest, dirs_exist_ok=True)
            return {"ok": True, "path": str(dest)}
        # npm install
        try:
            result = subprocess.run(
                ["npm", "pack", spec, "--pack-destination", str(self._dir)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {"ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def remove(self, plugin_id: str) -> bool:
        path = self._dir / plugin_id
        if path.exists():
            shutil.rmtree(path)
            log.info("plugin_removed", id=plugin_id)
            return True
        return False

    def list_installed(self) -> list[str]:
        if not self._dir.exists():
            return []
        return [
            d.name
            for d in self._dir.iterdir()
            if d.is_dir() and (d / "watchlight.plugin.json").exists()
        ]
