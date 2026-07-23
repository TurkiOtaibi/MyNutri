from __future__ import annotations

import base64
import json
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from pydantic import ValidationError

from app.core.auth import SupabaseTokenVerifier, get_token_verifier
from app.core.config import Settings
from app.core.jwks import RotationSafeJwksClient


class FakeClock:
    def __init__(self) -> None:
        self._value = 0.0
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            return self._value

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._value += seconds


class FakeFetcher:
    def __init__(self, *responses: Any) -> None:
        self._responses = deque(responses)
        self._lock = threading.Lock()
        self.calls = 0

    def __call__(self) -> Any:
        with self._lock:
            self.calls += 1
            response = self._responses.popleft()
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            return response()
        return response


@dataclass
class BlockingResponse:
    response: Any
    started: threading.Event
    release: threading.Event

    def __call__(self) -> Any:
        self.started.set()
        if not self.release.wait(timeout=3):
            raise TimeoutError("test release was not signaled")
        return self.response


PRIVATE_A = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_B = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_EC = ec.generate_private_key(ec.SECP256R1())


def _jwk(private_key: Any, kid: str, **overrides: Any) -> dict[str, Any]:
    document = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    document.update({"kid": kid, "use": "sig", "alg": "RS256"})
    document.update(overrides)
    return document


KEY_A = _jwk(PRIVATE_A, "a")
KEY_B = _jwk(PRIVATE_B, "b")
KEY_EC = {
    **json.loads(ECAlgorithm.to_jwk(PRIVATE_EC.public_key())),
    "kid": "e",
    "use": "sig",
    "alg": "ES256",
}


def _document(*keys: dict[str, Any]) -> dict[str, Any]:
    return {"keys": list(keys)}


def _token(kid: Any = "a", *, include_kid: bool = True, **headers: Any) -> str:
    token_headers = {"alg": "RS256", "typ": "JWT", **headers}
    if include_kid:
        token_headers["kid"] = kid
    encoded_header = base64.urlsafe_b64encode(
        json.dumps(token_headers).encode()
    ).rstrip(b"=")
    return f"{encoded_header.decode()}.e30.c2ln"


def _client(
    fetcher: FakeFetcher,
    clock: FakeClock,
    *,
    timeout: int = 1,
    lifespan: int = 60,
    cooldown: int = 5,
    negative_ttl: int = 5,
    negative_max_entries: int = 16,
    max_keys: int = 4,
    kid_max_length: int = 8,
) -> RotationSafeJwksClient:
    return RotationSafeJwksClient(
        "https://project.supabase.co/auth/v1/.well-known/jwks.json",
        timeout_seconds=timeout,
        cache_lifespan_seconds=lifespan,
        refresh_cooldown_seconds=cooldown,
        negative_cache_ttl_seconds=negative_ttl,
        negative_cache_max_entries=negative_max_entries,
        max_keys=max_keys,
        kid_max_length=kid_max_length,
        fetcher=fetcher,
        clock=clock,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("supabase_jwks_timeout_seconds", 0),
        ("supabase_jwks_timeout_seconds", -1),
        ("supabase_jwks_timeout_seconds", 31),
        ("supabase_jwks_cache_lifespan_seconds", 59),
        ("supabase_jwks_cache_lifespan_seconds", -1),
        ("supabase_jwks_cache_lifespan_seconds", 86_401),
        ("supabase_jwks_refresh_cooldown_seconds", 0),
        ("supabase_jwks_refresh_cooldown_seconds", -1),
        ("supabase_jwks_refresh_cooldown_seconds", 301),
        ("supabase_jwks_negative_cache_ttl_seconds", 0),
        ("supabase_jwks_negative_cache_ttl_seconds", 301),
        ("supabase_jwks_negative_cache_max_entries", 0),
        ("supabase_jwks_negative_cache_max_entries", 4_097),
        ("supabase_jwks_max_keys", 0),
        ("supabase_jwks_max_keys", -1),
        ("supabase_jwks_max_keys", 129),
        ("supabase_jwt_kid_max_length", 0),
        ("supabase_jwt_kid_max_length", -1),
        ("supabase_jwt_kid_max_length", 1_025),
    ],
)
def test_jwks_settings_configuration_rejects_out_of_range(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})


def test_jwks_settings_configuration_rejects_lifespan_shorter_than_cooldown() -> None:
    with pytest.raises(ValidationError, match="cache lifespan"):
        Settings(
            supabase_jwks_cache_lifespan_seconds=60,
            supabase_jwks_refresh_cooldown_seconds=61,
        )


