import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from src.core.config import ConfigurationError, ROOT_ENV_FILE, load_settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env_file = Path(self.directory.name) / ".env"
        self.values = {
            "AI_INTERNAL_TOKEN": "test-only-token",
            "EMBEDDING_PROVIDER": "openai",
            "EMBEDDING_MODEL": "text-embedding-3-small",
        }

    def write_env(self, **extra):
        values = self.values | extra
        self.env_file.write_text(
            "\n".join(f"{key}={value}" for key, value in values.items()),
            encoding="utf-8-sig",
        )

    def test_file_load_does_not_mutate_environment(self):
        self.write_env(OPENAI_API_KEY="file-key", MARIADB_PASSWORD="unrelated-secret")
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(env_file=self.env_file)
            self.assertEqual(settings.openai_api_key, "file-key")
            self.assertEqual(dict(os.environ), {})
            self.assertFalse(hasattr(settings, "mariadb_password"))

    def test_process_environment_overrides_file(self):
        self.write_env(OPENAI_API_KEY="file-key")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "process-key"}, clear=True):
            settings = load_settings(env_file=self.env_file)
        self.assertEqual(settings.openai_api_key, "process-key")

    def test_empty_process_value_does_not_fall_back(self):
        self.write_env(OPENAI_API_KEY="file-key")
        settings = load_settings(env_file=self.env_file, environ={"OPENAI_API_KEY": ""})
        with self.assertRaisesRegex(ConfigurationError, "OPENAI_API_KEY"):
            settings.require_embedding_api_key()
        with self.assertRaisesRegex(ConfigurationError, "AI_INTERNAL_TOKEN"):
            load_settings(env_file=self.env_file, environ={"AI_INTERNAL_TOKEN": ""})

    def test_container_without_env_file(self):
        for env_file in (self.env_file, None):
            with self.subTest(env_file=env_file):
                settings = load_settings(env_file=env_file, environ=self.values)
                self.assertEqual(settings.embedding_model, "text-embedding-3-small")

    def test_root_path_and_working_directory_independence(self):
        self.assertEqual(ROOT_ENV_FILE, Path(__file__).resolve().parents[2] / ".env")
        self.write_env()
        original = Path.cwd()
        try:
            os.chdir(self.directory.name)
            settings = load_settings(env_file=self.env_file, environ={})
            self.assertEqual(settings.ai_internal_token, "test-only-token")
            self.assertEqual(ROOT_ENV_FILE, Path(__file__).resolve().parents[2] / ".env")
        finally:
            os.chdir(original)

    def test_missing_or_invalid_token_is_rejected(self):
        for token in ("", "   ", "token with space", "토큰", "token\x00"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(ConfigurationError, "AI_INTERNAL_TOKEN"):
                    load_settings(env_file=None, environ=self.values | {"AI_INTERNAL_TOKEN": token})
        with self.assertRaisesRegex(ConfigurationError, "AI_INTERNAL_TOKEN"):
            load_settings(env_file=None, environ={})

    def test_embedding_contract_is_enforced_without_echoing_input(self):
        for field in ("EMBEDDING_PROVIDER", "EMBEDDING_MODEL"):
            with self.subTest(field=field):
                with self.assertRaises(ConfigurationError) as result:
                    load_settings(env_file=None, environ=self.values | {field: "private-invalid-value"})
                self.assertIn(field, str(result.exception))
                self.assertNotIn("private-invalid-value", str(result.exception))

    def test_optional_keys_and_llm_are_not_required_at_load_time(self):
        settings = load_settings(env_file=None, environ=self.values)
        self.assertEqual(settings.llm_model, "")
        self.assertEqual(settings.groq_api_key, "")
        with self.assertRaisesRegex(ConfigurationError, "OPENAI_API_KEY"):
            settings.require_embedding_api_key()

    def test_repr_hides_secrets_and_settings_are_immutable(self):
        settings = load_settings(env_file=None, environ=self.values | {
            "OPENAI_API_KEY": "openai-test-secret", "GROQ_API_KEY": "groq-test-secret",
        })
        for secret in (settings.ai_internal_token, settings.openai_api_key, settings.groq_api_key):
            self.assertNotIn(secret, repr(settings))
        self.assertEqual(settings.require_embedding_api_key(), "openai-test-secret")
        with self.assertRaises(FrozenInstanceError):
            settings.llm_model = "changed"

    def test_credentials_are_not_interpolated(self):
        self.write_env(OPENAI_API_KEY="literal-${UNRELATED}-key")
        settings = load_settings(env_file=self.env_file, environ={"UNRELATED": "expanded"})
        self.assertEqual(settings.openai_api_key, "literal-${UNRELATED}-key")


if __name__ == "__main__":
    unittest.main()
