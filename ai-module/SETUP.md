# AI 모듈 개발 환경 준비

Python 프로젝트·공통 설정 로더·FastAPI 앱·`/health`·내부 인증 의존성·공통 클라이언트 관리가 구현돼 있습니다. 적재·삭제 API는 아직 구현하지 않았습니다.

## 1. 실행 환경

- Python **3.12**, uv **0.12.23**을 사용합니다.
- 저장소 루트에서 `uv --version`, `uv python list --only-installed`로 확인합니다.
- 기본 `python`이 3.13이어도 전역 설정을 바꿀 필요는 없습니다. 프로젝트 생성·가상환경 구성 시 `uv`에서 Python 3.12를 명시합니다.
- Ollama 설치는 필요 없습니다.

## 2. 환경변수 파일 복사

Backend와 AI Module은 **저장소 루트의 `.env` 하나**를 사용합니다. `ai-module/.env`를 별도로 만들지 않습니다.

PowerShell, 저장소 루트에서:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Git Bash:

```bash
test -f .env || cp .env.example .env
```

기존 파일이 있으면 유지하고 `.env.example`의 새 항목만 추가합니다.

| 항목 | 입력 방법 | 필요한 단계 |
|---|---|---|
| `OPENAI_API_KEY` | 강사에게 제공받은 실제 키를 로컬 `.env`에만 입력 | 실제 문서·질문 임베딩 |
| `AI_INTERNAL_TOKEN` | 아래 명령으로 각자 생성, Backend와 AI에 같은 값 사용 | 내부 API 인증 |
| `EMBEDDING_PROVIDER` | `openai` 유지 | 적재·검색 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` 유지, 기본 1536차원 | 적재·검색 |
| `AI_SERVICE_URL` | 호스트 실행은 `http://localhost:8000`, Compose는 `http://ai-service:8000` | Backend → AI 연결 |
| `LLM_PROVIDER` | 개발 `groq`, 배포 `openai` | 답변 생성 |
| `LLM_MODEL` | 질의 담당자가 공지한 모델명 | 답변 생성 |
| `GROQ_API_KEY` | 제공받은 키, 실제 Groq 답변 생성 시 입력 | 개발 답변 생성 |
| `LANGSMITH_TRACING` | `false` 유지 | 기본 설정 |

API 키와 비밀번호는 공용 예시 문자열로 채우지 않습니다. 빈 항목에 실제 값을 입력해야 합니다. 모델 선택은 유료 호출 실행과 별개이며, 실제 교안 임베딩은 추출 텍스트를 OpenAI API로 전송합니다.

내부 토큰 생성 예시(로컬 터미널에서 실행 후 `.env`에 직접 입력):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

이 명령은 표준 라이브러리만 사용합니다. JWT에는 별도로 생성한 값을 사용합니다. 생성값을 채팅·PR·스크린샷에 붙이지 않습니다.

Backend·DB 설정은 기존 루트 `.env.example`의 해당 구역과 README 3.3절을 따릅니다.

## 3. 자료와 검증

- 실제 교안은 Git에서 제외된 `ai-module/data/` 등에 보관합니다. 경로·파일 크기·페이지 수는 개인 검증 기록으로 관리합니다.
- 테스트와 개발 Chroma 저장소는 분리합니다. 개발 데이터는 회원·문서 ID가 다른 배포 환경으로 복사하지 않습니다.
- 단위 테스트는 모의 임베딩으로 진행하고, 실제 API의 접근 권한·비용·검색 품질 검증과 구분합니다.
- `/health`는 앱의 기동 상태만 나타냅니다. 외부 모델 API의 키·권한이나 Chroma 연결 상태를 확인하지 않습니다.

## 4. 의존성 설치

저장소 루트에서 다음 명령을 실행합니다.

```bash
cd ai-module
uv sync --locked
uv run --locked python --version
```

Python은 3.12 계열로 제한하며, 정확한 패키지 버전은 `uv.lock`에 고정합니다. `.venv`는 Git에서 제외됩니다. 의존성 설치는 모델 API를 호출하지 않습니다.

