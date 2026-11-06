# AI 모듈 개발 환경 준비

현재 단계는 Python 프로젝트와 의존성 준비입니다. `pyproject.toml`과 `uv.lock`은 추가됐으며, FastAPI 앱은 다음 작업에서 구현합니다.

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
- 공통 설정 로더만 구현된 상태로, FastAPI 기동이나 API 연결이 검증된 것은 아닙니다.

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

## 6. 다음 단계

FastAPI 앱·헬스체크를 만들고 시작 시 설정 로더를 연결합니다. 내부 인증 의존성과 임베딩 클라이언트의 구현·검증도 아직 남아 있습니다.
