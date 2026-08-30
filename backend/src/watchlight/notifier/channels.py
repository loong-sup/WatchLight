from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from watchlight.contracts.channel.plugin import OutboundMessage
from watchlight.storage.repos.identity import IdentityRepo

if TYPE_CHECKING:
    from watchlight.contracts.channel.plugin import ChannelPlugin
    from watchlight.storage.store import Store


class ChannelAdapter(Protocol):
    async def send(self, user_id: str, text: str) -> None: ...


class MemoryChannelAdapter:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send(self, user_id: str, text: str) -> None:
        self.sent.append((user_id, text))


class RuntimeChannelAdapter:
    """Deliver a notification through an already-started Gateway channel plugin."""

    def __init__(self, store: Store, channel_key: str, plugin: ChannelPlugin) -> None:
        self.store = store
        self.channel_key = channel_key
        self.plugin = plugin

    async def send(self, user_id: str, text: str) -> None:
        identities = IdentityRepo(self.store).list_bound(user_id)
        identity = next(
            (item for item in identities if item["channel_key"] == self.channel_key), None
        )
        if identity is None:
            raise LookupError(f"no bound {self.channel_key} identity")
        channel_data = (
            {"receive_id_type": "open_id"}
            if self.channel_key == "feishu"
            else None
        )
        await self.plugin.send(
            "default",
            str(identity["channel_user_id"]),
            OutboundMessage(text=text, channelData=channel_data),
        )


class ChannelAdapters:
    def __init__(self) -> None:
        self._items: dict[str, ChannelAdapter] = {}

    def register(self, channel_key: str, adapter: ChannelAdapter) -> None:
        self._items[channel_key] = adapter

    def get(self, channel_key: str) -> ChannelAdapter:
        try:
            return self._items[channel_key]
        except KeyError as exc:
            raise LookupError(f"channel unavailable: {channel_key}") from exc
