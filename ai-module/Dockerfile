# =========================================================
#  AI Module (FastAPI · LangChain · Python 3.12) - 멀티스테이지 · 비root · HEALTHCHECK
#  빌드: uv 0.12.23 로 .venv 생성  →  실행: .venv + src 만 복사 (uv · 테스트 코드 미포함)
# =========================================================

# ---------- 1) 빌드 단계: uv 로 의존성 설치 ----------
# 베이스 이미지는 패치 버전 태그 + digest 로 고정 (보안점검서 I-4). 갱신 시 태그 · digest 를 함께 바꾸고 Trivy 재검사
FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# uv.lock 과 다르면 빌드 실패 (--locked), 개발 의존성 제외
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/ src/

# ---------- 2) 실행 단계 ----------
FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# 비root 사용자 + Chroma 볼륨 위치를 미리 만들고 소유자 지정 - 보안점검서 I-2
#  (Compose 의 chroma-data:/data/chroma 가 처음 생성될 때 이 소유권을 이어받음)
RUN groupadd --system app \
 && useradd --system --gid app --create-home --shell /usr/sbin/nologin app \
 && mkdir -p /data/chroma && chown app:app /data/chroma

WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src

USER app
EXPOSE 8000

# slim 이미지에는 curl 이 없으므로 표준 라이브러리로 확인 (Compose 와 동일)
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
