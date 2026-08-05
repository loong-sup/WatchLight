# 文件说明：本文件属于 契约层。
# 主要职责：实现 adapters 相关能力。
# 阅读提示：定义跨模块共享的数据结构。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Channel adapter protocols — optional capabilities a channel can implement."""

from typing import Any, Protocol


class ChannelConfigAdapter(Protocol):
    """Config resolution for a channel."""

    def list_account_ids(self, config: dict[str, Any]) -> list[str]: ...
    def resolve_account(self, config: dict[str, Any], account_id: str | None = None) -> Any: ...


class ChannelOutboundAdapter(Protocol):
    """Outbound message delivery."""

    @property
    def delivery_mode(self) -> str: ...  # "direct" | "gateway" | "hybrid"

    async def send_text(
        self, account_id: str, conversation_id: str, text: str, **kwargs: Any
    ) -> dict[str, Any]: ...


class ChannelStreamingAdapter(Protocol):
    """Block streaming support."""

    @property
    def block_streaming_coalesce_defaults(self) -> dict[str, int]: ...


class ChannelGatewayAdapter(Protocol):
    """Gateway lifecycle — start/stop channel accounts."""

    async def start_account(self, account_id: str, config: dict[str, Any]) -> None: ...
    async def stop_account(self, account_id: str) -> None: ...
