# AI 모듈 개발 환경 준비

현재 단계는 환경 준비입니다. FastAPI 앱과 `pyproject.toml`은 다음 구현 단계에서 추가합니다.

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
- 아직 실행 코드가 없으므로 이 단계에서 FastAPI 기동이나 API 연결이 검증된 것은 아닙니다.

## 4. 다음 단계

`pyproject.toml`과 `uv.lock`을 추가할 때 Python 3.12 호환성을 확인하고 의존성을 잠급니다. 설정 로더는 실행 위치에 관계없이 루트 `.env`를 읽고, 실행 환경변수가 파일 값보다 우선하도록 구현합니다.