포함된 의존성은 FastAPI·uvicorn, 환경변수 로딩, multipart 업로드, PDF 로더·분할기, OpenAI 임베딩 연동, Chroma입니다. 질의·답변 생성용 패키지는 질의 파트 구현 시 추가합니다.

## 5. 공통 설정 로더

`src/core/config.py`의 `load_settings()`를 앱 시작 시 한 번 호출하고 반환된 읽기 전용 `Settings`를 공통 의존성으로 전달합니다. 모듈 import만으로 설정을 읽거나 API를 호출하지 않습니다.

- 파일 위치 기준으로 저장소 루트 `.env`를 읽습니다. 터미널의 작업 디렉터리는 영향을 주지 않습니다.
- 프로세스 환경변수가 파일 값보다 우선합니다. 빈 문자열도 우선하며 파일 값으로 대체하지 않습니다.
- `.env`가 없는 컨테이너에서도 주입된 환경변수만으로 동작합니다. `env_file=None`이면 파일 로딩을 명시적으로 끕니다.
- `.env` 내용을 `os.environ`에 복사하지 않으며, 설정 객체에는 필요한 AI 항목만 담습니다. `${...}` 치환은 하지 않습니다.
- 내부 토큰은 필수이며 공백·제어문자·비ASCII 문자를 거부합니다. 임베딩 설정은 `openai` / `text-embedding-3-small`만 허용합니다.
- API 키와 LLM 설정은 로딩 시 필수가 아닙니다. 임베딩 클라이언트 구현에서는 `settings.require_embedding_api_key()`를 호출해 키 존재를 확인해야 합니다. 키 유효성·권한은 확인하지 않습니다. LLM 공급자·모델·키 검증은 질의 파트에서 연결합니다.
- 토큰·API 키는 `repr(settings)`에서 숨깁니다. 개별 속성이나 설정 전체를 사전으로 변환해 로그에 출력하면 안 됩니다.

임시 설정만 사용하는 테스트 (`ai-module`에서 실행):

```bash
uv run --locked python -m unittest discover -s tests -v
```

## 6. FastAPI 실행과 헬스체크

`ai-module`에서 실행합니다.

```bash
uv run --locked uvicorn src.api.main:app --reload --port 8000
```

`GET http://localhost:8000/health`는 인증 헤더 없이 `200`과 `{"status":"ok"}`를 반환합니다. 모델·저장소 클라이언트를 생성하거나 호출하지 않습니다.

앱은 lifespan 시작 시 `load_settings()`를 한 번 호출하고 `app.state.settings`에 보관합니다. 필수 설정이 잘못되면 기동에 실패합니다. 설정을 바꾼 뒤에는 앱을 재시작해야 합니다. API 키가 없어도 내부 토큰과 임베딩 설정이 올바르면 헬스체크가 동작합니다.

## 7. 내부 인증 의존성

`src/core/security.py`의 `require_internal_token`을 내부 API 라우터에 적용합니다. 앱 전체에 적용하지 않아 `/health`는 공개로 유지합니다.

```python
from fastapi import APIRouter, Depends
from src.core.security import require_internal_token

router = APIRouter(dependencies=[Depends(require_internal_token)])
```

앱 시작 시 검증한 `app.state.settings.ai_internal_token`과 헤더를 `secrets.compare_digest`로 비교합니다. `X-Internal-Token`이 없거나 비어 있거나 불일치하면 `401`과 `{"detail":"Unauthorized"}`를 반환합니다. 중복 헤더와 비ASCII 값도 동일하게 거부하며, 입력 토큰을 로그나 응답에 담지 않습니다.

테스트용 라우터에서 POST·DELETE 인증과 거부 시 핸들러 미실행을 확인합니다. 테스트 라우터는 서비스에 등록되지 않습니다. 실제 적재·삭제·질의 라우터를 구현할 때 위 의존성을 연결해야 합니다.

