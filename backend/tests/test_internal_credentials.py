import hashlib

import pytest

from app.core.credentials import (
    hash_password,
    normalize_username,
    validate_password,
    verify_password,
)


def test_password_hash_uses_random_salt_and_never_contains_password():
    password = "synthetic-password"
    first, second = hash_password(password), hash_password(password)
    assert first != second
    assert password not in first
    assert first.startswith("scrypt$32768$8$1$")
    assert verify_password(password, first)
    assert not verify_password("incorrect", first)


@pytest.mark.parametrize(
    "value", ["", "a", "ab", "a" * 33, "اسم", "a b", " abc", "abc ", "a@b", "Ａbc"]
)
def test_username_rejects_invalid_format(value):
    with pytest.raises(ValueError):
        normalize_username(value)


@pytest.mark.parametrize("value", ["AbC", "A_1.z-9", "A" * 32])
def test_username_normalizes_ascii_identity(value):
    assert normalize_username(value) == value.lower()


def test_password_minimum_is_eight_characters_without_trimming():
    with pytest.raises(ValueError, match="8"):
        validate_password("1234567")
    validate_password("12345678")
    validate_password(" 123456 ")
    with pytest.raises(ValueError):
        validate_password("password\ud800")
    assert not verify_password("password\ud800", hash_password("password"))


@pytest.mark.parametrize(
    "encoded", ["", "invalid", "scrypt$1073741824$8$1$00$00", "scrypt$32768$8$1$zz$zz"]
)
def test_corrupt_hash_is_rejected_without_unbounded_work(encoded, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("invalid encoded parameters must not reach scrypt")

    monkeypatch.setattr(hashlib, "scrypt", unexpected)
    assert not verify_password("synthetic-password", encoded)
