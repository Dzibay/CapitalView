"""
Хранение API-токенов брокеров.

В БД токен лежит зашифрованным (Fernet, префикс ``enc:v1:``) и наружу не отдаётся:
браузер видит только маску (``••••1a2b``). Для поиска «этот токен уже подключён»
используется отпечаток SHA-256 — токены брокеров длинные и случайные, подобрать
токен по отпечатку нельзя.

Значения без префикса — токены, сохранённые до шифрования; они читаются как есть
и шифруются при ближайшей записи (и миграцией в init_db).
"""
import base64
import hashlib
from functools import lru_cache
from typing import List, Optional

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.config import Config

ENCRYPTED_PREFIX = "enc:v1:"


class BrokerTokenUnavailable(Exception):
    """Сохранённый токен не расшифровывается (сменился ключ шифрования)."""


def _fernet_from_secret(secret: str) -> Fernet:
    digest = hashlib.sha256(b"capitalview:broker-token:" + secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _key_secrets() -> List[str]:
    secrets = []
    if Config.BROKER_TOKEN_ENCRYPTION_KEY:
        secrets.append(Config.BROKER_TOKEN_ENCRYPTION_KEY)
    secrets.extend(s.strip() for s in Config.BROKER_TOKEN_ENCRYPTION_KEY_OLD.split(",") if s.strip())
    if Config.JWT_SECRET_KEY:
        secrets.append(Config.JWT_SECRET_KEY)
    if not secrets:
        raise RuntimeError("Не задан ключ шифрования токенов брокеров (BROKER_TOKEN_ENCRYPTION_KEY или JWT_SECRET_KEY)")
    return list(dict.fromkeys(secrets))


@lru_cache(maxsize=1)
def _cipher() -> MultiFernet:
    # Шифруем первым ключом, расшифровываем любым из списка
    return MultiFernet([_fernet_from_secret(s) for s in _key_secrets()])


def is_encrypted(value: Optional[str]) -> bool:
    return bool(value) and value.startswith(ENCRYPTED_PREFIX)


def encrypt_token(token: Optional[str]) -> Optional[str]:
    token = (token or "").strip()
    if not token:
        return None
    if is_encrypted(token):
        return token
    return ENCRYPTED_PREFIX + _cipher().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(stored: Optional[str]) -> Optional[str]:
    if not stored:
        return None
    if not is_encrypted(stored):
        return stored  # сохранён до шифрования
    try:
        return _cipher().decrypt(stored[len(ENCRYPTED_PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise BrokerTokenUnavailable(
            "Сохранённый токен брокера не удалось прочитать — подключите брокера заново"
        ) from e


def token_fingerprint(token: Optional[str]) -> Optional[str]:
    token = (token or "").strip()
    if not token:
        return None
    return hashlib.sha256(b"capitalview:broker-token-fp:" + token.encode("utf-8")).hexdigest()


def mask_token(token: Optional[str]) -> Optional[str]:
    token = (token or "").strip()
    if not token:
        return None
    return "••••" + token[-4:] if len(token) > 8 else "••••"
