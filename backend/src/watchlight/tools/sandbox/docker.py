# 文件说明：本文件属于 工具系统层。
# 主要职责：实现 docker 相关能力。
# 阅读提示：注册、执行和限制工具调用。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Docker sandbox — execute commands in isolated containers."""

import asyncio
from typing import Any

from watchlight.core.logging import get_logger

log = get_logger("tools.sandbox.docker")


class DockerSandbox:
    """Execute commands in a Docker container."""

    def __init__(
        self,
        image: str = "python:3.12-slim",
        mount_mode: str = "none",  # "none" | "read-only" | "read-write"
        workspace: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.image = image
        self.mount_mode = mount_mode
        self.workspace = workspace
        self.timeout = timeout

    async def execute(self, command: str) -> dict[str, Any]:
        """Run a command inside Docker container."""
        docker_cmd = ["docker", "run", "--rm", "--network=none"]

        if self.workspace and self.mount_mode != "none":
            ro = ":ro" if self.mount_mode == "read-only" else ""
            docker_cmd.extend(["-v", f"{self.workspace}:/workspace{ro}", "-w", "/workspace"])

        docker_cmd.extend(["--memory=256m", "--cpus=1", self.image, "sh", "-c", command])

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode,
            }
        except TimeoutError:
            log.error("docker_timeout", command=command[:100])
            return {"error": "Docker execution timed out", "exit_code": -1}
        except FileNotFoundError:
            return {"error": "Docker not available", "exit_code": -1}
        except Exception as e:
            log.error("docker_error", error=str(e))
            return {"error": str(e), "exit_code": -1}