def test_jwks_settings_configuration_rejects_lifespan_shorter_than_negative_ttl() -> None:
    with pytest.raises(ValidationError, match="negative cache TTL"):
        Settings(
            supabase_jwks_cache_lifespan_seconds=60,
            supabase_jwks_negative_cache_ttl_seconds=61,
        )


@pytest.mark.parametrize(
    "token",
    [
        _token(include_kid=False),
        _token(""),
        _token(7),
        _token("123456789"),
        "not-a-jwt",
    ],
)
def test_header_kid_invalid_values_fail_before_fetch(token: str) -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A))
    client = _client(fetcher, clock)
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(token)
    assert fetcher.calls == 0


@pytest.mark.parametrize("algorithm", ["HS256", "none", "RS512", "", None])
def test_header_unsupported_algorithm_fails_before_fetch(algorithm: Any) -> None:
    fetcher = FakeFetcher(_document(KEY_A))
    client = _client(fetcher, FakeClock())
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token(alg=algorithm))
    assert fetcher.calls == 0


def test_header_kid_at_limit_is_accepted_and_jku_is_ignored() -> None:
    clock = FakeClock()
    key = _jwk(PRIVATE_A, "12345678")
    fetcher = FakeFetcher(_document(key))
    client = _client(fetcher, clock)
    signing_key = client.get_signing_key_from_jwt(
        _token("12345678", jku="https://attacker.example/jwks")
    )
    assert signing_key.key_id == "12345678"
    assert fetcher.calls == 1


@pytest.mark.parametrize(
    ("key", "kid", "matching_algorithm", "mismatched_algorithm"),
    [
        (KEY_A, "a", "RS256", "ES256"),
        (KEY_EC, "e", "ES256", "RS256"),
    ],
)
def test_warm_key_algorithm_mismatch_fails_without_refresh(
    key: dict[str, Any],
    kid: str,
    matching_algorithm: str,
    mismatched_algorithm: str,
) -> None:
    fetcher = FakeFetcher(_document(key))
    client = _client(fetcher, FakeClock())
    assert (
        client.get_signing_key_from_jwt(_token(kid, alg=matching_algorithm)).key_id
        == kid
    )
    with pytest.raises(PyJWKClientError, match="Unable to resolve a signing key"):
        client.get_signing_key_from_jwt(_token(kid, alg=mismatched_algorithm))
    assert fetcher.calls == 1


def test_document_jwks_limit_exact_is_accepted_and_one_over_is_rejected() -> None:
    clock = FakeClock()
    exact = [_jwk(PRIVATE_A, f"k{index}") for index in range(4)]
    fetcher = FakeFetcher(_document(*exact))
    client = _client(fetcher, clock, max_keys=4)
    assert client.get_signing_key_from_jwt(_token("k3")).key_id == "k3"

    over_fetcher = FakeFetcher(_document(*exact, _jwk(PRIVATE_A, "overflow")))
    over_client = _client(over_fetcher, FakeClock(), max_keys=4)
    with pytest.raises(PyJWKClientError):
        over_client.get_signing_key_from_jwt(_token("k3"))
    assert over_fetcher.calls == 1


@pytest.mark.parametrize(
    "bad_document",
    [
        None,
        [],
        {},
        {"keys": []},
        {"keys": ["bad"]},
        _document({**KEY_A, "kid": ""}),
        _document({**KEY_A, "kid": "123456789"}),
        _document({**KEY_A, "use": "enc"}),
        _document({**KEY_A, "kty": "invalid"}),
    ],
)
def test_document_malformed_or_unusable_fails_closed(bad_document: Any) -> None:
    fetcher = FakeFetcher(bad_document)
    client = _client(fetcher, FakeClock())
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token())
    assert fetcher.calls == 1


@pytest.mark.parametrize(
    "duplicate_document",
    [
        _document(KEY_A, _jwk(PRIVATE_B, "a")),
        _document({**KEY_A, "alg": "RS512"}, KEY_A),
    ],
)
def test_document_duplicate_kid_is_rejected(
    duplicate_document: dict[str, Any],
) -> None:
    fetcher = FakeFetcher(duplicate_document)
    client = _client(fetcher, FakeClock())
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token())
    assert fetcher.calls == 1


def test_invalid_document_preserves_valid_snapshot_and_consumes_cooldown() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A), {"keys": []}, _document(KEY_A, KEY_B))
    client = _client(fetcher, clock)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    clock.advance(5)
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("b"))
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("b"))
    assert fetcher.calls == 2


