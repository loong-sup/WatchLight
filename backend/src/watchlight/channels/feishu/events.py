# 文件说明：本文件属于 通道接入层。
# 主要职责：处理事件接收、解码和分发。
# 阅读提示：统一外部消息入口和回复出口。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""飞书 WebSocket 长连接事件订阅。

本模块负责连接飞书开放平台的长连接地址，直接接收实时事件。
这种方式不需要公网回调 URL，是当前本地开发和内网部署的推荐模式。
"""

import asyncio
import json
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import websockets

from watchlight.channels.feishu.auth import FeishuAuth
from watchlight.core.logging import get_logger

log = get_logger("channel.feishu.events")

FEISHU_WS_ENDPOINT_URL = "https://open.feishu.cn/callback/ws/endpoint"

FRAME_TYPE_CONTROL = 0
FRAME_TYPE_DATA = 1
HEADER_TYPE = "type"
HEADER_MESSAGE_ID = "message_id"
HEADER_SUM = "sum"
HEADER_SEQ = "seq"
HEADER_TRACE_ID = "trace_id"
HEADER_BIZ_RT = "biz_rt"
MESSAGE_TYPE_EVENT = "event"
MESSAGE_TYPE_PING = "ping"
MESSAGE_TYPE_PONG = "pong"

MessageHandler = Callable[[dict[str, Any]], Any]


def _encode_varint(value: int) -> bytes:
    # 飞书长连接帧使用类似 protobuf 的 varint 编码，不能直接按 JSON 文本处理。
    chunks = bytearray()
    raw = value
    while raw > 0x7F:
        chunks.append((raw & 0x7F) | 0x80)
        raw >>= 7
    chunks.append(raw)
    return bytes(chunks)


def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    shift = 0
    value = 0
    cursor = offset
    while cursor < len(data):
        byte = data[cursor]
        cursor += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, cursor
        shift += 7
    raise ValueError("truncated varint")


def _encode_len(field_number: int, payload: bytes) -> bytes:
    return _encode_varint((field_number << 3) | 2) + _encode_varint(len(payload)) + payload


def _encode_header(header: dict[str, str]) -> bytes:
    result = bytearray()
    key = header.get("key", "").encode()
    value = header.get("value", "").encode()
    result.extend(_encode_len(1, key))
    result.extend(_encode_len(2, value))
    return bytes(result)


def _decode_header(data: bytes) -> dict[str, str]:
    header: dict[str, str] = {}
    cursor = 0
    while cursor < len(data):
        tag, cursor = _decode_varint(data, cursor)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type != 2:
            raise ValueError(f"unsupported header wire type: {wire_type}")
        size, cursor = _decode_varint(data, cursor)
        payload = data[cursor : cursor + size]
        cursor += size
        if field == 1:
            header["key"] = payload.decode()
        elif field == 2:
            header["value"] = payload.decode()
    return header


def _encode_frame(frame: dict[str, Any]) -> bytes:
    result = bytearray()

    def add_varint(field_number: int, value: Any) -> None:
        result.extend(_encode_varint(field_number << 3))
        result.extend(_encode_varint(int(value)))

    if "SeqID" in frame:
        add_varint(1, frame["SeqID"])
    if "LogID" in frame:
        add_varint(2, frame["LogID"])
    if "service" in frame:
        add_varint(3, frame["service"])
    if "method" in frame:
        add_varint(4, frame["method"])
    for header in frame.get("headers", []):
        result.extend(_encode_len(5, _encode_header(header)))
    if frame.get("payloadEncoding"):
        result.extend(_encode_len(6, str(frame["payloadEncoding"]).encode()))
    if frame.get("payloadType"):
        result.extend(_encode_len(7, str(frame["payloadType"]).encode()))
    if frame.get("payload") is not None:
        payload = frame["payload"]
        if isinstance(payload, str):
            payload = payload.encode()
        result.extend(_encode_len(8, bytes(payload)))
    if frame.get("LogIDNew"):
        result.extend(_encode_len(9, str(frame["LogIDNew"]).encode()))
    return bytes(result)


def _decode_frame(data: bytes) -> dict[str, Any]:
    frame: dict[str, Any] = {"headers": []}
    cursor = 0
    while cursor < len(data):
        tag, cursor = _decode_varint(data, cursor)
        field = tag >> 3
        wire_type = tag & 7
        if wire_type == 0:
            value, cursor = _decode_varint(data, cursor)
            if field == 1:
                frame["SeqID"] = value
            elif field == 2:
                frame["LogID"] = value
            elif field == 3:
                frame["service"] = value
            elif field == 4:
                frame["method"] = value
            continue
        if wire_type != 2:
            raise ValueError(f"unsupported frame wire type: {wire_type}")
        size, cursor = _decode_varint(data, cursor)
        payload = data[cursor : cursor + size]
        cursor += size
        if field == 5:
            frame["headers"].append(_decode_header(payload))
        elif field == 6:
            frame["payloadEncoding"] = payload.decode()
        elif field == 7:
            frame["payloadType"] = payload.decode()
        elif field == 8:
            frame["payload"] = payload
        elif field == 9:
            frame["LogIDNew"] = payload.decode()
    return frame


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {header.get("key", ""): header.get("value", "") for header in headers}


class FeishuEventSubscriber:
    """通过飞书长连接订阅事件，并把解码后的事件交给上层 channel 处理。"""

    def __init__(self, auth: FeishuAuth, on_message: MessageHandler) -> None:
        self.auth = auth
        self.on_message = on_message
        self._task: asyncio.Task[None] | None = None
        self._ping_task: asyncio.Task[None] | None = None
        self._event_chunks: dict[str, list[bytes | None]] = {}
        self._running = False

    async def _get_ws_config(self) -> tuple[str, dict[str, Any]]:
        """从飞书 endpoint API 获取本次连接要使用的 WebSocket 地址和客户端配置。"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                FEISHU_WS_ENDPOINT_URL,
                headers={"locale": "zh", "User-Agent": "watchlight-py/0.1"},
                json={"AppID": self.auth.app_id, "AppSecret": self.auth.app_secret},
                timeout=15,
            )
            data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get Feishu WS endpoint: {data.get('msg')}")

        url_data = data.get("data", {})
        ws_url = url_data.get("URL") or url_data.get("url")
        if not ws_url:
            raise RuntimeError(f"No WebSocket URL in response: {data}")
        client_config = url_data.get("ClientConfig")
        return str(ws_url), client_config if isinstance(client_config, dict) else {}

    async def _loop(self) -> None:
        """长连接主循环：负责连接、收帧、断线后指数退避重连。"""
        backoff = 1.0  # 断线后从 1 秒开始重连，最长退避到 60 秒。
        max_backoff = 60.0

        while self._running:
            try:
                ws_url, client_config = await self._get_ws_config()
                log.info("feishu_ws_connecting", url=ws_url[:50] + "...")

                async with websockets.connect(ws_url, ping_interval=None) as ws:
                    log.info("feishu_ws_connected")
                    backoff = 1.0  # 连接成功后重置退避时间，避免下一次断线等待过久。
                    # 飞书需要业务层 ping 帧保活，仅依赖 WebSocket 协议 ping 不够。
                    self._ping_task = asyncio.create_task(
                        self._ping_loop(ws, ws_url, client_config)
                    )
                    async for raw_message in ws:
                        try:
                            if not isinstance(raw_message, bytes):
                                log.warning("feishu_ws_invalid_text_frame")
                                continue
                            data = _decode_frame(raw_message)
                            await self._handle_frame(data, ws)
                        except Exception as e:
                            log.error("feishu_ws_handler_error", error=str(e), exc_info=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("feishu_ws_disconnected", error=str(e), backoff=backoff)
                self._cancel_ping_task()
                if self._running:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)  # 指数退避，降低频繁重连压力。

    async def _ping_loop(
        self,
        ws: Any,
        ws_url: str,
        client_config: dict[str, Any],
    ) -> None:
        parsed = urlparse(ws_url)
        query = parse_qs(parsed.query)
        service_id = int((query.get("service_id") or ["0"])[0] or 0)
        interval = int(client_config.get("PingInterval", 120))
        while self._running:
            frame = {
                "SeqID": 0,
                "LogID": 0,
                "service": service_id,
                "method": FRAME_TYPE_CONTROL,
                "headers": [{"key": HEADER_TYPE, "value": MESSAGE_TYPE_PING}],
            }
            await ws.send(_encode_frame(frame))
            await asyncio.sleep(max(interval, 1))

    async def _handle_frame(self, data: dict[str, Any], ws: Any) -> None:
        """处理单个飞书 WebSocket 帧，包括控制帧、事件帧、分片事件和 ack。"""
        headers = _headers_to_dict(data.get("headers", []))
        frame_type = headers.get(HEADER_TYPE, "")
        method = data.get("method")

        if method == FRAME_TYPE_CONTROL:
            if frame_type == MESSAGE_TYPE_PONG:
                log.debug("feishu_ws_pong")
            return

        if method != FRAME_TYPE_DATA or frame_type != MESSAGE_TYPE_EVENT:
            return

        # 大事件可能被飞书拆成多个帧；只有分片合并完整后才交给消息解析层。
        merged = self._merge_event_payload(headers, data.get("payload", b""))
        if merged is None:
            return

        event_type = ""
        header = merged.get("header")
        if isinstance(header, dict):
            event_type = str(header.get("event_type") or "")
        log.info("feishu_event_received", event_type=event_type)
        await self._ack_event(ws, data)
        await self.on_message(merged)

    def _merge_event_payload(
        self, headers: dict[str, str], payload: bytes
    ) -> dict[str, Any] | None:
        message_id = headers.get(HEADER_MESSAGE_ID) or headers.get(HEADER_TRACE_ID) or "single"
        total = max(int(headers.get(HEADER_SUM) or 1), 1)
        seq = int(headers.get(HEADER_SEQ) or 0)
        if total == 1:
            loaded = json.loads(payload.decode())
            return loaded if isinstance(loaded, dict) else {}

        # 按 message/trace id 分桶缓存分片，避免多个事件交错到达时互相污染。
        chunks = self._event_chunks.setdefault(message_id, [None] * total)
        if 0 <= seq < total:
            chunks[seq] = payload
        if any(chunk is None for chunk in chunks):
            return None
        merged = b"".join(chunk or b"" for chunk in chunks)
        self._event_chunks.pop(message_id, None)
        loaded = json.loads(merged.decode())
        return loaded if isinstance(loaded, dict) else {}

    async def _ack_event(self, ws: Any, frame: dict[str, Any]) -> None:
        # 解码成功后先向飞书 ack，后续业务处理失败只记本地日志，避免飞书持续重投。
        headers = [*frame.get("headers", []), {"key": HEADER_BIZ_RT, "value": "0"}]
        ack = {
            **frame,
            "headers": headers,
            "payload": json.dumps({"code": 200}).encode(),
        }
        await ws.send(_encode_frame(ack))

    def _cancel_ping_task(self) -> None:
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None

    def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        log.info("feishu_event_subscriber_started")

    def stop(self) -> None:
        self._running = False
        self._cancel_ping_task()
        if self._task:
            self._task.cancel()
            self._task = None
        log.info("feishu_event_subscriber_stopped")
