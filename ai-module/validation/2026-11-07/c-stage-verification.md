# C단계 최종 검증 기록

검증일: 2026-11-07 KST
대상: `feature/ai-ingestion`, 서비스 코드 커밋 `6794e04`(C4).
C5 변경은 재현용 오프라인 HTTP 스크립트와 문서 정리이며 서비스 동작을 수정하지 않았다.

**판정: C1~C5의 AI 직접 적재 구현·오프라인 검증 완료.** 실제 모델 적재, Backend E2E, DELETE API, 운영 검증 완료를 뜻하지 않는다.

## 환경과 실행 결과

Windows 로컬, Python 3.12.13, FastAPI 0.162.0, Chroma 1.5.9, pypdf 7.0.0, langchain-openai 1.7.4, Uvicorn 0.54.0. 테스트는 합성 설정을 주입하며 실제 `.env`를 읽거나 API 키를 사용하지 않았다.

`ai-module`에서 실행:

```bash
uv sync --locked --offline
uv pip check
uv run --locked --offline python -m unittest discover -s tests -v
uv run --locked --offline python scripts/smoke_ingestion_offline.py
```

| 검사 | 결과 |
|---|---|
| 잠금 파일 기반 의존성 확인 | 통과, 설치 패키지 109개 확인 |
| 설치 패키지 호환성 | `All installed packages are compatible` |
| 전체 unittest | 63개 통과, 이번 실행 테스트 본문 4.017초 |
| 실제 Uvicorn loopback HTTP | 아래 항목 모두 통과 |
| Mock 재생성 | 별도 임시 폴더에서 생성한 58개 파일이 저장소 파일과 바이트 단위 일치 |
| 변경 공백 검사 | `git diff --check` 통과 |

손상 PDF 테스트의 `EOF marker not found`는 의도한 손상 입력에 대한 파서 경고다. 테스트 실패가 아니다. asyncio 디버그의 느린 task 메시지 역시 종료 결과는 성공이었다.

## 실제 로컬 HTTP 확인

`scripts/smoke_ingestion_offline.py`는 실제 앱을 합성 설정으로 생성하고 모의 임베딩만 주입한다. `127.0.0.1`의 OS 할당 포트에서 Uvicorn을 실행해 HTTP 요청을 보낸다. 원본 PDF는 테스트 코드가 생성하며 Chroma는 임시 경로만 사용한다.

| 요청/확인 | 관측값 |
|---|---|
| 인증 없는 GET /health | 200, `{"status":"ok"}` |
| 토큰 없는 POST /internal/documents | 401 |
| 정상 합성 PDF 적재 | 200, `{"documentId":12,"chunkCount":2}` |
| 동일 소유자·문서 재적재 | 409, `DOCUMENT_ALREADY_EXISTS` |
| documentId=0 | 400, `INVALID_INPUT` |
| 모의 임베딩 호출 | 2개 청크 배치 1회(중복/입력 오류에서는 추가 호출 없음) |
| 서버 종료 후 저장소 재개방 | 청크 2개, PDF 페이지 `[1,3]` 보존 |
| 종료 정리 | 서버 종료, 임시 저장소 제거 |

이는 실제 TCP HTTP·PDF 파싱·Chroma 저장 확인이며 OpenAI 모델 호출은 아니다. 서버를 다시 기동한 것은 아니고 서버 종료 후 Chroma 클라이언트를 새로 열어 확인했다. 출력 JSON의 `pages_after_storage_reopen` 필드가 이 결과다.

## 완료 근거 연결

| 완료 항목 | 근거 |
|---|---|
| 인증·필수/중복 필드·범위·크기·오류 응답 | `tests/test_documents.py` |
| 실제 PDF 추출·빈 페이지 보존·800/100 분할·임시 파일 정리 | `tests/test_pdf.py` |
| 배치·벡터 개수/차원/수치 검증·모의 공급자 실패·시간 예산 | `tests/test_embedding.py` |
| 실제 임시 Chroma 저장·ID/개수 확인·재개방·중복 차단 | `tests/test_ingest.py` |
| 부분 저장 실패 정리·다른 소유자/문서 유지·정리 실패 보고 | `tests/test_ingest.py` |
| 동일 문서 동시 적재·반복 취소·지연된 저장 이후 정리 | `tests/test_ingest.py`, `tests/test_documents.py` |
| 기존 설정·health·인증·클라이언트 재사용 회귀 | `test_app.py`, `test_config.py`, `test_security.py`, `test_resources.py` |

## 인계와 남은 범위

- 재사용: `app.state.resources`의 공통 클라이언트, `ingestion` coordinator. 컬렉션은 `study_materials_text-embedding-3-small`, 임베딩은 1536차원, 메타데이터는 `owner_uuid`, `document_id`, `document_name`, `page`다.
- C1~C4 사용법과 오류 계약은 `SETUP.md`, `INGESTION_CONTRACT.md`, API 설계서 6.1, `mock-data/internal/ingest.*.json`을 참고한다.
- **D단계**: DELETE API, 삭제 멱등성, 적재와 삭제 경합, Backend 120초 이후 삭제, 실패 잔재 복구. Backend가 409에도 삭제를 호출하는 기존 흐름은 별도 보완 대상이다.
- **E단계**: 승인된 실제 교안의 모델 API 적재, 토큰/사용량과 전체 시간 측정, 가장 큰 교안의 120초 기준 확인.
- **통합/운영**: Backend·Frontend E2E, 검색 READY 필터, Docker/Linux/EC2, 다중 worker는 미검증이다.
- 처리 100초·정리 10초는 강제 종료 보장이 아니다. 동기 파서/Chroma 호출 종료와 정리를 기다리며, 압축 해제 메모리·CPU·페이지 수의 하드 상한 및 서버 강제 종료 후 자동 복구도 보장하지 않는다.
- 앞선 규약 점검의 이슈 번호·pre-commit·설정 상수 정리는 사용자 판단으로 이번 단계에서 보류했다. 비밀정보 검사 도구 통과나 원격 CI 통과를 주장하지 않는다.

이 검증에서는 서비스 배포·외부 업로드·실제 모델 API 호출·Git push를 수행하지 않았다.
