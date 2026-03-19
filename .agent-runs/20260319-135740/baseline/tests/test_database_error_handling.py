from __future__ import annotations

import asyncio
import json
import unittest

from sqlalchemy.exc import OperationalError

from app.main import app
from app.presentation.dependencies.auth import get_password_reset_service


class _FailingPasswordResetService:
    def request_password_reset(self, email: str, reset_link_base_url: str) -> None:
        raise OperationalError("SELECT 1", {}, Exception("database unavailable"))


async def _send_request(
    method: str,
    path: str,
    *,
    body: bytes = b"",
    content_type: str | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    messages: list[dict] = []
    headers = [(b"host", b"testserver")]
    if content_type is not None:
        headers.append((b"content-type", content_type.encode("latin-1")))
    if body:
        headers.append((b"content-length", str(len(body)).encode("latin-1")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }

    sent = False

    async def receive() -> dict:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    await app(scope, receive, send)

    start = next(message for message in messages if message["type"] == "http.response.start")
    response_headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start.get("headers", [])
    }
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], response_body, response_headers


class DatabaseErrorHandlingTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_password_reset_service] = lambda: _FailingPasswordResetService()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_web_forgot_password_returns_503_when_database_is_unavailable(self) -> None:
        status_code, body, _ = asyncio.run(
            _send_request(
                "POST",
                "/forgot-password",
                body=b"email=person%40example.com",
                content_type="application/x-www-form-urlencoded",
            )
        )

        self.assertEqual(status_code, 503)
        self.assertIn("Database is unavailable", body.decode("utf-8"))

    def test_api_forgot_password_returns_503_when_database_is_unavailable(self) -> None:
        status_code, body, headers = asyncio.run(
            _send_request(
                "POST",
                "/api/v1/auth/forgot-password",
                body=json.dumps({"email": "person@example.com"}).encode("utf-8"),
                content_type="application/json",
            )
        )

        self.assertEqual(status_code, 503)
        self.assertEqual(headers.get("content-type"), "application/json")
        self.assertEqual(
            json.loads(body.decode("utf-8")),
            {"detail": "Database is unavailable. Start PostgreSQL and try again."},
        )


if __name__ == "__main__":
    unittest.main()
