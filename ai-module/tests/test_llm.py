"""core/llm.py 단위 테스트. 실제 모델 API는 호출하지 않는다(생성·검증만 확인)."""

import unittest

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from src.core.config import ConfigurationError, Settings
from src.core.llm import (
    LLM_CALL_PARAMS,
    MAX_OUTPUT_TOKENS,
    REQUEST_TIMEOUT_SECONDS,
    LLMConfigurationError,
    build_llm,
)


def make_settings(**overrides) -> Settings:
    """임베딩 계약을 만족하는 기본 Settings에 LLM 관련 값만 덮어쓴다."""
    values = {
        "ai_internal_token": "test-only-token",
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
    }
    values.update(overrides)
    return Settings(**values)


class BuildLlmTests(unittest.TestCase):
    def test_groq_provider_builds_chatgroq(self):
        settings = make_settings(
            llm_provider="groq", llm_model="some-model", groq_api_key="dummy"
        )
        llm = build_llm(settings)
        self.assertIsInstance(llm, ChatGroq)

    def test_openai_provider_builds_chatopenai(self):
        settings = make_settings(
            llm_provider="openai", llm_model="some-model", openai_api_key="dummy"
        )
        llm = build_llm(settings)
        self.assertIsInstance(llm, ChatOpenAI)

    def test_provider_is_case_insensitive_and_trimmed(self):
        settings = make_settings(
            llm_provider="  GROQ  ", llm_model="some-model", groq_api_key="dummy"
        )
        self.assertIsInstance(build_llm(settings), ChatGroq)

    def test_invalid_provider_is_rejected(self):
        settings = make_settings(llm_provider="bad", llm_model="some-model")
        with self.assertRaises(ConfigurationError) as result:
            build_llm(settings)
        self.assertIn("LLM_PROVIDER", str(result.exception))

    def test_empty_model_is_rejected(self):
        settings = make_settings(
            llm_provider="groq", llm_model="   ", groq_api_key="dummy"
        )
        with self.assertRaises(ConfigurationError) as result:
            build_llm(settings)
        self.assertIn("LLM_MODEL", str(result.exception))

    def test_missing_groq_key_is_rejected(self):
        settings = make_settings(llm_provider="groq", llm_model="some-model")
        with self.assertRaises(ConfigurationError) as result:
            build_llm(settings)
        self.assertIn("GROQ_API_KEY", str(result.exception))

    def test_missing_openai_key_is_rejected(self):
        settings = make_settings(llm_provider="openai", llm_model="some-model")
        with self.assertRaises(ConfigurationError) as result:
            build_llm(settings)
        self.assertIn("OPENAI_API_KEY", str(result.exception))

    def test_llm_configuration_error_is_a_configuration_error(self):
        # config.py의 ConfigurationError를 상속하므로 상위 타입으로도 잡힌다.
        self.assertTrue(issubclass(LLMConfigurationError, ConfigurationError))

    def test_errors_do_not_echo_key_values(self):
        # 키 값을 넣어도 에러 메시지에는 필드명만 남고 값은 노출되지 않아야 한다.
        settings = make_settings(
            llm_provider="openai", llm_model="some-model", openai_api_key="   "
        )
        with self.assertRaises(ConfigurationError) as result:
            build_llm(settings)
        self.assertNotIn("some-model", str(result.exception))

    def test_call_params_and_timeout_contract(self):
        # 호출 파라미터와 타임아웃이 의도한 기본값인지 고정한다.
        self.assertEqual(MAX_OUTPUT_TOKENS, 1024)
        self.assertEqual(LLM_CALL_PARAMS["max_tokens"], 1024)
        self.assertEqual(LLM_CALL_PARAMS["temperature"], 0)
        self.assertEqual(LLM_CALL_PARAMS["max_retries"], 0)
        self.assertTrue(LLM_CALL_PARAMS["streaming"])
        # Backend 60초보다 짧아야 AI가 먼저 타임아웃되어 error를 보낼 수 있다.
        self.assertLess(REQUEST_TIMEOUT_SECONDS, 60.0)


if __name__ == "__main__":
    unittest.main()
