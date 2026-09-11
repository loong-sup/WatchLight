import asyncio
import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from watchlight.channels.wecom.client import WeComResponseClient
from watchlight.channels.wecom.crypto import WeComCrypto, WeComSignatureError
from watchlight.channels.wecom.message import parse_inbound
from watchlight.channels.wecom.plugin import WeComChannelPlugin
from watchlight.contracts.channel.plugin import OutboundMessage
from watchlight.gateway.app import create_app

TOKEN = "watchlight-wecom"
AES_KEY = base64.b64encode(bytes(range(32))).decode("ascii").rstrip("=")


def test_wecom_crypto_round_trip_and_signature() -> None:
    crypto = WeComCrypto(TOKEN, AES_KEY)
    payload = json.dumps({"msgid": "message-1", "msgtype": "text"})
    envelope = crypto.encrypt(payload, timestamp="1700000000", nonce="nonce-1")
    encrypted = str(envelope["encrypt"])

    crypto.verify_signature(
        str(envelope["msgsignature"]), "1700000000", "nonce-1", encrypted
    )
    assert crypto.decrypt(encrypted) == payload
    with pytest.raises(WeComSignatureError):
        crypto.verify_signature("bad", "1700000000", "nonce-1", encrypted)


def test_wecom_group_message_is_normalized_and_mention_removed() -> None:
    message = parse_inbound(
        {
            "msgid": "message-1",
            "aibotid": "bot-1",
            "chatid": "group-1",
            "chattype": "group",
            "from": {"userid": "alice"},
            "response_url": "https://qyapi.weixin.qq.com/cgi-bin/aibot/response?code=1",
            "msgtype": "text",
            "text": {"content": "@Watchlight 帮我总结"},
        },
        account_id="default",
        bot_name="Watchlight",
    )

    assert message is not None
    assert message.channel == "wecom"
    assert message.chat_type == "group"
    assert message.conversation_id == "group-1"
    assert message.sender_id == "alice"
    assert message.text == "帮我总结"
    assert message.raw and message.raw["mentioned_bot"] is True


@pytest.mark.asyncio
async def test_wecom_plugin_dispatches_once_and_uses_response_url() -> None:
    inbound = AsyncMock()
    response_client = SimpleNamespace(send_markdown=AsyncMock(return_value={"errcode": 0}))
    plugin = WeComChannelPlugin(on_inbound=inbound)
    await plugin.start(
        "default",
        {
            "channels": {
                "wecom": {
                    "accounts": {
                        "default": {
                            "token": TOKEN,
                            "encodingAESKey": AES_KEY,
                            "botName": "Watchlight",
                        }
                    }
                }
            }
        },
    )
    plugin._clients["default"] = response_client  # type: ignore[assignment]
    payload = {
        "msgid": "message-1",
        "chatid": "group-1",
        "chattype": "group",
        "from": {"userid": "alice"},
        "response_url": "https://qyapi.weixin.qq.com/cgi-bin/aibot/response?code=1",
        "msgtype": "text",
        "text": {"content": "@Watchlight 你好"},
    }

    assert await plugin.handle_event("default", payload) is True
    await asyncio.sleep(0)
    inbound.assert_awaited_once()
    assert await plugin.handle_event("default", payload) is False
    await plugin.send(
        "default",
        "group-1",
        OutboundMessage(text="**你好**", replyToId="message-1"),
    )
    response_client.send_markdown.assert_awaited_once_with(
        payload["response_url"], "**你好**"
    )
    with pytest.raises(RuntimeError, match="recent inbound response_url"):
        await plugin.send(
            "default",
            "group-1",
            OutboundMessage(text="重复回复", replyToId="message-1"),
        )


def test_wecom_response_url_rejects_untrusted_host() -> None:
    with pytest.raises(ValueError, match="response_url host"):
        WeComResponseClient._validate_response_url("https://example.com/steal")


def test_wecom_callback_routes_verify_and_ack() -> None:
    app = create_app(boot=False)
    runtime = SimpleNamespace(
        verify_wecom_callback=lambda *args, **kwargs: "verified",
        handle_wecom_callback=AsyncMock(return_value=True),
    )
    app.state.gateway_runtime = runtime
    client = TestClient(app)
    params = {"msg_signature": "sig", "timestamp": "1", "nonce": "n"}

    verify = client.get(
        "/api/channels/wecom/events", params={**params, "echostr": "encrypted"}
    )
    assert verify.status_code == 200
    assert verify.text == "verified"
    callback = client.post(
        "/api/channels/wecom/events",
        params=params,
        content=json.dumps({"encrypt": "encrypted"}),
        headers={"content-type": "application/json"},
    )
    assert callback.status_code == 200
    assert callback.content == b""
    runtime.handle_wecom_callback.assert_awaited_once()
