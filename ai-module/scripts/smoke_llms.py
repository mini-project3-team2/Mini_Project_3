"""Two authorized streaming smoke tests using synthetic source material."""
import argparse
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai-module'))
from openai import AsyncOpenAI
from src.core.config import load_settings

PROMPT = (
    '다음 합성 자료만 근거로 질문에 한국어 한 문장으로 답하고 출처를 [p.3]으로 표시하세요. '
    '자료: [p.3] 테스트 도서관의 평일 운영시간은 오전 9시부터 오후 6시까지이다. '
    '질문: 테스트 도서관은 평일 몇 시에 문을 닫나요?'
)


async def check(provider, model, endpoint, key, effort, settings):
    result = dict(provider=provider, model=model, reasoning_effort=effort,
                  max_completion_tokens=512, request_attempts=0, retries=0,
                  success=False, answer_chunks=0)
    if not key.strip():
        result['error_type'] = 'MissingAPIKey'
        return result
    start = time.perf_counter()
    answer = []
    try:
        async with asyncio.timeout(55):
            async with AsyncOpenAI(api_key=key, base_url=endpoint, max_retries=0, timeout=30) as client:
                result['request_attempts'] = 1
                options = dict(model=model, messages=[{'role': 'user', 'content': PROMPT}],
                               reasoning_effort=effort, max_completion_tokens=512,
                               stream=True, stream_options={'include_usage': True})
                if provider == 'groq':
                    options['extra_body'] = {'include_reasoning': False}
                stream = await client.chat.completions.create(**options)
                async with stream:
                    async for chunk in stream:
                        result['returned_model'] = chunk.model
                        usage = chunk.usage
                        if usage is None:
                            extra_usage = getattr(chunk, 'x_groq', None)
                            if isinstance(extra_usage, dict):
                                usage = extra_usage.get('usage')
                        if usage:
                            data = usage if isinstance(usage, dict) else usage.model_dump()
                            result['usage'] = {name: data.get(name) for name in
                                               ('prompt_tokens', 'completion_tokens', 'total_tokens')}
                            detail = data.get('completion_tokens_details') or {}
                            if 'reasoning_tokens' in detail:
                                result['usage']['reasoning_tokens'] = detail['reasoning_tokens']
                        for choice in chunk.choices:
                            if choice.finish_reason:
                                result['finish_reason'] = choice.finish_reason
                            content = choice.delta.content
                            if content:
                                if not answer:
                                    result['first_answer_seconds'] = round(time.perf_counter() - start, 3)
                                answer.append(content)
                                result['answer_chunks'] += 1
                text = ''.join(answer)
                # Defensive redaction; credentials are never supplied in prompts.
                for secret in (settings.openai_api_key, settings.groq_api_key, settings.ai_internal_token):
                    if secret:
                        text = text.replace(secret, '[REDACTED]')
                result['answer'] = text
                normalized = ''.join(text.split())
                result['expected_time_present'] = '오후6시' in normalized or '18시' in normalized
                result['expected_citation_present'] = '[p.3]' in text
                result['success'] = bool(text.strip()) and result.get('finish_reason') == 'stop'
    except Exception as error:
        result['error_type'] = type(error).__name__
        status = getattr(error, 'status_code', None)
        if isinstance(status, int):
            result['http_status'] = status
        code = getattr(error, 'code', None)
        if code in ('model_not_found', 'insufficient_quota', 'rate_limit_exceeded', 'invalid_api_key', 'unsupported_parameter', 'unsupported_value'):
            result['error_code'] = code
    result['total_seconds'] = round(time.perf_counter() - start, 3)
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return result


async def main(destination: Path):
    settings = load_settings()
    rows = []
    for args in [
        ('groq', 'openai/gpt-oss-120b', 'https://api.groq.com/openai/v1', settings.groq_api_key, 'low'),
        ('openai', 'gpt-6-luna', 'https://api.openai.com/v1', settings.openai_api_key, 'none'),
    ]:
        rows.append(await check(*args, settings))
        report = dict(time_kst=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
                      test_type='single synthetic grounded-answer streaming smoke test per provider', results=rows)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    return 0 if all(row['success'] and row.get('expected_time_present') and row.get('expected_citation_present') for row in rows) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live llms smoke test: sends synthetic text and may incur API charges.")
    parser.add_argument("--run-live", action="store_true", help="Run the real API request(s); no retries.")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "ai-module/data/smoke-results/llms.json",
                        help="Local JSON output; default path is Git-ignored.")
    args = parser.parse_args()
    if not args.run_live:
        parser.print_help()
        sys.exit(0)
    logging.disable(logging.CRITICAL)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        exit_code = asyncio.run(main(args.output))
    except Exception as error:
        # Configuration and file errors must not print credentials or full traces.
        print(json.dumps({"success": False, "error_type": type(error).__name__}))
        exit_code = 1
    sys.exit(exit_code)
