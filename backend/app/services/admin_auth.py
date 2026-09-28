"""Backend-only, bounded Supabase Auth Admin API boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx
from fastapi import Depends

from app.core.config import Settings, get_settings, validate_supabase_base_url


@dataclass(frozen=True, slots=True)
class AdminIdentity:
    id: UUID
    email: str | None


class AdminAuthError(Exception):
    def __init__(self, kind: str = "unavailable") -> None:
        self.kind = kind
        super().__init__(kind)


class AdminAuthGateway(Protocol):
    def create_user(self, auth_id: UUID, email: str, password: str) -> AdminIdentity: ...

    def get_user_by_id(self, auth_id: UUID) -> AdminIdentity | None: ...

    def find_user_by_email(self, email: str) -> AdminIdentity | None: ...

    def reset_password(self, auth_id: UUID, password: str) -> None: ...

    def delete_user(self, auth_id: UUID) -> None: ...


class SupabaseAdminClient:
    def __init__(
        self,
        *,
        base_url: str,
        service_key: str,
        timeout_seconds: int,
        transport: httpx.BaseTransport | None = None,
        allow_loopback_http: bool = False,
    ) -> None:
        if not service_key:
            raise AdminAuthError("unavailable")
        try:
            base = validate_supabase_base_url(
                base_url, allow_loopback_http=allow_loopback_http
            )
        except ValueError as error:
            raise AdminAuthError("unavailable") from error
        self._url = f"{base}/auth/v1/admin/users"
        self._headers = {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
        }
        self._timeout = timeout_seconds
        self._transport = transport

    def _request(
        self, method: str, suffix: str = "", *, json: dict | None = None, params: dict | None = None
    ) -> httpx.Response:
        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.request(
                    method,
                    f"{self._url}{suffix}",
                    headers=self._headers,
                    json=json,
                    params=params,
                )
        except httpx.HTTPError as error:
            raise AdminAuthError("unavailable") from error
        if response.is_redirect:
            raise AdminAuthError("unavailable")
        return response

    @staticmethod
    def _identity(response: httpx.Response) -> AdminIdentity:
        try:
            payload = response.json()
            return AdminIdentity(UUID(payload["id"]), payload.get("email"))
        except (ValueError, TypeError, KeyError) as error:
            raise AdminAuthError("unavailable") from error

    @staticmethod
    def _error_kind(response: httpx.Response) -> str:
        try:
            code = str(response.json().get("code", "")).lower()
        except (ValueError, TypeError, AttributeError):
            code = ""
        if code in {"email_exists", "user_already_exists"}:
            return "duplicate_email"
        if code in {"weak_password", "password_too_short", "validation_failed"}:
            return "password_rejected"
        return "unavailable"

    def create_user(self, auth_id: UUID, email: str, password: str) -> AdminIdentity:
        response = self._request(
            "POST",
            json={"id": str(auth_id), "email": email, "password": password, "email_confirm": True},
        )
        if response.status_code != 200:
            raise AdminAuthError(self._error_kind(response))
        identity = self._identity(response)
        if identity.id != auth_id:
            raise AdminAuthError("unavailable")
        return identity

    def get_user_by_id(self, auth_id: UUID) -> AdminIdentity | None:
        response = self._request("GET", f"/{auth_id}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise AdminAuthError("unavailable")
        return self._identity(response)

    def find_user_by_email(self, email: str) -> AdminIdentity | None:
        normalized = email.casefold()
        for page in range(1, 10_001):
            response = self._request("GET", params={"page": page, "per_page": 100})
            if response.status_code != 200:
                raise AdminAuthError("unavailable")
            try:
                users = response.json()["users"]
                if not isinstance(users, list):
                    raise TypeError
                for user in users:
                    if str(user.get("email", "")).casefold() == normalized:
                        return AdminIdentity(UUID(user["id"]), user.get("email"))
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                raise AdminAuthError("unavailable") from error
            if len(users) < 100:
                return None
        raise AdminAuthError("unavailable")

    def reset_password(self, auth_id: UUID, password: str) -> None:
        response = self._request("PUT", f"/{auth_id}", json={"password": password})
        if response.status_code != 200:
            raise AdminAuthError(self._error_kind(response))

    def delete_user(self, auth_id: UUID) -> None:
        response = self._request("DELETE", f"/{auth_id}", json={"should_soft_delete": False})
        if response.status_code not in {200, 204, 404}:
            raise AdminAuthError("unavailable")


def get_admin_auth_gateway(settings: Settings = Depends(get_settings)) -> AdminAuthGateway:
    key = settings.supabase_service_role_key
    if key is None:
        raise AdminAuthError("unavailable")
    return SupabaseAdminClient(
        base_url=settings.supabase_url,
        service_key=key.get_secret_value(),
        timeout_seconds=settings.supabase_admin_http_timeout_seconds,
        allow_loopback_http=settings.environment != "production",
    )