## 8. 공통 임베딩과 Chroma 클라이언트

- `app.state.resources`는 앱 수명주기마다 하나 생성됩니다. `src/core/resources.py`의 `get_embeddings`와 `get_collection`을 FastAPI `Depends`로 주입하거나, 앱의 리소스 관리자에서 `await resources.embeddings()` / `await resources.collection()`으로 가져옵니다.
- 첫 사용 시 생성하고 재사용합니다. 동시 초기화는 잠금으로 한 번만 수행하며, 앱 종료 시 생성된 클라이언트를 정리합니다. `/health`만 호출하면 API 키 검증·Chroma 파일 생성은 일어나지 않습니다.
- `src/core/embeddings.py`는 설정의 모델과 키를 명시적으로 사용합니다. 기본 1536차원을 유지하고, 요청 타임아웃 30초·SDK 재시도 0회·배치 크기 64로 구성합니다. 이 타임아웃은 전체 적재 시간 제한이 아니며, 전체 예산과 재시도는 적재 단계에서 제어해야 합니다.
- 텍스트를 그대로 전달하도록 자동 토큰 분할을 끕니다. 호출 전 입력 길이 제한과 반환 벡터의 개수·차원 검증은 이후 적재·질의 구현에서 수행해야 합니다. 실제 API 키 유효성·임베딩 결과는 아직 검증하지 않았습니다.
- Chroma 컬렉션 이름은 `settings.collection_name` (`study_materials_text-embedding-3-small`)입니다. 기본 저장 경로는 `ai-module/chroma_db`입니다. 선택 변수 `CHROMA_PERSIST_DIRECTORY`로 변경할 수 있으며, 상대 경로는 `ai-module` 기준입니다. Compose에서 변경할 때는 AI 서비스의 `environment`와 볼륨 마운트 경로를 함께 맞춥니다.
- Chroma에는 `embeddings` / `query_embeddings`를 명시적으로 전달해야 합니다. 설치된 버전은 `embedding_function=None`만으로 기본 모델 사용이 차단되지 않아, `ExplicitVectorsOnly` 함수를 등록해 자동 임베딩을 거부합니다. Chroma 클라이언트는 이 모듈을 통해 생성해야 합니다. 익명 사용 통계는 비활성화합니다.
- 임시 Chroma 저장소에 합성 벡터를 넣고 재개방한 검증은 실제 OpenAI 임베딩·검색 품질 검증과 구분합니다. 실데이터 저장소를 테스트에 사용하지 않습니다.

## 9. PDF 검증·추출·분할 (C2)

`src/services/pdf.py`의 동기 함수 `prepare_pdf(source, filename, owner_uuid=..., document_id=..., document_name=...)`는 바이너리 스트림을 받아 LangChain `Document` 청크 목록을 반환합니다. 식별자와 표시 이름은 호출자가 C1 계약대로 검증한 값을 넘깁니다. 현재 HTTP 라우터에는 연결하지 않았습니다.

- 파일 확장자(대소문자 무시), 실제 `%PDF-` 헤더, 빈 파일, 10MiB 제한을 검사합니다. MIME과 선언된 크기는 신뢰하지 않습니다.
- 서버 생성 임시 경로에 나눠 복사하고, 성공·예외 시 모두 임시 파일을 정리합니다. 입력 스트림의 소유권은 호출자에게 있습니다.
- `PyPDFLoader`로 페이지별 추출 후 800자·최대 100자 오버랩으로 분할합니다. 분할 경계에 따라 실제 오버랩은 작을 수 있습니다. 빈 페이지는 건너뛰되 PDF 페이지 번호는 1부터 원래 위치를 유지합니다.
- 메타데이터는 `owner_uuid`, `document_id`, `document_name`, `page`만 남기며 PDF 작성자와 로컬 파일 경로는 제외합니다.
- `PdfProcessingError`는 고정 `code`와 `status_code`를 제공합니다. 알려진 PDF 파싱 오류·텍스트 없음은 422, 입력 파일 오류는 400/413입니다. 디스크·스트림 오류나 예상하지 못한 버그를 422로 감추지 않습니다. HTTP 매핑은 C4에서 연결합니다.
- 동기 함수는 작업 스레드에서 실행해야 합니다. 요청 취소만으로 스레드가 끝나지 않으므로 호출자는 작업이 끝날 때까지 입력 스트림을 유지해야 합니다. `prepare_pdf` 내부에서 임시 파일 생성·추출·정리를 함께 수행합니다. 비동기 취소 연동은 아직 검증하지 않았습니다.
- 파일 바이트 제한은 압축 해제 후 메모리·페이지 수·CPU 시간의 상한이 아닙니다. 파서 프로세스 격리 및 하드 시간 제한은 구현하지 않았습니다. 이미지 OCR은 지원하지 않습니다.

