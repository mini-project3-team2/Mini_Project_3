"""질의 파트 연결 확인(3단계): Groq LLM · OpenAI LLM · OpenAI 임베딩을 각 1회만 호출.

기존 core/llm.py의 build_llm과 core/embeddings.py의 임베딩 클라이언트를 그대로 쓴다.
새 클라이언트를 만들지 않는다. 호출은 각 1회뿐이며 반복하지 않는다(비용·한도 절약).

안전 규칙(기존 smoke 스크립트와 동일):
- --run-live 없으면 아무 호출도 하지 않는다.
- 키 값, 예외 메시지 원문, 전체 트레이스를 절대 출력하지 않는다.
- 결과 JSON은 .gitignore된 ai-module/data/ 아래에만 저장한다.

LLM_CALL_PARAMS(temperature·max_tokens 등) 때문에 실패하면, 어떤 파라미터가
문제인지 알 수 있도록 공급자 오류의 code·param만 추출해 보여 준다(값은 노출 안 함).
"""
import argparse
import asyncio
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-module"))

from langchain_core.messages import HumanMessage

from src.core.config import load_settings
from src.core.embeddings import open_embeddings
from src.core.llm import LLM_CALL_PARAMS, build_llm

# 합성 프롬프트(수업 자료 아님). 짧은 한 문장 답을 유도한다.
PROMPT = "한국어로 '연결 확인 완료'라고만 짧게 답하세요."
EMBED_INPUT = "질의 파트 임베딩 연결 확인용 합성 문장입니다."
# 응답 앞부분만 짧게 남긴다.
PREVIEW_CHARS = 40
# 스크립트 전체 상한(개별 호출 타임아웃은 build_llm이 가진 40초).
OVERALL_TIMEOUT = 55


def _redact(text: str, settings) -> str:
    """혹시라도 섞인 비밀 값을 방어적으로 가린다(프롬프트에 키를 넣지는 않는다)."""
    for secret in (settings.openai_api_key, settings.groq_api_key, settings.ai_internal_token):
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def _error_fields(error) -> dict:
    """키·원문 없이, 어떤 파라미터가 문제인지 알 수 있는 필드만 추출한다."""
    fields = {"error_type": type(error).__name__}
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        fields["http_status"] = status
    # OpenAI/Groq SDK 오류는 code·param을 노출한다(예: unsupported_value, 'temperature').
    for name in ("code", "param"):
        value = getattr(error, name, None)
        if isinstance(value, str) and value:
            fields[name] = value
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        for name in ("code", "param"):
            value = body.get(name)
            if isinstance(value, str) and value and name not in fields:
                fields[name] = value
    return fields


async def check_llm(label: str, settings, *, provider: str, model: str) -> dict:
    """build_llm으로 만든 모델을 astream으로 1회 호출. 첫 토큰·총 소요 시간 측정."""
    result = {
        "check": label,
        "provider": provider,
        "model": model,
        "call_params": dict(LLM_CALL_PARAMS),
        "success": False,
        "chunks": 0,
    }
    # build_llm은 settings를 읽으므로, 이 호출용으로 공급자/모델만 바꿔 넘긴다.
    import dataclasses

    call_settings = dataclasses.replace(settings, llm_provider=provider, llm_model=model)
    start = time.perf_counter()
    pieces = []
    try:
        llm = build_llm(call_settings)
    except Exception as error:  # 설정/키 누락 등 생성 단계 오류
        result.update(_error_fields(error))
        result["stage"] = "build"
        result["total_seconds"] = round(time.perf_counter() - start, 3)
        return result

    try:
        async with asyncio.timeout(OVERALL_TIMEOUT):
            async for chunk in llm.astream([HumanMessage(content=PROMPT)]):
                text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                if text:
                    if not pieces:
                        result["first_token_seconds"] = round(time.perf_counter() - start, 3)
                    pieces.append(text)
                    result["chunks"] += 1
    except Exception as error:  # 호출 단계 오류(파라미터 거부 포함)
        result.update(_error_fields(error))
        result["stage"] = "call"
        result["total_seconds"] = round(time.perf_counter() - start, 3)
        return result

    answer = _redact("".join(pieces), settings).strip()
    result["answer_preview"] = answer[:PREVIEW_CHARS]
    result["success"] = bool(answer)
    result["total_seconds"] = round(time.perf_counter() - start, 3)
    return result


async def check_embedding(settings) -> dict:
    """기존 임베딩 클라이언트로 1문장 임베딩 1회. 차원·소요 시간 확인."""
    result = {
        "check": "openai_embedding",
        "provider": settings.embedding_provider,
        "model": settings.embedding_model,
        "success": False,
    }
    start = time.perf_counter()
    try:
        async with asyncio.timeout(OVERALL_TIMEOUT):
            async with open_embeddings(settings) as embeddings:
                vectors = await embeddings.aembed_documents([EMBED_INPUT])
        result["first_token_seconds"] = round(time.perf_counter() - start, 3)
        result["vector_count"] = len(vectors)
        result["dimensions"] = [len(v) for v in vectors]
        result["success"] = len(vectors) == 1 and result["dimensions"] == [1536]
    except Exception as error:
        result.update(_error_fields(error))
    result["total_seconds"] = round(time.perf_counter() - start, 3)
    return result


async def main(destination: Path, openai_model: str) -> int:
    settings = load_settings()
    results = []

    # 1) Groq LLM — .env의 LLM_PROVIDER/LLM_MODEL 그대로 사용
    results.append(await check_llm(
        "groq_llm", settings,
        provider="groq", model=settings.llm_model,
    ))

    # 2) OpenAI LLM — 모델명은 인자/환경변수로만 받는다(코드 고정 금지)
    if openai_model.strip():
        results.append(await check_llm(
            "openai_llm", settings,
            provider="openai", model=openai_model.strip(),
        ))
    else:
        results.append({
            "check": "openai_llm", "provider": "openai", "success": False,
            "skipped": "OpenAI 모델명이 없습니다(--openai-model 또는 OPENAI_LLM_MODEL 지정).",
        })

    # 3) OpenAI 임베딩 — 기존 클라이언트 그대로
    results.append(await check_embedding(settings))

    report = {
        "time_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "test_type": "query-part connection smoke: one call each (groq llm, openai llm, openai embedding)",
        "results": results,
    }
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(r.get("success") for r in results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="질의 파트 연결 확인(실호출·과금 가능, 각 1회). --run-live 없으면 아무것도 호출하지 않음."
    )
    parser.add_argument("--run-live", action="store_true", help="실제 API 1회씩 호출(재시도 없음).")
    parser.add_argument(
        "--openai-model", default=os.environ.get("OPENAI_LLM_MODEL", ""),
        help="OpenAI LLM 확인에 쓸 모델명(미지정 시 환경변수 OPENAI_LLM_MODEL). 코드에 고정하지 않음.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "ai-module/data/smoke-results/query-llm.json",
        help="로컬 JSON 출력 경로. 기본 경로는 .gitignore 대상.",
    )
    args = parser.parse_args()
    if not args.run_live:
        parser.print_help()
        sys.exit(0)
    logging.disable(logging.CRITICAL)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        exit_code = asyncio.run(main(args.output, args.openai_model))
    except Exception as error:
        # 설정·파일 오류도 키나 전체 트레이스를 출력하지 않는다.
        print(json.dumps({"success": False, "error_type": type(error).__name__}))
        exit_code = 1
    sys.exit(exit_code)
