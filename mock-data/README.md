# AskNote Mock 데이터

`docs/4.API설계서.md`의 요청 · 응답 형식을 그대로 따른 Mock 데이터입니다. Backend가 완성되기 전에 Frontend가 실제와 같은 데이터로 화면을 만들고, Backend는 같은 JSON을 테스트 기대값으로 쓰는 것이 목적입니다.

- 기준 문서: `docs/4.API설계서.md`, `docs/3.데이터베이스설계서.md`
- API 설계서가 바뀌면 이 폴더도 함께 고칩니다 (API 계약 변경은 합의 후 문서 먼저)

## 폴더 구성

```text
mock-data/
├── data/          # 메모리 DB 역할의 원본 데이터
│   ├── members.json      테스트 회원 6명 (아래 표)
│   ├── documents.json    자료 5개 (READY · INDEXING, 다른 회원 자료 포함)
│   └── chats.json        질문 기록 14건 (student 13건 + 다른 회원 1건)
├── requests/      # 요청 본문 예시 (Postman · 테스트에 그대로 사용)
├── responses/     # API별 정상 · 오류 응답 예시 (파일명 = 상황.상태코드)
├── sse/           # 질문 스트리밍(/api/chats/stream) 이벤트 예시
│   ├── *.txt             실제 SSE 형식 그대로 (event: · data: · 빈 줄)
│   └── *.events.json     같은 내용을 배열로 (MSW 핸들러에서 반복하며 흘려보낼 때 사용)
├── internal/      # Backend 테스트용 가짜 AI Module 응답 (6장 내부 API)
├── pdfs/          # AI 적재 검증용 PDF 5개 (React, Git, 정보보안학 01~03)
└── gen.py         # 위 JSON을 다시 만드는 스크립트 (저장소 최상위에서 python mock-data/gen.py)
```

## 테스트 계정

| 이메일 | 비밀번호 | 상태 | 확인할 화면 |
|---|---|---|---|
| student@test.com | Test1234! | 정상 | 기본 계정 — READY 자료 2개 + INDEXING 1개, 질문 기록 13건(10 · 3, 2페이지), 피드백 HELPFUL · NOT_HELPFUL · 미선택 섞임 |
| empty@test.com | Test1234! | 정상 | 자료 · 기록 없음 — 채팅 "자료 없음" 화면(3-2), 빈 목록 |
| indexing@test.com | Test1234! | 정상 | INDEXING 자료만 있음 — 질문 시 400 `NO_DOCUMENT` |
| locked@test.com | Test1234! | 잠김 | 로그인 시 423 `ACCOUNT_LOCKED` (`lockedUntil` 포함) |
| other@test.com | Test1234! | 정상 | 자료 id 21 · 기록 id 201 소유 — student로 삭제 · 피드백 시 403 (IDOR 확인) |
| admin@test.com | Admin1234! | ADMIN | 화면 없음 — Actuator 접근 확인용 (실제 서버는 환경 변수로 생성) |

> `members.json`의 `password` · `_note`는 Mock 전용 필드입니다. 실제 API 응답에는 비밀번호가 포함되지 않으며, 실제 서버의 비밀번호와 무관한 테스트 값입니다.

## 토큰 규칙 (Mock 전용)

- 로그인 응답: `accessToken` = `mock-access-token-{회원 id}`, `refreshToken` = `mock-refresh-token-{회원 id}`
- `Authorization: Bearer expired`로 요청하면 401 `UNAUTHORIZED` → 화면의 재발급 처리 확인
- 실제 JWT가 아니라 문자열이므로 화면은 토큰 내용을 해석하지 않습니다

## 응답 파일 목록

| API | 파일 |
|---|---|
| POST /api/auth/signup | `auth/signup.201` · `signup.400-invalid-input` · `signup.409-duplicate-email` |
| POST /api/auth/login | `auth/login.200` · `login.401-invalid-credentials` · `login.423-account-locked` |
| POST /api/auth/refresh | `auth/refresh.200` · `refresh.401-invalid-refresh-token` |
| POST /api/auth/logout | 204 (본문 없음) |
| POST /api/documents | `documents/upload.201` · `upload.400-invalid-file-type` · `upload.400-empty-file` · `upload.413-file-too-large` · `upload.422-text-extraction-failed` · `upload.503-ai-unavailable` |
| GET /api/documents | `documents/list.200` · `list-indexing-only.200` · `list-empty.200` |
| DELETE /api/documents/{id} | 204 / `common/403-forbidden` / `documents/delete.404-document-not-found` |
| POST /api/chats/stream | `sse/stream-success` · `sse/stream-not-found` · `sse/stream-error` / `chats/stream.400-no-document` |
| GET /api/chats | `chats/list.200-page0` · `list.200-page1` · `list-empty.200` |
| PATCH /api/chats/{id}/feedback | `chats/feedback.200` / `common/403-forbidden` / `chats/feedback.404-chat-not-found` |
| 공통 | `common/400-invalid-input` · `401-unauthorized` · `403-forbidden` · `500-internal-server-error` |

## 데이터 규칙 (서버 규칙과 동일)

- 응답은 `{ success, data, message }`, 실패는 `{ success: false, data: null, message, code }` (API 설계서 2장)
- 날짜는 한국 시간 `yyyy-MM-ddTHH:mm:ss` (Z 없음)
- 자료 · 기록 목록은 최신순, 질문 기록만 페이징 (`page`는 0부터, `size`는 10)
- 출처 `page`는 PDF 페이지 번호로 1부터
- 질문은 `READY` 자료가 1개 이상일 때만 가능 (INDEXING만 있으면 400 `NO_DOCUMENT`)
- 남의 자료 · 기록에 삭제 · 피드백 요청 시 403

## 사용 방법

- **Frontend (MSW):** `msw/` 핸들러를 만들 때 `data/`를 메모리 DB로 읽고, 응답은 `responses/` 형식을 따릅니다. 스트리밍은 `sse/*.events.json`을 순서대로 `event: ...\ndata: ...\n\n` 형식으로 흘려보내면 됩니다. 개발 모드에서 기본으로 켜고, `VITE_USE_MOCK=false`로 끕니다
- **Backend:** 테스트 기대값으로 `responses/`를, 가짜 AI Module 응답으로 `internal/`을 씁니다
- **AI Module:** `internal/` 형식이 실제 응답과 같아야 합니다 (`done`은 `{}`, `error`는 `{"code": ...}`)
- **PDF 적재 검증:** `pdfs/`의 PDF를 사용합니다. JSON 응답에 등장하는 예시 파일명과는 별개의 실제 검증 자료이며, `gen.py`로 생성되지 않습니다.
