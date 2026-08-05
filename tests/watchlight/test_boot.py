from pathlib import Path
from types import SimpleNamespace

import pytest
from watchlight.contracts.config.types_watchlight import WatchlightConfig, WatchshedConfig
from watchlight.gateway.boot_watchshed import bootstrap_watchlight
from watchlight.tools.factory import create_default_tool_registry
from watchlight.tools.policy import ToolPolicy
from watchlight.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_bootstrap_scheduler_tick_and_clean_shutdown(tmp_path: Path) -> None:
    services = bootstrap_watchlight(
        WatchlightConfig(
            watchshed=WatchshedConfig(
                dbPath=str(tmp_path / "watch.db"), blobRoot=str(tmp_path / "blobs")
            )
        )
    )
    assert await services.scheduler.tick() == []
    await services.start()
    assert len(services._tasks) == 2
    await services.stop()


def test_bootstrap_registers_read_only_task_tool_for_messaging(tmp_path: Path) -> None:
    assert create_default_tool_registry().get("watch_tasks_list") is None
    registry = ToolRegistry()
    runtime = SimpleNamespace(
        tool_registry=registry,
        channel_registry=SimpleNamespace(get=lambda _channel: None),
    )
    services = bootstrap_watchlight(
        WatchlightConfig(
            watchshed=WatchshedConfig(
                dbPath=str(tmp_path / "watch.db"), blobRoot=str(tmp_path / "blobs")
            )
        ),
        runtime,
    )

    assert registry.get("watch_tasks_list") is not None
    assert registry.get("watch_tasks_delete") is None
    policy = ToolPolicy(profile="messaging")
    assert policy.is_allowed("watch_tasks_list")
    assert not policy.is_allowed("bash")
    assert not policy.is_allowed("write_file")
    services.store.close()
