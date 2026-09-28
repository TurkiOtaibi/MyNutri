from uuid import uuid4

import httpx

from app.services.admin_auth import SupabaseAdminClient


def test_admin_create_sends_preassigned_uuid_without_exposing_password() -> None:
    auth_id = uuid4()
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": str(auth_id), "email": "new@example.com"})

    client = SupabaseAdminClient(
        base_url="http://localhost:54321",
        service_key="synthetic-secret",
        timeout_seconds=3,
        transport=httpx.MockTransport(respond),
        allow_loopback_http=True,
    )
    identity = client.create_user(auth_id, "new@example.com", "synthetic-password")
    assert identity.id == auth_id
    assert len(requests) == 1
    assert requests[0].url.path == "/auth/v1/admin/users"
    assert requests[0].read().decode().find(f'"id":"{auth_id}"') >= 0
    assert "synthetic-password" not in repr(client)


def test_admin_delete_then_get_404_is_verified_absent() -> None:
    auth_id = uuid4()
    methods: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return httpx.Response(404, json={"code": "user_not_found"})

    client = SupabaseAdminClient(
        base_url="http://localhost:54321",
        service_key="synthetic-secret",
        timeout_seconds=3,
        transport=httpx.MockTransport(respond),
        allow_loopback_http=True,
    )
    client.delete_user(auth_id)
    assert client.get_user_by_id(auth_id) is None
    assert methods == ["DELETE", "GET"]
