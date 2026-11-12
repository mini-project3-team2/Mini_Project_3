# AskNote Frontend

React + Vite 로 만든 AskNote 화면입니다. 화면 · 컴포넌트 · 상태 관리 · 보안 구현 방식은 [`docs/6.Frontend개발명세서.md`](../docs/6.Frontend개발명세서.md)가 기준입니다.

## 실행

Node 24 (`.nvmrc`) 기준입니다.

```bash
npm install
cp .env.example .env.local
npm run dev        # http://localhost:5173
```

- `/api` 요청은 Vite 프록시가 `http://localhost:8080`(Backend)으로 넘깁니다.
- Backend 없이 화면만 볼 때는 `.env.local` 에서 `VITE_USE_MOCK=true` 로 두면 MSW 가 `mock-data/` 기반 응답을 돌려줍니다 (개발 서버 전용).
- `VITE_` 변수는 빌드 결과물에 그대로 들어가므로 키 · 비밀번호를 넣지 않습니다.

## 명령

| 명령 | 내용 |
|------|------|
| `npm run dev` | 개발 서버 |
| `npm run build` | 운영 빌드 (`dist/`, MSW 워커 제외) |
| `npm run lint` | ESLint |
| `npm run preview` | 빌드 결과 미리 보기 |

## 폴더

| 경로 | 내용 |
|------|------|
| `src/pages/` | 로그인 · 회원가입 · AI 학습 채팅 · 내 자료 · 질문 기록 |
| `src/components/` | 화면 공통 컴포넌트 |
| `src/hooks/` | 답변 스트리밍 · 자료 · 기록 Hook |
| `src/store/` | Zustand 상태 |
| `src/services/` | axios 공통 모듈, 답변 스트리밍(`fetch`) |
| `src/mocks/` | MSW 핸들러 |
| `nginx.conf` | 운영 Nginx 설정 (`/api` 프록시, 요청 횟수 제한, 보안 헤더) |

## Docker

`Dockerfile` 은 `node` 로 빌드한 뒤 비root `nginx-unprivileged`(포트 8080)로 실행합니다. 이미지 · 배포 절차는 [`docs/8.컨테이너배포가이드.md`](../docs/8.컨테이너배포가이드.md)를 참고합니다.
