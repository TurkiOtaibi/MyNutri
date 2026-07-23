from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import jwt
from jwt import PyJWK, PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

_SUPPORTED_SIGNING_ALGORITHMS = frozenset({"ES256", "RS256"})
_LOOKUP_FAILURE_MESSAGE = "Unable to resolve a signing key."
_CONNECTION_FAILURE_MESSAGE = "Unable to refresh signing keys."


@dataclass(frozen=True, slots=True)
class _JwksSnapshot:
    keys: Mapping[str, PyJWK]
    expires_at: float


class RotationSafeJwksClient:
    """Bound JWKS refreshes while retaining fail-closed key rotation.

    ``PyJWK.from_dict`` and ``PyJWKClient.fetch_data`` are public APIs verified by
    the dependency-floor tests against the declared minimum, PyJWT 2.10.1.
    """

    def __init__(
        self,
        uri: str,
        *,
        timeout_seconds: int,
        cache_lifespan_seconds: int,
        refresh_cooldown_seconds: int,
        negative_cache_ttl_seconds: int,
        negative_cache_max_entries: int,
        max_keys: int,
        kid_max_length: int,
        fetcher: Callable[[], Any] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._cache_lifespan_seconds = cache_lifespan_seconds
        self._refresh_cooldown_seconds = refresh_cooldown_seconds
        self._negative_cache_ttl_seconds = negative_cache_ttl_seconds
        self._negative_cache_max_entries = negative_cache_max_entries
        self._max_keys = max_keys
        self._kid_max_length = kid_max_length
        self._clock = clock or time.monotonic

        if fetcher is None:
            library_client = PyJWKClient(
                uri,
                cache_jwk_set=False,
                cache_keys=False,
                timeout=timeout_seconds,
            )
            fetcher = library_client.fetch_data
        self._fetcher = fetcher

        self._condition = threading.Condition()
        self._snapshot: _JwksSnapshot | None = None
        self._refresh_in_flight = False
        self._refresh_generation = 0
        self._last_completed_generation = 0
        self._last_completed_failure: type[PyJWKClientError] | None = None
        self._next_refresh_allowed = 0.0
        self._negative_cache: OrderedDict[str, float] = OrderedDict()

    def get_signing_key_from_jwt(self, token: str | bytes) -> PyJWK:
        kid = self._validated_kid(token)

        while True:
            with self._condition:
                key = self._unexpired_key(kid, self._clock())
                if key is not None:
                    return key
                now = self._clock()
                if self._is_negative_cached(kid, now):
                    raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)

                if self._refresh_in_flight:
                    captured_generation = self._refresh_generation
                    completed = self._condition.wait_for(
                        lambda: self._last_completed_generation >= captured_generation,
                        timeout=float(self._timeout_seconds),
                    )
                    if not completed:
                        raise PyJWKClientConnectionError(_CONNECTION_FAILURE_MESSAGE)
                    if (
                        self._last_completed_generation == captured_generation
                        and self._last_completed_failure is not None
                    ):
                        raise self._last_completed_failure(
                            self._failure_message(self._last_completed_failure)
                        )
                    continue

                if now < self._next_refresh_allowed:
                    raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)

                self._refresh_generation += 1
                owned_generation = self._refresh_generation
                self._refresh_in_flight = True
                self._next_refresh_allowed = now + self._refresh_cooldown_seconds

            snapshot: _JwksSnapshot | None = None
            failure_type: type[PyJWKClientError] | None = None
            failure_cause: Exception | None = None
            try:
                try:
                    document = self._fetcher()
                except Exception as error:
                    failure_type = (
                        PyJWKClientError
                        if isinstance(error, json.JSONDecodeError)
                        else PyJWKClientConnectionError
                    )
                    failure_cause = error
                else:
                    try:
                        snapshot = self._build_snapshot(document)
                    except Exception as error:
                        failure_type = PyJWKClientError
                        failure_cause = error
            finally:
                with self._condition:
                    if snapshot is not None:
                        self._snapshot = snapshot
                        if kid not in snapshot.keys:
                            self._record_negative(kid, self._clock())
                    self._last_completed_generation = owned_generation
                    self._last_completed_failure = failure_type
                    self._refresh_in_flight = False
                    self._condition.notify_all()

            if failure_type is not None:
                raise failure_type(self._failure_message(failure_type)) from failure_cause

    def _validated_kid(self, token: str | bytes) -> str:
        try:
            header = jwt.get_unverified_header(token)
        except Exception as error:
            raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE) from error
        kid = header.get("kid")
        if header.get("alg") not in _SUPPORTED_SIGNING_ALGORITHMS:
            raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
        if not isinstance(kid, str) or not kid or len(kid) > self._kid_max_length:
            raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
        return kid

    def _build_snapshot(self, document: Any) -> _JwksSnapshot:
        if not isinstance(document, dict):
            raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
        raw_keys = document.get("keys")
        if not isinstance(raw_keys, list) or not raw_keys:
            raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
        if len(raw_keys) > self._max_keys:
            raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)

        parsed_keys: dict[str, PyJWK] = {}
        seen_kids: set[str] = set()
        for raw_key in raw_keys:
            if not isinstance(raw_key, dict):
                raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
            if raw_key.get("use") not in (None, "sig"):
                continue
            kid = raw_key.get("kid")
            if not isinstance(kid, str) or not kid or len(kid) > self._kid_max_length:
                raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
            if kid in seen_kids:
                raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
            seen_kids.add(kid)
            try:
                parsed_key = PyJWK.from_dict(raw_key)
            except Exception as error:
                raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE) from error
            if parsed_key.algorithm_name not in _SUPPORTED_SIGNING_ALGORITHMS:
                continue
            parsed_keys[kid] = parsed_key

        if not parsed_keys:
            raise PyJWKClientError(_LOOKUP_FAILURE_MESSAGE)
        return _JwksSnapshot(
            keys=MappingProxyType(parsed_keys),
            expires_at=self._clock() + self._cache_lifespan_seconds,
        )

    def _unexpired_key(self, kid: str, now: float) -> PyJWK | None:
        snapshot = self._snapshot
        if snapshot is None or now >= snapshot.expires_at:
            return None
        return snapshot.keys.get(kid)

    def _is_negative_cached(self, kid: str, now: float) -> bool:
        expires_at = self._negative_cache.get(kid)
        if expires_at is None:
            return False
        if now >= expires_at:
            del self._negative_cache[kid]
            return False
        self._negative_cache.move_to_end(kid)
        return True

    def _record_negative(self, kid: str, now: float) -> None:
        self._negative_cache[kid] = now + self._negative_cache_ttl_seconds
        self._negative_cache.move_to_end(kid)
        while len(self._negative_cache) > self._negative_cache_max_entries:
            self._negative_cache.popitem(last=False)

    @staticmethod
    def _failure_message(failure_type: type[PyJWKClientError]) -> str:
        if failure_type is PyJWKClientConnectionError:
            return _CONNECTION_FAILURE_MESSAGE
        return _LOOKUP_FAILURE_MESSAGE
