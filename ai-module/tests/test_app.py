import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.core.config import ConfigurationError, load_settings


class AppTests(unittest.TestCase):
    def setUp(self):
        self.values = {
            "AI_INTERNAL_TOKEN": "test-only-token",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_MODEL": "text-embedding-3-small",
        }

    def test_health_is_public_and_works_without_api_keys(self):
        settings = load_settings(env_file=None, environ=self.values)
        application = create_app(lambda: settings)
        with patch("src.core.resources.open_embeddings") as embedding_factory, \
             patch("src.core.resources.open_collection") as collection_factory, \
             TestClient(application) as client:
            for headers in ({}, {"X-Internal-Token": "irrelevant"}):
                response = client.get("/health", headers=headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ok"})
                self.assertEqual(response.headers["content-type"], "application/json")
                self.assertNotIn(settings.ai_internal_token, response.text)
            embedding_factory.assert_not_called()
            collection_factory.assert_not_called()

    def test_settings_loaded_at_startup_once_and_released_on_shutdown(self):
        settings = load_settings(env_file=None, environ=self.values)
        loader = Mock(return_value=settings)
        application = create_app(loader)
        loader.assert_not_called()
        with TestClient(application) as client:
            self.assertIs(application.state.settings, settings)
            client.get("/health")
            client.get("/health")
            loader.assert_called_once_with()
        self.assertFalse(hasattr(application.state, "settings"))
        self.assertFalse(hasattr(application.state, "resources"))

    def test_api_docs_endpoints_are_disabled(self):
        # 내부 API 문서(/docs·/redoc·/openapi.json)는 비공개여야 한다(#90).
        settings = load_settings(env_file=None, environ=self.values)
        application = create_app(lambda: settings)
        with patch("src.core.resources.open_embeddings"), \
             patch("src.core.resources.open_collection"), \
             TestClient(application) as client:
            for path in ("/docs", "/redoc", "/openapi.json"):
                self.assertEqual(client.get(path).status_code, 404, path)
            # /health는 그대로 동작해야 한다.
            self.assertEqual(client.get("/health").status_code, 200)

    def test_invalid_configuration_prevents_startup(self):
        for overrides in ({"AI_INTERNAL_TOKEN": ""}, {"EMBEDDING_MODEL": "unsupported"}):
            with self.subTest(overrides=overrides):
                values = self.values | overrides
                application = create_app(lambda: load_settings(env_file=None, environ=values))
                with self.assertRaises(ConfigurationError):
                    with TestClient(application):
                        self.fail("Invalid settings must prevent application startup")


if __name__ == "__main__":
    unittest.main()
