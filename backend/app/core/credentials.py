"""Versioned, bounded standard-library password hashing; no credential logging."""

import hashlib
import hmac
import re
import secrets
from threading import BoundedSemaphore

SCRYPT_N = 2**15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 64 * 1024 * 1024
_hash_slots = BoundedSemaphore(2)
USERNAME_MESSAGE = (
    "استخدم من 3 إلى 32 حرفًا لاسم المستخدم: أحرف إنجليزية أو أرقام أو . أو _ أو - فقط."
)
PASSWORD_MESSAGE = "كلمة المرور قصيرة. استخدم 8 أحرف على الأقل."


def normalize_username(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9._-]{3,32}", value) is None:
        raise ValueError(USERNAME_MESSAGE)
    return value.lower()


def validate_password(value: str) -> None:
    if len(value) < 8:
        raise ValueError(PASSWORD_MESSAGE)
    if len(value) > 256:
        raise ValueError("استخدم كلمة مرور لا تتجاوز 256 حرفًا.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("كلمة المرور تحتوي على أحرف غير صالحة.") from None


def _derive(password: str, salt: bytes) -> bytes:
    # Bound concurrent memory consumption to about 64 MiB per worker process.
    with _hash_slots:
        return hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            maxmem=SCRYPT_MAXMEM,
            dklen=64,
        )


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = _derive(password, salt)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$")
        # Accept only reviewed parameter sets, never arbitrary database-supplied work.
        if (algorithm, n, r, p) != ("scrypt", str(SCRYPT_N), str(SCRYPT_R), str(SCRYPT_P)):
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 64 or len(password) > 256:
            return False
    except (ValueError, TypeError):
        return False
    try:
        actual = _derive(password, salt)
    except UnicodeEncodeError:
        _derive("", salt)
        return False
    return hmac.compare_digest(actual, expected)


# Construct once before serving requests: missing identities still perform one hash.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))
