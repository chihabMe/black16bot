import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


PREFIX = "enc:v1:"


class DecryptionError(Exception):
    pass


def _fernet() -> Fernet:
    key_material = settings.STOCK_ENCRYPTION_KEY or settings.SECRET_KEY
    digest = hashlib.sha256(key_material.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def is_encrypted(value: str) -> bool:
    return bool(value and value.startswith(PREFIX))


def encrypt_text(value: str) -> str:
    if not value or is_encrypted(value):
        return value
    token = _fernet().encrypt(value.encode()).decode()
    return PREFIX + token


def decrypt_text(value: str) -> str:
    if not value or not is_encrypted(value):
        return value
    token = value.removeprefix(PREFIX).encode()
    try:
        return _fernet().decrypt(token).decode()
    except InvalidToken:
        raise DecryptionError("Failed to decrypt value (possible key mismatch)")
