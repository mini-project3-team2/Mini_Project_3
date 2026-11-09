"""설정에서 채팅 LLM을 선택·생성한다. 생성 시 네트워크 호출은 하지 않는다.

환경변수로 전환하는 것은 LLM뿐이다(개발 groq / 배포 openai). 임베딩 공급자·모델은
다른 곳에서 고정되며 여기서는 건드리지 않는다.

추론 모델(Groq gpt-oss, OpenAI GPT-5 mini/nano)은 temperature 같은 파라미터를
거부하거나, 추론 토큰을 출력 예산(max_tokens)에 포함시킬 수 있다. 그래서 호출
파라미터는 아래 LLM_CALL_PARAMS 한 곳에 모아 두었고, 실제 모델이 거부하면
이 딕셔너리만 고쳐서 해당 파라미터를 빼거나 조정한다(3단계 연결 확인에서 검증).
"""

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from src.core.config import ConfigurationError, Settings

# 지원 공급자. 임베딩은 의도적으로 제외한다.
GROQ = "groq"
OPENAI = "openai"
SUPPORTED_PROVIDERS = (GROQ, OPENAI)

# Groq 추론 모델(gpt-oss) 전용 설정. 추론에 출력 예산을 다 쓰고 답변 토큰 0개로
# 끝나는 문제(#63)를 막기 위해 추론 노력을 낮춘다. Groq 허용값은 low/medium/high이고
# none은 거부(400)된다. reasoning_effort는 추론 모델에서만 받으므로, Groq라도 비추론
# 모델(예: llama-3.3-70b-versatile)로 바꾸면 거부될 수 있어 gpt-oss 계열에만 넣는다.
GROQ_REASONING_PREFIX = "openai/gpt-oss"
GROQ_REASONING_EFFORT = "low"


def _uses_groq_reasoning(provider: str, model: str) -> bool:
    return provider == GROQ and model.startswith(GROQ_REASONING_PREFIX)

# 생성 답변 길이 상한. 문서에 구체값이 없어(아키텍처 6.3은 "max_tokens 제한"만 언급)
# 우리가 정한 기본값이다. 환경변수로 빼지 않고 코드 상수로 둔다.
# 주의: 추론 모델에서는 이 예산에 추론 토큰도 함께 포함된다.
MAX_OUTPUT_TOKENS = 1024

# 단일 모델 호출 타임아웃. Backend 스트리밍 타임아웃이 60초이므로, "안쪽일수록
# 짧게"(API 설계서 4.1) 원칙에 따라 그보다 짧게 둔다. AI가 먼저 끊겨야 error
# 이벤트를 Backend로 보낼 수 있고, Backend가 먼저 끊으면 그 기회를 잃는다.
# 스트림 전체의 하드 타임아웃은 질의 라우터(7단계)가 담당한다.
REQUEST_TIMEOUT_SECONDS = 40.0

# ---------------------------------------------------------------------------
# 모델 호출 파라미터를 한곳에서 조정하기 위한 딕셔너리. 실제 추론 모델이 아래 중
# 하나(예: temperature)를 거부하면 여기만 고쳐서 빼거나 바꾼다. 키는 ChatGroq와
# ChatOpenAI 생성자 모두가 받는 인자여야 한다.
# ---------------------------------------------------------------------------
LLM_CALL_PARAMS: dict[str, object] = {
    # 근거 기반 답변·환각 억제용. 일부 추론 모델은 이 값을 거부하므로,
    # 3단계 검증에서 temperature로 실패하면 이 줄을 제거한다.
    "temperature": 0,
    # 출력 상한(위의 추론 토큰 주의 참고).
    "max_tokens": MAX_OUTPUT_TOKENS,
    # SDK 레벨 재시도 없음: 시간 예산은 질의 경로가 직접 관리한다.
    "max_retries": 0,
    # .astream()으로 토큰을 점진적으로 스트리밍하기 위해 활성화.
    "streaming": True,
}


class LLMConfigurationError(ConfigurationError):
    """LLM 설정 오류. 필드명만 담고 입력 값은 절대 담지 않는다."""


def _require_llm_settings(settings: Settings) -> tuple[str, str, str]:
    """공급자·모델·키 존재 여부를 검증한다. 키의 유효성까지는 확인하지 않는다."""
    provider = settings.llm_provider.strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise LLMConfigurationError("LLM_PROVIDER must be one of groq, openai")

    model = settings.llm_model.strip()
    if not model:
        raise LLMConfigurationError("LLM_MODEL is required")

    if provider == GROQ:
        api_key = settings.groq_api_key.strip()
        if not api_key:
            raise LLMConfigurationError("GROQ_API_KEY is required for the groq LLM")
    else:
        api_key = settings.openai_api_key.strip()
        if not api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is required for the openai LLM")

    return provider, model, api_key


def build_llm(settings: Settings):
    """설정된 공급자에 맞는 채팅 모델을 생성한다.

    생성 자체는 네트워크 호출을 하지 않는다. 키·권한은 모델을 실제로 호출할 때만
    (3단계 연결 확인과 질의 경로에서) 검증된다.
    """
    provider, model, api_key = _require_llm_settings(settings)
    params = dict(LLM_CALL_PARAMS)

    if provider == GROQ:
        # gpt-oss 추론 모델일 때만 reasoning_effort를 넣는다(다른 Groq 모델엔 넣지 않음).
        if _uses_groq_reasoning(provider, model):
            params["reasoning_effort"] = GROQ_REASONING_EFFORT
        return ChatGroq(
            model=model,
            api_key=api_key,
            timeout=REQUEST_TIMEOUT_SECONDS,
            **params,
        )
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://api.openai.com/v1",
        timeout=REQUEST_TIMEOUT_SECONDS,
        **params,
    )