def test_cache_cold_known_key_and_exact_ttl_refresh_counts() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A), _document(KEY_A))
    client = _client(fetcher, clock, lifespan=60)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    assert fetcher.calls == 1
    clock.advance(60)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    assert fetcher.calls == 2


def test_cooldown_unknown_kids_are_globally_bounded_at_exact_boundary() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A), _document(KEY_A), _document(KEY_A))
    client = _client(fetcher, clock)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    for kid in ("b", "b", "c", "d"):
        with pytest.raises(PyJWKClientError):
            client.get_signing_key_from_jwt(_token(kid))
    assert fetcher.calls == 1
    clock.advance(5)
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("b"))
    assert fetcher.calls == 2
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("c"))
    assert fetcher.calls == 2
    clock.advance(5)
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("d"))
    assert fetcher.calls == 3


def test_negative_cache_is_bounded_and_evicts_oldest_kid() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(*[_document(KEY_A) for _ in range(5)])
    client = _client(
        fetcher,
        clock,
        cooldown=1,
        negative_ttl=10,
        negative_max_entries=3,
    )
    for kid in ("u0", "u1", "u2", "u3", "u4"):
        with pytest.raises(PyJWKClientError):
            client.get_signing_key_from_jwt(_token(kid))
        clock.advance(1)
        assert len(client._negative_cache) <= 3
    assert list(client._negative_cache) == ["u2", "u3", "u4"]
    assert fetcher.calls == 5


def test_negative_cache_ttl_expiry_permits_rotation_recovery() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A), _document(KEY_A, KEY_B))
    client = _client(fetcher, clock, cooldown=5, negative_ttl=10)
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("b"))
    assert fetcher.calls == 1
    clock.advance(5)
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("b"))
    assert fetcher.calls == 1
    clock.advance(5)
    assert client.get_signing_key_from_jwt(_token("b")).key_id == "b"
    assert fetcher.calls == 2


@pytest.mark.parametrize("failure", [TimeoutError("timeout"), RuntimeError("transport")])
def test_cache_connection_failure_consumes_cooldown(failure: Exception) -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(failure, _document(KEY_A))
    client = _client(fetcher, clock)
    with pytest.raises(PyJWKClientConnectionError):
        client.get_signing_key_from_jwt(_token("a"))
    with pytest.raises(PyJWKClientError) as suppressed:
        client.get_signing_key_from_jwt(_token("a"))
    assert type(suppressed.value) is PyJWKClientError
    assert fetcher.calls == 1
    clock.advance(5)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    assert fetcher.calls == 2


def test_cache_json_parse_failure_is_normalized_and_consumes_cooldown() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(json.JSONDecodeError("invalid", "", 0), _document(KEY_A))
    client = _client(fetcher, clock)
    with pytest.raises(PyJWKClientError) as failure:
        client.get_signing_key_from_jwt(_token("a"))
    assert type(failure.value) is PyJWKClientError
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("a"))
    assert fetcher.calls == 1
    clock.advance(5)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    assert fetcher.calls == 2


def test_cache_failed_unknown_refresh_preserves_unexpired_known_key() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A), TimeoutError("provider unavailable"))
    client = _client(fetcher, clock)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    clock.advance(5)
    with pytest.raises(PyJWKClientConnectionError):
        client.get_signing_key_from_jwt(_token("b"))
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    assert fetcher.calls == 2


def test_cache_expired_snapshot_never_accepts_stale_key_after_failure() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A), TimeoutError("provider unavailable"))
    client = _client(fetcher, clock, lifespan=60)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    clock.advance(60)
    with pytest.raises(PyJWKClientConnectionError):
        client.get_signing_key_from_jwt(_token("a"))
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("a"))
    assert fetcher.calls == 2


def _join_threads(threads: list[threading.Thread]) -> None:
    for thread in threads:
        thread.join(timeout=3)
    assert not any(thread.is_alive() for thread in threads)


def test_singleflight_concurrent_rotation_has_one_fetch_and_all_succeed() -> None:
    clock = FakeClock()
    started = threading.Event()
    release = threading.Event()
    fetcher = FakeFetcher(
        _document(KEY_A),
        BlockingResponse(_document(KEY_A, KEY_B), started, release),
    )
    client = _client(fetcher, clock)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    clock.advance(5)
    barrier = threading.Barrier(9)
    results: list[str] = []
    errors: list[Exception] = []

    def resolve() -> None:
        barrier.wait()
        try:
            results.append(client.get_signing_key_from_jwt(_token("b")).key_id)
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=resolve) for _ in range(8)]
    for thread in threads:
        thread.start()
    barrier.wait()
    assert started.wait(timeout=3)
    release.set()
    _join_threads(threads)
    assert errors == []
    assert results == ["b"] * 8
    assert fetcher.calls == 2


