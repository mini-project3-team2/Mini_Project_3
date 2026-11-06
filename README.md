# MiniProject3 - 2조 - 수업 자료 기반 AI 학습 도우미

> React + Spring Boot + FastAPI(LangChain RAG) 기반 AI 서비스
> 3차 미니프로젝트 · 2026.11.05 ~ 11.13 (산출물 제출·발표 **11/13 금**)

**처음 받았다면 → [⚡ 빠른 시작](#-빠른-시작)부터 따라 하세요.**

| 목차 | |
|---|---|
| [⚡ 빠른 시작](#-빠른-시작) | 처음 받은 팀원이 할 일 (체크리스트) |
| [1. 프로젝트 개요](#1-프로젝트-개요) | 목적 · 아키텍처 · 서비스/포트 |
| [2. 기술 스택](#2-기술-스택) | 공식 버전 · LLM/임베딩 |
| [3. 개발 환경 세팅](#3-개발-환경-세팅) | 설치 · 저장소 세팅 · `.env` · DB |
| [4. 파트별 시작](#4-파트별-시작) | Backend · Frontend · AI · DevOps |
| [5. 로컬 실행](#5-로컬-실행) | 실행 명령 · 주소 |
| [6. 협업 규칙](#6-협업-규칙) | 브랜치 · 커밋 · PR |
| [7. 비밀정보 규칙](#7-비밀정보-규칙) | Key·비밀번호 관리 (**감점 주의**) |
| [8. 산출물·제출물](#8-산출물제출물) | 9종 산출물 · 제출 목록 |
| [9. 문제 해결](#9-문제-해결) | 자주 막히는 상황 |

> 기준 문서: `0.3차프로젝트_가이드.md`(이하 **가이드**), `1-1.프로젝트_평가표.md`(이하 **평가표**), `README.md`

---

## 팀 구성

| 이름 | 역할 | 담당 |
|---|---|---|
| 강찬식 | LLM |  |
| 김지우 | LLM |  |
| 서다영 | DevOps |  |
| 윤수연 | Backend |  |
| 전승호 | Frontend |  |
| 정성재 | Backend |  |

> 역할 예: Team Lead / Backend / Frontend / LLM / DevOps

---

## ⚡ 빠른 시작

> 모든 명령은 **Git Bash** 에서, **저장소 최상위 폴더**에서 실행합니다.

- **1. 프로그램 설치** - Git, Docker Desktop, uv (+ 내 파트 도구) → [3.1](#31-프로그램-설치)
- **2. 커밋 작성자 설정** - GitHub 계정 이메일과 같게 → [3.2](#32-저장소-최초-세팅-1회)
- **3. 저장소 받기 + pre-commit 설치** → [3.2](#32-저장소-최초-세팅-1회)
- **4. `.env` 만들기** - `cp .env.example .env` 후 값 채우기 → [3.3](#33-env-작성)
- **5. DB 실행** - Docker Desktop 켜고 `docker compose up -d` → [3.4](#34-db-실행-확인)
- **6. 내 파트 시작** - 프로젝트가 아직 없으면 생성, 있으면 합류 → [4장](#4-파트별-시작)

---

## 1. 프로젝트 개요

### 목적 (가이드 1.1)

기능을 많이 만드는 것이 아니라, 아래 3가지를 **끝까지 동작하게** 만드는 것이 목표입니다. 평가도 기능의 양이 아니라 **완성도와 근거** 중심입니다.

| # | 목적 | 완성 기준 |
|---|---|---|
| ① | LLM 연동 | Backend → FastAPI(LangChain RAG) → 답변이 화면까지 **스트리밍** |
| ② | 안전한 백엔드 | OWASP Top 10 직접 점검, 취약점 **재현 → 조치 → 재확인** 3건 이상 |
| ③ | 배포 | 전 구성요소 Docker 패키징 → GitHub Actions 이미지 빌드 → EC2 서비스 |

**권장 범위** (가이드 1.2): 도메인 1개 + AI 기능 1개 · 엔티티 3~4개 · 화면 4~6개 · RAG 질의응답 1개를 확실하게

### 아키텍처

```
[사용자] → [Frontend: React] → [Backend: Spring Boot] → [AI Module: FastAPI + LangChain]
                                      ↓                          ↓
                                 [RDB: MariaDB]            [Vector DB: FAISS/Chroma]
```

- Frontend 는 AI Module 을 **직접 호출하지 않습니다.** 반드시 Backend 를 거칩니다.
- AI Module 과 DB 는 **외부에 포트를 공개하지 않습니다.** (평가표 감점 사유)

### 서비스 · 포트

| 서비스 (Compose 이름) | 포트 | 헬스체크 | 운영 외부 공개 |
|---|---|---|---|
| `frontend` | 80 (개발: 5173) | `/` | ✅ |
| `backend` | 8080 | `/actuator/health` | ❌ (frontend nginx 가 `/api` 프록시) |
| `ai-service` | 8000 | `/health` | ❌ |
| `database` | 3306 | `healthcheck.sh` | ❌ |

- Backend API 경로는 모두 **`/api/**`** 로 시작합니다. (개발: Vite 프록시 / 운영: nginx 가 그대로 전달)
- 이 표의 이름·포트·경로는 **산출물 9종 전체에서 동일하게** 씁니다. (가이드 5장)

### 디렉터리 구조

```
.
├── backend/              # Spring Boot
├── frontend/             # React (Vite)          .nvmrc → Node 버전 고정
├── ai-module/            # FastAPI + LangChain   .python-version → Python 버전 고정
├── docs/                 # 개발 산출물 9종
├── .github/              # Actions(비밀정보 검사, Build & Push), PR·이슈 템플릿
├── docker-compose.yml    # 로컬 개발용
├── .env.example          # 환경변수 샘플 (값 없음, Backend·AI·DB 공용)
└── README.md
```

---

## 2. 기술 스택

### 공식 버전 (`README.md`)

> **로컬 버전 = Docker 이미지 버전 = 산출물 문서 버전** 이 같아야 합니다. (가이드 5장)

| 구분 | 기술 · 버전 | 버전 기준 파일 | Docker 이미지 |
|---|---|---|---|
| Frontend | React **19.3.x**, React Router, **Zustand**, Vite | `frontend/package.json` | `node:24-alpine` → `nginx:alpine` |
| Backend | Spring Boot **4.0.x**, Spring Security **7.x**, JPA, Java **17** | `backend/pom.xml` | Maven + `eclipse-temurin:17-jdk` → `eclipse-temurin:17-jre` |
| AI Module | Python **3.12**, uv **0.12.23**, FastAPI, LangChain, Tavily(필요 시) | `ai-module/.python-version`, `uv.lock` | `python:3.12-slim` (+ `ghcr.io/astral-sh/uv:0.12.23`) |
| Database | MariaDB, Vector DB (FAISS 또는 Chroma), Flyway | `docker-compose.yml` | `mariadb:10.11` |
| Infra | Docker, Docker Compose, GitHub Actions, AWS EC2, (Minikube / GCP GKE) | | |

### LLM · 임베딩 (가이드 3.4 · Key 는 강사 제공)

| 구분 | 개발·테스트 (로컬) | 배포 (EC2 / K8s) |
|---|---|---|
| LLM | **Groq** | **OpenAI** |
| 임베딩 | **Ollama `bge-m3`** (1024차원) | **OpenAI `text-embedding-3-small`** (1536차원) |
| Key | `GROQ_API_KEY` | `OPENAI_API_KEY` |

- **코드 수정 없이 환경변수로만 전환**: `LLM_PROVIDER` · `LLM_MODEL` · `EMBEDDING_PROVIDER` · `EMBEDDING_MODEL`
- 차원이 달라 **개발 인덱스를 배포로 복사하지 않고 다시 적재(인덱싱)** 합니다. 경로에 모델명을 넣습니다. (예: `faiss_index/docs_bge-m3/`)
- OpenAI 모델로 통합 테스트합니다. (OutputParser·Tool 호출 결과가 모델마다 다를 수 있음)

<details>
<summary><b>기준 문서가 요구하는 기술 (평가 항목)</b> - 펼치기</summary>

| 구분 | 요구 기술 | 근거 |
|---|---|---|
| Frontend | React Router(DOM), 전역 상태 **Zustand**, AI 채팅 UI(**스트리밍**), 파일 업로드 UI, 로딩 피드백(LoadingSpinner), 반응형 | 가이드 3.1, 평가표 FE |
| Backend | JPA(엔티티 3~4개·연관관계), Spring Data JPA, JWT, RESTful API, `@Valid`, AI 연동 **RestClient/WebClient**(타임아웃·에러·Fallback) | 가이드 3.1, 평가표 BE |
| AI | FastAPI REST + **SSE**, LangChain RAG(로드→분할→임베딩→검색→생성), FAISS/Chroma | 가이드 3.1, 평가표 AI |
| AI (가산) | LangGraph / `create_agent`, Tool(**Tavily**), LangSmith | 가이드 3.2·3.5, 평가표 AI |
| Database | MariaDB, **Flyway** (`ddl-auto: validate`) | 가이드 6장, 평가표 배포 |
| 보안 | OWASP Top 10 점검, Burp Suite, SBOM(CVE), `npm audit` | 가이드 3.3, 평가표 보안 |
| Infra | Docker(멀티스테이지·경량·HEALTHCHECK), Compose, Docker Hub, GitHub Actions, EC2, (Minikube/GKE) | 평가표 배포 |

> **Tavily** 는 가이드상 "필요한 경우" 선택이지만, 평가표 AI 항목이 "LLM + VectorDB + Tool(Tavily) 결합", "내부 문서와 외부 정보 결합"을 평가하므로 **결합을 권장**합니다.

</details>

---

## 3. 개발 환경 세팅

> 명령은 **Git Bash** 기준입니다. (Windows 는 Git 설치 시 함께 설치됨 · cmd 에서는 `cp`·`openssl` 이 동작하지 않음)

### 3.1 프로그램 설치

**전원 공통**

| 프로그램 | 용도 | 설치 |
|---|---|---|
| Git (+ Git Bash) | 버전 관리, 터미널 | <https://git-scm.com/downloads> |
| Docker Desktop | DB·전체 서비스 실행 | <https://www.docker.com/products/docker-desktop/> (Windows: WSL2 기반) |
| uv **0.12.23** | pre-commit 설치, AI 모듈 | 아래 명령 |
| IDE | IntelliJ (BE) / VS Code (FE·AI) | |

```bash
# uv 설치 - Windows (PowerShell 에서)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# uv 설치 - macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# 터미널을 새로 열고 버전 맞추기
uv self update 0.12.23
```

**내 파트만**

| 파트 | 설치 |
|---|---|
| Backend | JDK 17 - Temurin <https://adoptium.net/> |
| Frontend | Node.js 24 LTS - <https://nodejs.org/> (또는 nvm-windows / fnm) |
| AI | Ollama <https://ollama.com/download> → `ollama pull bge-m3` |
| 보안 점검 (Day 4) | Burp Suite |
| DevOps | Docker Hub 계정·Access Token, AWS 계정·EC2 키페어 |

**설치 확인**

```bash
git --version
docker compose version     # v2 이상 (docker-compose v1 사용 금지)
uv --version               # 0.12.23
java -version              # Backend: 17
node -v                    # Frontend: v24.x
ollama list                # AI: bge-m3 표시
```

### 3.2 저장소 최초 세팅 (1회)

```bash
# 1) 커밋 작성자 = GitHub 계정 이메일 (평가표: 커밋 로그로 개인 기여도 측정)
git config --global user.name  "홍길동"
git config --global user.email "GitHub 에 등록된 이메일"

# 2) 저장소 받기
git clone <저장소 URL>
cd <저장소 폴더>

# 3) 커밋 전 비밀정보 자동 검사
uv tool install pre-commit        # 못 찾으면: uv tool update-shell 후 터미널 재시작
pre-commit install

# 4) 환경변수 파일
cp .env.example .env
```

### 3.3 `.env` 작성

`.env` 는 **저장소 최상위**(`docker-compose.yml` 옆)에 둡니다. Backend·AI 모듈도 이 파일을 읽습니다.

| 변수 | 누가 / 무엇을 | 예시 |
|---|---|---|
| `MARIADB_ROOT_PASSWORD`<br>`MARIADB_PASSWORD` | **각자** 랜덤 생성 (내 PC 전용, 공유 불필요) | `openssl rand -hex 24` |
| `MARIADB_DATABASE`<br>`MARIADB_USER` | **팀 공통** 이름 (`root` 사용 불가) | `mp3db`, `mp3user` |
| `JWT_SECRET`<br>`AI_INTERNAL_TOKEN` | **각자** 랜덤 생성 | `openssl rand -hex 32` |
| `GROQ_API_KEY` | **강사 제공** (팀 DM 으로만 공유) | |
| `LLM_MODEL` | **AI 담당이 정해 공지** (Groq 모델명) | |
| `OPENAI_API_KEY` | 통합 테스트부터 (강사 제공) | |
| `TAVILY_API_KEY`, `LANGSMITH_*` | 사용할 때만 | |
| 나머지 | `.env.example` 기본값 그대로 | |

> ⚠️ 값에 **`$` 와 따옴표를 쓰지 않습니다.** (Compose 는 `$` 를 변수로 해석해 값이 잘리고, Spring 은 따옴표를 값으로 읽음)

### 3.4 DB 실행 확인

**Docker Desktop 을 먼저 켠 뒤:**

```bash
docker compose up -d
docker compose ps         # database 가 (healthy) 이면 완료
```

---

## 4. 파트별 시작

| 상황 | 할 일 |
|---|---|
| 내 파트 프로젝트가 **아직 없음** | 파트 **담당자 1명**이 아래 파트별 절차로 생성 → PR (동시에 생성하면 충돌) |
| 이미 **생성되어 병합됨** | [합류하는 팀원](#합류하는-팀원) 명령만 실행 |

> - 각 폴더의 기존 파일(`.dockerignore`, `.env.example`, `.nvmrc`, `.python-version`)을 **지우지 마세요.**
> - 2차 프로젝트·수업 실습 코드를 **재사용해도 됩니다** (가이드 1.2). 원본의 `.git` 폴더를 빼고 복사한 뒤 아래 설정을 맞춥니다.
> - **Day 2 부터 인증·소유자 검증을 함께 구현**합니다. (가이드 4장 - 보안을 마지막에 몰지 않음)

### 합류하는 팀원

```bash
git checkout main && git pull
docker compose up -d                 # DB (Docker Desktop 실행 상태)

# ↓ 내 파트 하나만 실행 (저장소 최상위에서)
cd backend   && ./mvnw spring-boot:run
cd frontend  && npm install && cp .env.example .env.local && npm run dev
cd ai-module && uv sync && uv run uvicorn src.api.main:app --reload --port 8000

# 작업은 항상 새 브랜치에서
git checkout -b feature/<기능>
```

<details>
<summary><b>🟦 Backend - 최초 생성 절차</b></summary>

1. **Spring Initializr**: Maven / Java 17 / **Spring Boot 4.0.x**
   - 의존성: Spring Web, Spring Data JPA, Spring Security, Validation, MariaDB Driver, Flyway Migration, Actuator, Lombok
2. 받은 zip 의 **내용물**을 `backend/` 바로 아래에 풉니다. (`backend/backend/` 가 되지 않게)
3. **첫 커밋 전** `mvnw` 실행 권한 등록 (Windows 에서 빠지면 Docker 빌드 시 `Permission denied`):
   ```bash
   git update-index --add --chmod=+x backend/mvnw
   ```
4. **Spring Boot 4 주의사항** (실습 코드를 가져올 때 특히)

   | 항목 | 확인할 것 |
   |---|---|
   | Flyway | `spring-boot-starter-flyway` + `flyway-mysql` 필요 (`flyway-core` 만으로는 자동 설정 안 됨) |
   | RestClient | `RestClient.Builder` 주입 실패 시 `spring-boot-starter-restclient` 추가 |
   | Jackson 3 | 패키지 `com.fasterxml.jackson` → `tools.jackson` |
   | Security 7 | `SecurityConfig` 이전 시 삭제된 API 컴파일 오류 확인 |

5. **`application.yml`**:
   ```yaml
   spring:
     config:
       # Spring 은 .env 를 자동으로 읽지 않으므로 import (파일이 없으면 무시 → Docker 영향 없음)
       import: "optional:file:.env[.properties],optional:file:../.env[.properties]"
     datasource:
       url: jdbc:mariadb://${DB_HOST}:${DB_PORT}/${MARIADB_DATABASE}
       username: ${MARIADB_USER}        # root 가 아닌 앱 전용 계정
       password: ${MARIADB_PASSWORD}
     jpa:
       hibernate:
         ddl-auto: validate             # 스키마는 Flyway 로만 변경 (update 금지)

   jwt:
     secret: ${JWT_SECRET}
     access-expiration: ${JWT_ACCESS_EXPIRATION}
     refresh-expiration: ${JWT_REFRESH_EXPIRATION}

   management:
     endpoints:
       web:
         exposure:
           include: ${ACTUATOR_EXPOSURE:health,info}   # Actuator 노출 최소화
   ```

   | 실행 위치 | `DB_HOST` | `DB_PORT` | `AI_SERVICE_URL` |
   |---|---|---|---|
   | PC 에서 직접 | `localhost` | `DB_LOCAL_PORT` 값 | `http://localhost:8000` |
   | Compose 안 (Day 3~) | `database` | `3306` | `http://ai-service:8000` |

   - Actuator: **`/actuator/health` 만 `permitAll()`** (Docker HEALTHCHECK 용), 나머지 `/actuator/**` 는 ADMIN 전용. health 규칙을 먼저 작성합니다.
6. 패키지: `controller/` `service/` `repository/` `entity/` `dto/` `config/`
   - 테이블·컬럼은 **snake_case** → Flyway SQL(`src/main/resources/db/migration/V1__init.sql`)과 `@Table`·`@Column` 일치
7. **평가표 BE 체크**: `@Transactional` 범위 · 페이징·정렬 · Custom Query · `@NotNull`/`@Size`/`@Pattern` · RESTful URL (변경·삭제에 GET 금지)
8. AI 호출: **RestClient 또는 WebClient** + 타임아웃·에러 핸들링·Fallback
9. SBOM: `cyclonedx-maven-plugin` 추가 → `./mvnw package` → `target/bom.json` → CVE 확인 결과를 보안점검서에
10. 실행: `./mvnw spring-boot:run` (cmd 는 `mvnw.cmd`) 또는 IntelliJ

</details>

<details>
<summary><b>🟩 Frontend - 최초 생성 절차</b></summary>

1. `node -v` 가 **v24.x** 인지 확인 후, 저장소 최상위에서:
   ```bash
   npm create vite@latest frontend -- --template react     # TypeScript 로 정했다면 react-ts
   ```
   - "폴더가 비어있지 않음" 질문 → **`Ignore files and continue`** 선택
     (`Remove existing files` 를 고르면 `.dockerignore`·`.env.example`·`.nvmrc` 가 삭제됨)
   - nvm-windows 는 `.nvmrc` 를 읽지 않으므로 `nvm install 24` → `nvm use 24` (fnm 은 `fnm use`)
2. `package.json` 의 `react`·`react-dom` 이 **19.3.x** 인지 확인
3. 환경변수: `cd frontend && cp .env.example .env.local`
4. `vite.config.js` 에 Backend 프록시 (CORS 없이 개발, 운영 nginx 와 같은 `/api` 경로):
   ```js
   server: {
     proxy: { '/api': 'http://localhost:8080' },
   },
   ```
   API 주소는 `import.meta.env.VITE_API_URL ?? '/api'` 처럼 기본값을 둡니다.
5. 추가 설치:
   ```bash
   npm install react-router-dom zustand     # Redux 는 사용하지 않음 (가이드 3.1·평가표: Zustand)
   ```
   HTTP 클라이언트(fetch / axios)는 팀이 정하고, 401(토큰 만료) 처리를 공통 모듈 한 곳에서 합니다.
6. 폴더: `src/components/` `src/pages/` `src/services/` `src/store/` `src/hooks/` `src/utils/`
7. **평가표 FE 체크**: 컴포넌트 단일 책임·재사용 · 커스텀 Hook · **LoadingSpinner** · 반응형 · **AI 채팅(스트리밍)** · **파일 업로드 UI**
   - 스트리밍은 `fetch` + `ReadableStream` 권장 (POST + JWT 헤더가 필요해 `EventSource` 부적합)
   - AI 응답은 **`dangerouslySetInnerHTML` 없이** 렌더링 (XSS)
   - Tavily 사용 시 답변의 **출처(URL)** 표시
8. `npm audit` 결과와 조치를 보안점검서에 기록
9. 실행: `npm install` → `npm run dev` (http://localhost:5173)

</details>

<details>
<summary><b>🟪 AI - 최초 생성 절차</b></summary>

1. 저장소 안에서 (`.python-version` 의 3.12 자동 적용):
   ```bash
   cd ai-module
   uv init --app .
   uv add fastapi "uvicorn[standard]" python-dotenv langchain langchain-community langchain-text-splitters
   uv add langchain-groq langchain-ollama langchain-openai   # 개발(Groq·Ollama) / 배포(OpenAI)
   uv add faiss-cpu               # 또는 langchain-chroma
   uv add pypdf docx2txt          # 업로드 문서 로더 (지원 형식은 팀 확정)
   uv add langchain-tavily        # 웹 검색 Tool (필요 시)
   # (선택·가산) uv add langgraph langsmith
   ```
2. 구조: `src/api/`(FastAPI) `src/chains/`(LangChain) `src/core/` `src/utils/`
   - `main.py` → `src/api/main.py` 로 이동, `src/`·`src/api/` 에 빈 `__init__.py`
   - 헬스체크 `GET /health` 필수 (Compose·Dockerfile HEALTHCHECK)
3. `.env`: `load_dotenv()` 가 상위 폴더의 루트 `.env` 를 찾습니다.
4. **모델 전환** (가이드 3.4): `LLM_PROVIDER`/`LLM_MODEL`, `EMBEDDING_PROVIDER`/`EMBEDDING_MODEL` 로 분기. **모델명·공급자·키를 코드에 쓰지 않습니다.**
   - 인덱스 경로에 모델명: `faiss_index/docs_bge-m3/`, `faiss_index/docs_text-embedding-3-small/`
   - 배포(EC2)는 OpenAI 임베딩이므로 EC2 에 Ollama 불필요
5. **웹 검색** (가이드 3.5, 필요 시): `TavilySearch(max_results=3)` 를 RAG 검색 Tool 과 함께 `create_agent(tools=[...])` 에 등록, 시스템 프롬프트에 "내부 문서 우선, 없으면 웹 검색 + 출처(URL) 표시"
   - 웹 검색 결과는 외부 입력 (간접 Prompt Injection 주의)
   - Tool 호출은 **Groq·OpenAI 둘 다** 테스트
6. **평가표 AI 체크**: REST API 설계 · **SSE 스트리밍** · 에러 처리 · RAG 품질
   - 비용 방지: 질문 길이 제한, `max_tokens`
   - (권장) 사용자별 문서 격리, Backend→AI 내부 인증 (`AI_INTERNAL_TOKEN` 헤더 검증)
7. 실행: `uv run uvicorn src.api.main:app --reload --port 8000`
8. 커밋: `uv.lock`, `.python-version` 은 **커밋**, `.venv` 는 자동 제외
   - `data/`, `uploads/`, `faiss_index/`, `chroma_db/` 는 Git·이미지 **제외** → 저장소에 넣을 RAG 기본 문서는 `ai-module/seed_docs/` 처럼 다른 폴더에

</details>

<details>
<summary><b>🟧 DevOps - 일정과 GitHub 설정</b></summary>

**GitHub 설정 (저장소 생성 직후)**

- [ ] Settings → General → Pull Requests: **Allow merge commits 만** 허용 (Squash·Rebase 해제)
- [ ] Settings → Branches: `main` 보호 (PR 필수, 승인 1명, status check `gitleaks` 필수)
- [ ] Settings → Code security: Secret scanning, Push protection 활성화
- [ ] Issues → Labels: `security` 라벨 생성
- [ ] Settings → Secrets and variables → Actions:
  - `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
  - 배포용 `OPENAI_API_KEY`, `TAVILY_API_KEY`, `JWT_SECRET`, DB 비밀번호 → EC2 `.env` 또는 K8s Secret 으로 전달 (가이드 3.4)
  - (가산: EC2 자동 배포) `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY` - 배포 가이드에는 **이름만** 기재

**일정 (가이드 4장)**

| Day | 작업 | 평가표 포인트 |
|---|---|---|
| 1 | 저장소·브랜치 규칙·로컬 DB(Compose) ← **이 저장소** | |
| 2 | 모듈별 Dockerfile 초안 | 멀티스테이지 · 경량 이미지 · HEALTHCHECK |
| 3 | **로컬 Compose 전체 기동** | 네트워크 · 볼륨 · 환경변수 · `depends_on` |
| 4 | GitHub Actions (이미지 빌드 → Docker Hub Push) | |
| 5 | EC2 배포 (Compose) - 운영에서는 `database`·`ai-service` 의 `ports` 미게시 | |
| 선택 | Kubernetes: Minikube 또는 GKE **택1** (최대 +3점, GKE 는 시연 후 클러스터 삭제) | |

</details>

---

## 5. 로컬 실행

| 대상 | 명령 | 주소 |
|---|---|---|
| DB | `docker compose up -d` | localhost:3306 (`DB_LOCAL_PORT`) |
| Backend | `./mvnw spring-boot:run` | http://localhost:8080 |
| AI Module | `uv run uvicorn src.api.main:app --reload --port 8000` | http://localhost:8000 |
| Frontend | `npm run dev` | http://localhost:5173 |

```bash
docker compose ps                  # 상태 확인
docker compose logs -f database    # 로그
docker compose down                # 중지 (데이터 유지)
docker compose down -v             # 중지 + DB 초기화
```

---

## 6. 협업 규칙

> 평가: 개별 70% / 팀 30%. 개인 기여도는 **Git 커밋 로그**(커밋 수·빈도·메시지·브랜치)로 측정합니다.

| 규칙 | 내용 |
|---|---|
| 커밋 작성자 | **본인 GitHub 계정 이메일** ([3.2](#32-저장소-최초-세팅-1회)) |
| 브랜치 | `main`(배포) / `feature/*` (버그는 `fix/*`) → **PR 로만 병합**, `main` 직접 푸시 금지 |
| PR 병합 | **Create a merge commit** (Squash 금지 - 개별 커밋이 사라짐) |
| 커밋 메시지 | `feat: 문서 업로드 API` · `fix(security): 타 사용자 문서 조회 차단` · `docs:` `chore:` `ci:` `refactor:` `test:` |
| 커밋 금지 | `.env`, 키 파일, `node_modules`, 빌드 산출물 (`.gitignore` 로 차단됨) |
| 스탠드업 | 매일 15분: 어제 한 일 / 오늘 할 일 / 막힌 점 |

**보안 이슈 → 수정 커밋 연결** (평가표 "보안 조치 커밋의 기여도")

```
Issue (보안 점검 발견사항 템플릿)  →  fix(security): ... 커밋  →  PR 에 "Closes #이슈번호"
```

---

## 7. 비밀정보 규칙

> 🚨 **평가표 감점**: 소스·설정파일·Git 이력에 API Key, 비밀번호, JWT secret 이 노출되면 **설정·운영 보안 항목 0점**

1. `.env`·키 파일·비밀번호는 **절대 커밋하지 않습니다.** 저장소에는 `.env.example` 만 둡니다.
2. 새 환경변수는 `.env.example` 에 **이름만** 추가합니다. `application*.yml` 의 비밀값은 `${JWT_SECRET}` 처럼 **환경변수 참조로만** 씁니다.
3. Key 는 `.env`(로컬)와 **GitHub Secrets**(CI·배포)에만 둡니다. `.env.prod` 같은 파일을 저장소에 두지 않습니다.
4. **강사 제공 Key 는 팀 내부에서만.** 코드·커밋·로그·캡처·발표 자료에 노출하지 않습니다.
5. 보안점검서·이슈·발표 자료의 Burp 캡처는 **JWT·쿠키·Key 를 마스킹**합니다. (예: `Bearer eyJhbGci...(생략)`)
6. pre-commit(로컬)과 GitHub Actions `Secret Scan`(전체 Git 이력)이 자동 검사합니다.
7. ⚠️ Key 를 푸시했거나 유출이 의심되면 **즉시 강사에게 알려** 폐기·재발급합니다. (커밋 삭제만으로는 부족)

---

## 8. 산출물·제출물

`docs/` 폴더에 9종을 정리합니다. (PDF / Word / Markdown)

| # | 문서 | 핵심 포인트 |
|---|---|---|
| 1 | 프로젝트 계획서 | 목적, 팀 구성, 일정, 보안 요구사항 |
| 2 | 시스템 아키텍처 설계서 | 구성도, 보안 아키텍처 (신뢰 경계·인증 방식·비밀정보 관리) |
| 3 | 데이터베이스 설계서 | ERD, 테이블, Vector DB 구성 |
| 4 | API 설계서 | 엔드포인트, 인증 여부, 오류 응답 (**403**·로그인 잠금 포함) |
| 5 | Backend 개발 명세서 | 구조, 설정, 보안 구현 방식 |
| 6 | Frontend 개발 명세서 | 페이지·컴포넌트, 상태관리, 프론트엔드 보안 |
| 7 | AI 모듈 연동 명세서 | FastAPI API, RAG, AI 보안, **환경별 모델** |
| 8 | 컨테이너 배포 가이드 | Dockerfile, Compose, 비밀정보 관리, GitHub Actions, EC2, (K8s) |
| 9 | 보안 점검서 | OWASP 점검표, 취약점 조치 3건 이상 (전/후 코드 · 재확인 근거) |

**작성 규칙**
- 기술 스택·포트·API 경로는 [2장](#2-기술-스택)·[서비스·포트](#서비스--포트) 표와 **일치**시킵니다.
- 보안점검서에는 **실제로 시도한 결과만** 적습니다.
- 2025년 샘플의 보안 부분은 참고하지 않으며, 샘플 복사는 인정되지 않습니다.
- 템플릿 예시값은 공식 값으로 교체합니다:

  | 템플릿 예시 | → 공식 값 |
  |---|---|
  | Spring Boot 3.2 | 4.0.x |
  | React 18 / Redux | 19.3.x / **Zustand** |
  | Python 3.11 / `python:3.11-slim` | 3.12 / `python:3.12-slim` |
  | `node:20-alpine` | `node:24-alpine` |
  | 벡터 차원 1536 (단일) | 개발 1024 / 배포 1536 |
  | AI 환경변수 | 가이드 3.4 변수명 |

**제출물 (11/13 금)**
1. GitHub Repository URL - README 포함, **실행 가능한 상태**, 비밀정보 미포함 (`.env.example` 제공)
2. 개발 산출물 9종
3. 발표 자료 (PPT/PDF, 30~40분) - **보안 점검 사례 1~2건 시연**, **배포 구조·CI/CD 흐름** 필수
4. 데모 동영상 (선택)

---

## 9. 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| `docker compose up` 시 `.env 에 ... 를 설정하세요` | `.env` 의 `MARIADB_*` 4개가 비어 있음 → [3.3](#33-env-작성) |
| `database` 가 `(healthy)` 가 안 되고 재시작 반복 | `MARIADB_USER=root` 사용 불가 → 다른 이름으로 바꾸고 `docker compose down -v` 후 다시 `up` |
| DB 접속 실패인데 비밀번호는 맞아 보임 | 값에 `$`·따옴표가 있음 → 영문+숫자로 다시 생성 |
| `port is already allocated` (3306) | `.env` 에서 `DB_LOCAL_PORT=3307` 로 바꾸고 다시 `up` |
| `docker` 명령이 응답 없음 | Docker Desktop 이 꺼져 있음 → 실행 후 재시도 |
| `cp` / `openssl` 을 찾을 수 없음 | cmd 사용 중 → **Git Bash** 에서 실행 |
| `pre-commit` 명령을 찾을 수 없음 | `uv tool update-shell` 후 터미널 재시작 |
| 첫 커밋이 실패하고 파일이 수정됨 | pre-commit 이 줄바꿈 등을 자동 수정한 것 → `git add` 후 다시 커밋 |
| 커밋이 `gitleaks` 로 막힘 | 키·토큰이 포함됨 → 해당 값 제거 (캡처·문서의 JWT 는 마스킹) |
| Spring 기동 시 `${JWT_SECRET}` 을 못 찾음 | `application.yml` 의 `spring.config.import` 누락 또는 `.env` 위치가 최상위가 아님 |
| Docker 빌드 시 `./mvnw: Permission denied` | `git update-index --add --chmod=+x backend/mvnw` 후 커밋 |
| Vite 생성 후 `.dockerignore` 등이 사라짐 | `Remove existing files` 를 선택함 → `git checkout -- frontend/` 로 복구 후 `Ignore files` 로 다시 생성 |
| AI 모듈(Docker)이 Ollama 에 연결 못 함 | `OLLAMA_BASE_URL=http://host.docker.internal:11434` (Linux 는 Compose 에 `extra_hosts: ["host.docker.internal:host-gateway"]`) |
| 임베딩 차원 불일치 오류 | 다른 모델로 만든 인덱스를 사용 중 → 인덱스 경로에 모델명을 넣고 다시 적재 |
| 복사해 온 폴더의 파일이 커밋되지 않음 | 안에 `.git` 폴더가 있음 (중첩 저장소) → `.git` 삭제 후 다시 `git add` |
