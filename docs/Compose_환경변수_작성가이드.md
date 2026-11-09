# Compose 환경 변수 작성 가이드

> 대상: DevOps (`docker-compose.yml` · `docker-compose.prod.yml` 작성)
> 작성: 윤수연 (Backend 1) · 팀 결정 반영

## 1. 결정 사항

- `.env` 파일은 지금처럼 **저장소 루트에 하나만** 둔다 (로컬 · EC2 모두)
- Compose에서는 `env_file: .env`를 쓰지 않고, **서비스별 `environment:`에 그 서비스가 쓰는 변수만** 적는다

**이유**

- `env_file: .env`를 쓰면 모든 컨테이너가 모든 비밀 값을 받는다 (Backend에 OpenAI 키, AI에 DB 비밀번호)
- 한 컨테이너가 뚫리면 다른 서비스의 키까지 노출된다 → 필요한 것만 넘겨 **최소 권한 원칙**을 지킨다
- 파일을 서비스별로 나누면 `AI_INTERNAL_TOKEN` · DB 계정 같은 공통 값이 중복되고, 팀원 세팅도 다시 바꿔야 한다 → 파일은 하나로 유지한다

## 2. 작성 규칙

1. `${변수}`는 Compose가 루트 `.env`에서 자동으로 채운다. **값을 Compose 파일에 직접 쓰지 않는다**
2. 컨테이너 주소(`DB_HOST`, `AI_SERVICE_URL`)는 `.env` 대신 **Compose에 직접** 적는다 (로컬 `.env`는 `127.0.0.1` 기준이라 컨테이너에서는 맞지 않음)
3. `SPRING_PROFILES_ACTIVE`는 **넣지 않는다** (`local`을 켜면 테스트 계정 · 데이터가 자동 생성됨)
4. `.dockerignore`에 `.env`를 넣어 이미지 안에 들어가지 않게 한다

## 3. 예시 (`docker-compose.yml`)

```yaml
services:
  database:
    image: mariadb:10.11.19@sha256:...   # 실제 값은 docker-compose.yml 참고 (태그 + digest 고정)
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD}
      MARIADB_DATABASE: ${MARIADB_DATABASE}
      MARIADB_USER: ${MARIADB_USER}
      MARIADB_PASSWORD: ${MARIADB_PASSWORD}

  backend:
    environment:
      DB_HOST: database                      # 컨테이너 주소는 직접 지정
      DB_PORT: 3306
      MARIADB_DATABASE: ${MARIADB_DATABASE}
      MARIADB_USER: ${MARIADB_USER}
      MARIADB_PASSWORD: ${MARIADB_PASSWORD}
      JWT_SECRET: ${JWT_SECRET}
      JWT_ACCESS_EXPIRATION: ${JWT_ACCESS_EXPIRATION}
      JWT_REFRESH_EXPIRATION: ${JWT_REFRESH_EXPIRATION}
      CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS}
      ACTUATOR_EXPOSURE: ${ACTUATOR_EXPOSURE}
      ADMIN_EMAIL: ${ADMIN_EMAIL}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      AI_SERVICE_URL: http://ai-service:8000 # 컨테이너 주소는 직접 지정
      AI_INTERNAL_TOKEN: ${AI_INTERNAL_TOKEN}
      # LLM · 임베딩 설정, API 키는 넘기지 않음

  ai-service:
    environment:
      AI_INTERNAL_TOKEN: ${AI_INTERNAL_TOKEN}
      LLM_PROVIDER: ${LLM_PROVIDER}
      LLM_MODEL: ${LLM_MODEL}
      EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER}
      EMBEDDING_MODEL: ${EMBEDDING_MODEL}
      GROQ_API_KEY: ${GROQ_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      # DB · JWT · 관리자 값은 넘기지 않음

  frontend:
    # 비밀 값 없음 (환경 변수 불필요)
```

> image · build · ports · networks · healthcheck · depends_on 등 나머지 설정은 기존 계획대로 작성한다

## 4. 서비스별로 받는 값

| 서비스 | 받는 값 | 받지 않는 값 |
|------|------|------|
| database | DB 계정 4개 (`MARIADB_*`) | 그 외 전부 |
| backend | DB 계정, JWT, CORS, Actuator, 관리자 계정, AI 주소 · 내부 토큰 | LLM · 임베딩 설정, API 키 |
| ai-service | 내부 토큰, LLM · 임베딩 설정, API 키 | DB, JWT, 관리자 계정 |
| frontend | 없음 | 전부 |

## 5. 배포용 (`docker-compose.prod.yml`)

- `environment:`는 위와 똑같이 쓰고, `build` 대신 Docker Hub 이미지만 사용한다
- EC2에서는 `.env`를 compose 파일과 같은 폴더에 두고 권한을 제한한다

```bash
chmod 600 .env
```

- 배포 서버 `.env`의 `JWT_SECRET` · `AI_INTERNAL_TOKEN` · `ADMIN_PASSWORD`는 **로컬과 다른 새 값**을 쓴다
- (선택) 시연 때 로그인 잠금 시간을 줄이려면 backend에 추가한다

```yaml
      LOGIN_LOCK_MINUTES: ${LOGIN_LOCK_MINUTES:-15}
```

## 6. 확인 방법 (보안점검서 캡처용)

```bash
# 변수가 제대로 채워졌는지 확인 (출력에 비밀 값이 그대로 보이므로 캡처하지 않는다)
docker compose config

# Backend 컨테이너에 LLM 키가 없는지 → 아무것도 안 나오면 정상
docker compose exec backend env | grep -E "OPENAI|GROQ"

# AI 컨테이너에 DB · JWT · 관리자 값이 없는지 → 아무것도 안 나오면 정상
docker compose exec ai-service env | grep -E "JWT|MARIADB|ADMIN"
```

- 마지막 두 명령의 "결과 없음" 화면을 캡처해 두면 **컨테이너별 최소 권한 환경 변수 전달**의 근거로 쓸 수 있다
- 반영 후 `2.시스템아키텍처설계서.md` 6.4(비밀정보 관리)에 "파일은 하나, 컨테이너에는 필요한 변수만 전달" 내용을 추가한다