def test_singleflight_fifty_concurrent_same_unknown_kid_fetch_once() -> None:
    clock = FakeClock()
    started = threading.Event()
    release = threading.Event()
    fetcher = FakeFetcher(BlockingResponse(_document(KEY_A), started, release))
    client = _client(fetcher, clock)
    barrier = threading.Barrier(51)
    errors: list[Exception] = []

    def resolve() -> None:
        barrier.wait()
        try:
            client.get_signing_key_from_jwt(_token("missing"))
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=resolve) for _ in range(50)]
    for thread in threads:
        thread.start()
    barrier.wait()
    assert started.wait(timeout=3)
    release.set()
    _join_threads(threads)
    assert len(errors) == 50
    assert all(type(error) is PyJWKClientError for error in errors)
    assert fetcher.calls == 1


def test_singleflight_concurrent_random_unknown_kids_share_one_fetch_and_fail() -> None:
    clock = FakeClock()
    started = threading.Event()
    release = threading.Event()
    fetcher = FakeFetcher(BlockingResponse(_document(KEY_A), started, release))
    client = _client(fetcher, clock)
    barrier = threading.Barrier(9)
    errors: list[Exception] = []

    def resolve(index: int) -> None:
        barrier.wait()
        try:
            client.get_signing_key_from_jwt(_token(f"u{index}"))
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=resolve, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    barrier.wait()
    assert started.wait(timeout=3)
    release.set()
    _join_threads(threads)
    assert len(errors) == 8
    assert all(isinstance(error, PyJWKClientError) for error in errors)
    assert fetcher.calls == 1


def test_concurrent_known_unexpired_key_returns_during_blocked_refresh() -> None:
    clock = FakeClock()
    started = threading.Event()
    release = threading.Event()
    fetcher = FakeFetcher(
        _document(KEY_A),
        BlockingResponse(_document(KEY_A), started, release),
    )
    client = _client(fetcher, clock)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    clock.advance(5)
    owner_error: list[Exception] = []

    def refresh_unknown() -> None:
        try:
            client.get_signing_key_from_jwt(_token("b"))
        except Exception as error:
            owner_error.append(error)

    owner = threading.Thread(target=refresh_unknown)
    owner.start()
    assert started.wait(timeout=3)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    release.set()
    _join_threads([owner])
    assert len(owner_error) == 1
    assert fetcher.calls == 2


@pytest.mark.parametrize(
    ("shared_failure", "expected_type"),
    [
        (TimeoutError("connection"), PyJWKClientConnectionError),
        ({"keys": []}, PyJWKClientError),
        (RuntimeError("unexpected"), PyJWKClientConnectionError),
    ],
)
def test_singleflight_failure_notifies_waiters_with_same_normalized_class(
    shared_failure: Any,
    expected_type: type[Exception],
) -> None:
    clock = FakeClock()
    started = threading.Event()
    release = threading.Event()

    def blocked_failure() -> Any:
        started.set()
        assert release.wait(timeout=3)
        if isinstance(shared_failure, BaseException):
            raise shared_failure
        return shared_failure

    fetcher = FakeFetcher(blocked_failure)
    client = _client(fetcher, clock)
    waiter_entered = threading.Event()
    original_wait_for = client._condition.wait_for

    def tracked_wait_for(
        predicate: Callable[[], bool], timeout: float | None = None
    ) -> bool:
        waiter_entered.set()
        return original_wait_for(predicate, timeout)

    client._condition.wait_for = tracked_wait_for
    errors: list[Exception] = []

    def resolve() -> None:
        try:
            client.get_signing_key_from_jwt(_token("a"))
        except Exception as error:
            errors.append(error)

    owner = threading.Thread(target=resolve)
    owner.start()
    assert started.wait(timeout=3)
    waiter = threading.Thread(target=resolve)
    waiter.start()
    assert waiter_entered.wait(timeout=3)
    release.set()
    _join_threads([owner, waiter])
    assert len(errors) == 2
    assert all(type(error) is expected_type for error in errors)
    assert fetcher.calls == 1


