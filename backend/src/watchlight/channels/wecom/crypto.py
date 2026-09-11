"""企业微信智能机器人回调的签名校验与 AES-256-CBC 加解密。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class WeComCryptoError(ValueError):
    """企业微信回调内容无效或无法解密。"""


class WeComSignatureError(WeComCryptoError):
    """企业微信回调签名不匹配。"""


class WeComCrypto:
    """实现企业微信官方回调协议使用的 AES-CBC 消息封装。"""

    _BLOCK_SIZE = 32

    def __init__(self, token: str, encoding_aes_key: str, receive_id: str = "") -> None:
        if not token:
            raise WeComCryptoError("token is required")
        try:
            key = base64.b64decode(f"{encoding_aes_key}=", validate=True)
        except (ValueError, TypeError) as exc:
            raise WeComCryptoError("invalid EncodingAESKey") from exc
        if len(key) != 32:
            raise WeComCryptoError("EncodingAESKey must decode to 32 bytes")
        self.token = token
        self.key = key
        self.receive_id = receive_id

    def signature(self, timestamp: str, nonce: str, encrypted: str) -> str:
        items = sorted([self.token, str(timestamp), str(nonce), encrypted])
        return hashlib.sha1("".join(items).encode("utf-8")).hexdigest()

    def verify_signature(
        self, signature: str, timestamp: str, nonce: str, encrypted: str
    ) -> None:
        expected = self.signature(timestamp, nonce, encrypted)
        if not hmac.compare_digest(expected, signature):
            raise WeComSignatureError("invalid callback signature")

    def decrypt(self, encrypted: str) -> str:
        try:
            ciphertext = base64.b64decode(encrypted, validate=True)
            decryptor = Cipher(
                algorithms.AES(self.key), modes.CBC(self.key[:16])
            ).decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
        except (ValueError, TypeError) as exc:
            raise WeComCryptoError("invalid encrypted callback") from exc

        plain = self._unpad(padded)
        if len(plain) < 20:
            raise WeComCryptoError("decrypted callback is too short")
        message_length = struct.unpack("!I", plain[16:20])[0]
        message_end = 20 + message_length
        if message_end > len(plain):
            raise WeComCryptoError("invalid callback message length")
        message = plain[20:message_end]
        try:
            received_id = plain[message_end:].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WeComCryptoError("callback receive id is not UTF-8") from exc
        if self.receive_id and received_id != self.receive_id:
            raise WeComCryptoError("callback receive id does not match")
        try:
            return message.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WeComCryptoError("callback message is not UTF-8") from exc

    def decrypt_json(self, encrypted: str) -> dict[str, Any]:
        try:
            value = json.loads(self.decrypt(encrypted))
        except json.JSONDecodeError as exc:
            raise WeComCryptoError("decrypted callback is not JSON") from exc
        if not isinstance(value, dict):
            raise WeComCryptoError("decrypted callback must be an object")
        return value

    def encrypt(
        self,
        message: str,
        *,
        timestamp: str | None = None,
        nonce: str | None = None,
    ) -> dict[str, str | int]:
        """加密被动回复；也用于协议回环测试。"""
        timestamp_value = timestamp or str(int(time.time()))
        nonce_value = nonce or secrets.token_hex(8)
        message_bytes = message.encode("utf-8")
        plain = (
            secrets.token_bytes(16)
            + struct.pack("!I", len(message_bytes))
            + message_bytes
            + self.receive_id.encode("utf-8")
        )
        encryptor = Cipher(
            algorithms.AES(self.key), modes.CBC(self.key[:16])
        ).encryptor()
        ciphertext = encryptor.update(self._pad(plain)) + encryptor.finalize()
        encrypted = base64.b64encode(ciphertext).decode("ascii")
        return {
            "encrypt": encrypted,
            "msgsignature": self.signature(timestamp_value, nonce_value, encrypted),
            "timestamp": int(timestamp_value),
            "nonce": nonce_value,
        }

    @classmethod
    def _pad(cls, value: bytes) -> bytes:
        padding = cls._BLOCK_SIZE - len(value) % cls._BLOCK_SIZE
        return value + bytes([padding]) * padding

    @classmethod
    def _unpad(cls, value: bytes) -> bytes:
        if not value:
            raise WeComCryptoError("empty decrypted callback")
        padding = value[-1]
        if padding < 1 or padding > cls._BLOCK_SIZE:
            raise WeComCryptoError("invalid callback padding")
        if value[-padding:] != bytes([padding]) * padding:
            raise WeComCryptoError("invalid callback padding")
        return value[:-padding]