검증: `uv run --locked python -m unittest discover -s tests -p test_pdf.py -v`. 합성 PDF로 페이지·청크·오버랩, 파일 크기 경계, 손상·암호화·전체 빈 텍스트, 임시 파일 정리와 내부 오류 구분을 확인합니다. API 키와 외부 호출을 사용하지 않습니다.

## 10. 임베딩·벡터 검증 (C3, 저장 전까지만)

`src/services/embedding.py`의 `await embed_chunks(chunks, client, budget_seconds=...)`에 C2 결과와 기존 `AppResources.embeddings()`의 클라이언트를 전달합니다. 반환값은 텍스트·4종 메타데이터·검증된 벡터를 가진 `EmbeddedChunk` 목록이며 메모리에만 존재합니다. 이 함수는 Chroma를 가져오거나 생성·저장하지 않습니다. HTTP API에도 아직 연결하지 않았습니다.

- 전체 청크의 공백·800자 제한·UTF-8 인코딩 가능 여부·메타데이터 형태를 첫 호출 전에 검증합니다. UUID와 파일명 등 요청 필드의 상세 계약 검증은 호출자 책임입니다.
- 최대 64개씩 순서대로 비동기 임베딩을 요청합니다. 새 클라이언트를 만들지 않으며 재시도하지 않습니다.
- 실제 토큰 수 대신 UTF-8 바이트 길이를 보수적인 토큰 수 상한으로 사용합니다. 현재 byte-level BPE 모델과 800자 제한에서는 청크당 최대 3,200, 배치당 최대 204,800입니다. 정확한 비용·사용 토큰 측정값이 아니며 토크나이저 다운로드도 하지 않습니다. 모델이나 분할 정책 변경 시 이 전제를 재검토해야 합니다.
- 공급자 입력 한도는 [OpenAI 임베딩 API 명세](https://developers.openai.com/api/reference/resources/embeddings/methods/create)의 입력당 8,192토큰·요청 합계 300,000토큰을 확인했습니다(2026-11-07). 코드는 입력 상한을 보수적으로 8,191로 둡니다.
- 반환 벡터의 개수·1536차원·숫자 타입(bool 제외)·유한값·비영벡터를 검증합니다. 모든 배치가 성공해야 결과를 반환하며 실패 시 부분 결과는 반환하지 않습니다. 이미 처리된 공급자 요청의 사용량이 취소되는 것은 아닙니다.
- 공급자 오류와 잘못된 벡터는 `EMBEDDING_ERROR`, 전체 예산 소진은 `INGESTION_TIMEOUT`입니다. 원문 오류를 메시지에 넣지 않습니다. 호출자 취소는 그대로 전파합니다.
- 기본 예산은 100초, 개별 호출 제한은 최대 30초입니다. 이후 적재 서비스에서는 PDF 처리 시간을 뺀 **남은 예산**을 넘겨야 합니다. 현재 이 함수의 제한을 전체 HTTP 적재 제한으로 해석하지 않습니다.

오프라인 검증: `uv run --locked python -m unittest discover -s tests -p test_embedding.py -v`. 모의 클라이언트로 배치 경계·벡터 오류·시간 초과·취소 및 합성 PDF에서 벡터까지를 검증합니다. 실제 모델 API 호출은 수행하지 않았습니다.

## 11. Chroma 저장 (C3)

앱 수명주기당 하나인 `app.state.resources.ingestion`을 사용합니다. `await resources.ingestion.ingest(chunks, embeddings, collection, budget_seconds=남은_초)`에 C2 청크와 공통 클라이언트를 전달하면 임베딩·검증·저장 후 `IngestionResult(document_id, chunk_count)`를 반환합니다. C2 PDF 준비와 이 호출을 잇는 HTTP 라우터는 C4에서 구현합니다.

- 동일 소유자·문서를 처리 중이면 409 `INGESTION_IN_PROGRESS`, 기존 청크가 있으면 임베딩 전에 409 `DOCUMENT_ALREADY_EXISTS`로 거부합니다. 문서 처리 중 잠금을 유지하고 `upsert`나 선삭제는 하지 않습니다.
- UUID를 표준 소문자로 정규화하고, 한 요청에 서로 다른 소유자·문서 ID·파일명이 섞인 청크를 거부합니다. 청크 ID는 `owner_uuid:document_id:0부터순번`입니다.
- `add`에 원문·명시적 벡터·4종 메타데이터·ID를 최대 64개씩 전달합니다. 마지막에 소유자 AND 문서 ID로 조회하여 예상 ID 집합과 개수가 모두 일치하는지 검사합니다.
- 부분 저장·검증 실패·시간 초과 시 이번 요청이 저장을 시도한 ID만 소유자 AND 문서 ID 조건으로 삭제하고 실제 제거를 확인합니다. 정리 실패는 `STORAGE_ERROR`로 보고하고 고정 로그 `ingestion_cleanup_failed`를 남깁니다. 잔재가 남으면 다음 재적재도 409로 거부하며, 삭제·복구는 D단계에서 연결합니다.
- Chroma 동기 작업은 작업 스레드로 실행합니다. 요청 취소 시 작업 종료와 정리를 기다린 뒤 취소를 전파하며, 반복 취소에도 문서 잠금을 먼저 해제하지 않습니다. 취소와 저장 완료가 겹치는 경우도 정리합니다.
- **단일 앱·단일 worker·공유 coordinator 사용**을 전제로 합니다. 외부 writer나 다른 프로세스와의 원자성, 서버 강제 종료 후 자동 복구는 보장하지 않습니다. Chroma 호출 자체를 강제 중단할 수 없어 처리 100초·정리 10초의 하드 상한은 구현하지 않았습니다. 멈춘 저장소에서 빠른 응답보다 작업 완료·정리를 기다리는 방식이며, Backend의 120초 뒤 DELETE 경합은 D단계 검증 대상입니다.

`uv run --locked python -m unittest discover -s tests -p test_ingest.py -v`로 임시 Chroma·모의 임베딩을 검증합니다. 합성 PDF 저장, 클라이언트 종료 후 재개방, 중복, 일부 저장 실패, 다른 소유자·문서 보존, 정리 실패, 시간 초과, 반복 취소를 포함합니다. 실제 교안이나 API를 사용하지 않습니다.

## 12. 다음 단계

실제 임베딩·Groq·OpenAI 연결 테스트의 실행 방법과 기존 성공 기록은 [실제 API 연결 검증](validation/README.md)을 참고하세요. 기본 단위 테스트는 외부 API를 호출하지 않습니다.

다음은 C4 요청 필드 검증·인증 연결·HTTP 오류 매핑입니다. 내부 오류 계약의 API 설계·Mock 정리도 함께 진행합니다. D단계 DELETE API와 적재·삭제 경합, 실제 API 성능 검증은 남아 있습니다. C3의 모의 임베딩·임시 Chroma 성공은 실제 OpenAI 적재나 Backend E2E 검증을 뜻하지 않습니다.