def test_singleflight_waiter_timeout_is_bounded_and_does_not_clear_owner() -> None:
    clock = FakeClock()
    started = threading.Event()
    release = threading.Event()
    fetcher = FakeFetcher(BlockingResponse(_document(KEY_A), started, release))
    client = _client(fetcher, clock, timeout=1)
    owner_errors: list[Exception] = []

    def owner() -> None:
        try:
            client.get_signing_key_from_jwt(_token("a"))
        except Exception as error:
            owner_errors.append(error)

    owner_thread = threading.Thread(target=owner)
    owner_thread.start()
    assert started.wait(timeout=3)
    with pytest.raises(PyJWKClientConnectionError):
        client.get_signing_key_from_jwt(_token("a"))
    assert owner_thread.is_alive()
    release.set()
    _join_threads([owner_thread])
    assert owner_errors == []
    assert fetcher.calls == 1


def test_rotation_retirement_replaces_snapshot_at_ttl_without_stale_acceptance() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(
        _document(KEY_A),
        _document(KEY_A, KEY_B),
        _document(KEY_B),
    )
    client = _client(fetcher, clock, lifespan=60, cooldown=5)
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    clock.advance(5)
    assert client.get_signing_key_from_jwt(_token("b")).key_id == "b"
    assert client.get_signing_key_from_jwt(_token("a")).key_id == "a"
    clock.advance(60)
    assert client.get_signing_key_from_jwt(_token("b")).key_id == "b"
    with pytest.raises(PyJWKClientError):
        client.get_signing_key_from_jwt(_token("a"))
    assert fetcher.calls == 3


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(TimeoutError("provider timeout"), id="timeout"),
        pytest.param(
            HTTPError(
                "https://project.supabase.co/auth/v1/.well-known/jwks.json",
                500,
                "Internal Server Error",
                None,
                None,
            ),
            id="http-500",
        ),
    ],
)
def test_outage_unknown_kid_fails_fast_with_generic_connection_error(
    failure: Exception,
) -> None:
    token = _token("unknown")
    fetcher = FakeFetcher(failure)
    client = _client(fetcher, FakeClock())
    with pytest.raises(
        PyJWKClientConnectionError, match="Unable to refresh signing keys"
    ) as error:
        client.get_signing_key_from_jwt(token)
    assert token not in str(error.value)
    assert "unknown" not in str(error.value)
    assert fetcher.calls == 1


def test_invalid_signature_does_not_trigger_refresh_storm() -> None:
    clock = FakeClock()
    fetcher = FakeFetcher(_document(KEY_A))
    client = _client(fetcher, clock)
    verifier = object.__new__(SupabaseTokenVerifier)
    verifier.issuer = "https://project.supabase.co/auth/v1"
    verifier.audience = "authenticated"
    verifier.jwks = client
    token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "iss": verifier.issuer,
            "aud": verifier.audience,
            "exp": 4_102_444_800,
        },
        PRIVATE_B,
        algorithm="RS256",
        headers={"kid": "a"},
    )
    for _ in range(20):
        with pytest.raises(jwt.InvalidSignatureError):
            verifier.verify(token)
    assert fetcher.calls == 1


def test_failures_do_not_log_raw_token_or_unverified_claims(caplog) -> None:
    token = _token("sensitive-kid")
    fetcher = FakeFetcher(TimeoutError("provider unavailable"))
    client = _client(fetcher, FakeClock(), kid_max_length=32)
    with pytest.raises(PyJWKClientConnectionError):
        client.get_signing_key_from_jwt(token)
    combined_logs = " ".join(record.getMessage() for record in caplog.records)
    assert token not in combined_logs
    assert "sensitive-kid" not in combined_logs


def test_verifier_cache_identity_includes_every_jwks_policy_setting() -> None:
    from app.core.auth import _cached_verifier

    _cached_verifier.cache_clear()
    common = {
        "environment": "test",
        "supabase_url": "https://project.supabase.co",
    }
    first = get_token_verifier(Settings(**common))
    variants = [
        Settings(**common, supabase_jwks_timeout_seconds=6),
        Settings(**common, supabase_jwks_cache_lifespan_seconds=601),
        Settings(**common, supabase_jwks_refresh_cooldown_seconds=31),
        Settings(**common, supabase_jwks_negative_cache_ttl_seconds=31),
        Settings(**common, supabase_jwks_negative_cache_max_entries=257),
        Settings(**common, supabase_jwks_max_keys=33),
        Settings(**common, supabase_jwt_kid_max_length=257),
    ]
    assert all(get_token_verifier(settings) is not first for settings in variants)
    assert get_token_verifier(Settings(**common)) is first
