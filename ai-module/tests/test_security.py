import unittest
from unittest.mock import Mock

from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.core.config import load_settings
from src.core.security import require_internal_token


class InternalTokenTests(unittest.TestCase):
    def setUp(self):
        self.token = "test-only-internal-token"
        settings = load_settings(env_file=None, environ={
            "AI_INTERNAL_TOKEN": self.token,
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_MODEL": "text-embedding-3-small",
        })
        self.application = create_app(lambda: settings)
        self.handler = Mock()
        # Only this test application exposes the probe; no fake business API.
        router = APIRouter(dependencies=[Depends(require_internal_token)])

        @router.api_route("/internal/auth-probe", methods=["POST", "DELETE"])
        async def probe():
            self.handler()
            return {"ok": True}

        self.application.include_router(router)
        self.client = self.enterContext(TestClient(self.application))

    def test_valid_token_allows_protected_handler(self):
        for method in ("POST", "DELETE"):
            with self.subTest(method=method):
                self.handler.reset_mock()
                response = self.client.request(method, "/internal/auth-probe", headers={
                    "x-internal-token": self.token,
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"ok": True})
                self.handler.assert_called_once_with()

    def test_missing_invalid_or_duplicate_token_never_runs_handler(self):
        cases = [
            [],
            [("X-Internal-Token", "")],
            [("X-Internal-Token", "wrong-token")],
            [("X-Internal-Token", self.token.upper())],
            [("X-Internal-Token", " " + self.token)],
            [("X-Internal-Token", self.token), ("X-Internal-Token", self.token)],
            [("X-Internal-Token", "wrong"), ("X-Internal-Token", self.token)],
            [("X-Internal-Token", self.token), ("X-Internal-Token", "wrong")],
            [(b"X-Internal-Token", b"\xff")],
        ]
        for method in ("POST", "DELETE"):
            for headers in cases:
                with self.subTest(method=method, headers=headers):
                    response = self.client.request(method, "/internal/auth-probe", headers=headers)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json(), {"detail": "Unauthorized"})
                    self.assertNotIn(self.token, response.text)
        self.handler.assert_not_called()

    def test_health_remains_public(self):
        for headers in ({}, {"X-Internal-Token": "wrong"}):
            response = self.client.get("/health", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok"})
        self.handler.assert_not_called()

    def test_probe_is_not_exposed_by_normal_application(self):
        self.assertNotIn("/internal/auth-probe", create_app().openapi()["paths"])


if __name__ == "__main__":
    unittest.main()
