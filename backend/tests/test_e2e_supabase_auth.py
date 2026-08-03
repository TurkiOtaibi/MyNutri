from __future__ import annotations

import json
from http.client import HTTPConnection
from threading import Thread

from scripts.e2e_supabase_auth import AuthState, Handler, ThreadingHTTPServer


def _request(
    server: ThreadingHTTPServer,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    body = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    data = json.loads(response.read() or b"{}")
    connection.close()
    return response.status, data


def _server() -> tuple[ThreadingHTTPServer, AuthState]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state = AuthState(f"http://127.0.0.1:{server.server_port}")
    Handler.state = state
    Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def test_recovery_requests_are_neutral_and_provider_errors_are_sanitized() -> None:
    server, state = _server()
    try:
        known = _request(server, "POST", "/auth/v1/recover", {"email": "admin.e2e@example.test"})
        unknown = _request(server, "POST", "/auth/v1/recover", {"email": "unknown@example.test"})
        provider_error = _request(
            server,
            "POST",
            "/auth/v1/recover",
            {"email": "provider-error-user@example.test"},
        )
        assert known == unknown == (200, {})
        assert provider_error[0] == 503
        assert state.request_records == [
            {"operation": "recover", "method": "POST", "path": "/auth/v1/recover", "status": 200},
            {"operation": "recover", "method": "POST", "path": "/auth/v1/recover", "status": 200},
            {"operation": "recover", "method": "POST", "path": "/auth/v1/recover", "status": 503},
        ]
        serialized = json.dumps(state.request_records)
        assert "admin.e2e" not in serialized
        assert "provider-error-user" not in serialized
    finally:
        server.shutdown()
        server.server_close()


def test_recovery_code_expiry_reuse_and_session_reuse_are_deterministic() -> None:
    server, state = _server()
    try:
        expired_status, _ = _request(
            server,
            "POST",
            "/auth/v1/verify",
            {"email": "admin.e2e@example.test", "token": "expired-code", "type": "recovery"},
        )
        assert expired_status == 403

        code = "valid-recovery-code-unit"
        verified_status, session = _request(
            server,
            "POST",
            "/auth/v1/verify",
            {"email": "admin.e2e@example.test", "token": code, "type": "recovery"},
        )
        reused_code_status, _ = _request(
            server,
            "POST",
            "/auth/v1/verify",
            {"email": "admin.e2e@example.test", "token": code, "type": "recovery"},
        )
        assert verified_status == 200
        assert reused_code_status == 403

        authorization = {"Authorization": f"Bearer {session['access_token']}"}
        updated_status, _ = _request(
            server, "PUT", "/auth/v1/user", {"password": "synthetic"}, authorization
        )
        reused_session_status, _ = _request(
            server, "PUT", "/auth/v1/user", {"password": "synthetic"}, authorization
        )
        missing_session_status, _ = _request(
            server, "PUT", "/auth/v1/user", {"password": "synthetic"}
        )
        assert updated_status == 200
        assert reused_session_status == 401
        assert missing_session_status == 401

        serialized = json.dumps(state.request_records)
        assert code not in serialized
        assert "synthetic" not in serialized
        assert "access_token" not in serialized
        assert "authorization" not in serialized.lower()
    finally:
        server.shutdown()
        server.server_close()
