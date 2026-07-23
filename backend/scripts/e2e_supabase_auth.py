"""Local-only Supabase Auth fixture used by Playwright and CI.

It issues short-lived signed JWTs and publishes a JWKS endpoint. It refuses
non-loopback binding and never contains production credentials.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4, uuid5

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ADMIN_ID = UUID("10000000-0000-0000-0000-000000000001")
NAMESPACE = UUID("10000000-0000-0000-0000-000000000000")
ADMIN_EMAIL = "admin.e2e@example.test"
ADMIN_PASSWORD = "E2e-only-password-2026!"


def _b64(value: int) -> str:
    return jwt.utils.base64url_encode(value.to_bytes((value.bit_length() + 7) // 8, "big")).decode()


class AuthState:
    def __init__(self, issuer: str) -> None:
        self.issuer = issuer.rstrip("/") + "/auth/v1"
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = self.key.public_key().public_numbers()
        self.jwks = {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": "mynutri-e2e",
                    "use": "sig",
                    "alg": "RS256",
                    "n": _b64(public.n),
                    "e": _b64(public.e),
                }
            ]
        }

    def user_for_email(self, email: str) -> dict[str, object]:
        normalized = email.strip().lower()
        user_id = ADMIN_ID if normalized == ADMIN_EMAIL else uuid5(NAMESPACE, normalized)
        return {
            "id": str(user_id),
            "aud": "authenticated",
            "role": "authenticated",
            "email": normalized,
            "email_confirmed_at": datetime.now(timezone.utc).isoformat(),
            "user_metadata": {"display_name": "مشرف الاختبار" if user_id == ADMIN_ID else "مستخدم الاختبار"},
            "app_metadata": {"provider": "email", "providers": ["email"]},
        }

    def session(self, email: str) -> dict[str, object]:
        user = self.user_for_email(email)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=2)
        token = jwt.encode(
            {
                "sub": user["id"],
                "email": user["email"],
                "aud": "authenticated",
                "iss": self.issuer,
                "iat": int(now.timestamp()),
                "exp": int(expires.timestamp()),
                "jti": str(uuid4()),
                "user_metadata": user["user_metadata"],
            },
            self.key,
            algorithm="RS256",
            headers={"kid": "mynutri-e2e"},
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 7200,
            "expires_at": int(expires.timestamp()),
            "refresh_token": f"e2e-refresh:{user['email']}",
            "user": user,
        }


class Handler(BaseHTTPRequestHandler):
    state: AuthState

    def _json(self) -> dict[str, object]:
        length = int(self.headers.get("content-length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _send(self, status: int, payload: object | None = None) -> None:
        self.send_response(status)
        self.send_header("access-control-allow-origin", self.headers.get("origin", "http://127.0.0.1:3000"))
        self.send_header("access-control-allow-credentials", "true")
        self.send_header(
            "access-control-allow-headers",
            "authorization, apikey, content-type, x-client-info, x-supabase-api-version",
        )
        self.send_header("access-control-allow-methods", "GET, POST, PUT, OPTIONS")
        if payload is None:
            self.end_headers()
            return
        body = json.dumps(payload).encode()
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/auth/v1/.well-known/jwks.json":
            self._send(200, self.state.jwks)
        elif path == "/health":
            self._send(200, {"ok": True})
        elif path == "/auth/v1/user":
            self._send(200, self.state.user_for_email(ADMIN_EMAIL))
        else:
            self._send(404, {"message": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        payload = self._json()
        if parsed.path == "/auth/v1/token":
            grant = parse_qs(parsed.query).get("grant_type", [""])[0]
            if grant == "password":
                email = str(payload.get("email", ""))
                password = str(payload.get("password", ""))
                if not email or (email == ADMIN_EMAIL and password != ADMIN_PASSWORD):
                    self._send(400, {"message": "Invalid login credentials"})
                    return
                self._send(200, self.state.session(email))
                return
            if grant == "refresh_token":
                refresh = str(payload.get("refresh_token", ""))
                email = refresh.removeprefix("e2e-refresh:") or ADMIN_EMAIL
                self._send(200, self.state.session(email))
                return
        if parsed.path == "/auth/v1/signup":
            self._send(200, self.state.session(str(payload.get("email", "user.e2e@example.test"))))
            return
        if parsed.path in {"/auth/v1/recover", "/auth/v1/logout"}:
            self._send(200, {})
            return
        self._send(404, {"message": "not found"})

    def do_PUT(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/auth/v1/user":
            self._send(200, self.state.user_for_email(ADMIN_EMAIL))
        else:
            self._send(404, {"message": "not found"})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("The E2E Auth fixture may bind only to loopback.")
    issuer = f"http://127.0.0.1:{args.port}"
    Handler.state = AuthState(issuer)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
