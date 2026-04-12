import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def _b64decode(data: str) -> bytes:
    return base64.b64decode(data.encode("utf-8"))


def get_master_key() -> bytes:
    try:
        key = _b64decode(settings.app_aes_key)
    except Exception as exc:
        raise ValueError("APP_AES_KEY must be valid base64") from exc

    if len(key) != 32:
        raise ValueError("APP_AES_KEY must decode to exactly 32 bytes")

    return key


def encrypt_api_key(plain_api_key: str) -> tuple[str, str, str]:
    if not plain_api_key or not plain_api_key.strip():
        raise ValueError("API key must not be empty")

    key = get_master_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)

    encrypted = aesgcm.encrypt(iv, plain_api_key.encode("utf-8"), None)
    ciphertext = encrypted[:-16]
    auth_tag = encrypted[-16:]

    return _b64encode(ciphertext), _b64encode(iv), _b64encode(auth_tag)


def decrypt_api_key(ciphertext_b64: str, iv_b64: str, auth_tag_b64: str) -> str:
    key = get_master_key()
    aesgcm = AESGCM(key)

    ciphertext = _b64decode(ciphertext_b64)
    iv = _b64decode(iv_b64)
    auth_tag = _b64decode(auth_tag_b64)

    plain = aesgcm.decrypt(iv, ciphertext + auth_tag, None)
    return plain.decode("utf-8")


def mask_api_key(value: str, prefix_len: int = 4) -> str:
    if value is None:
        return ""
    if len(value) <= prefix_len:
        return value
    return value[:prefix_len] + ("*" * (len(value) - prefix_len))
