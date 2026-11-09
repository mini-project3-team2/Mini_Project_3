# =========================================================
#  Frontend (React · Vite) - 멀티스테이지 · 비root · HEALTHCHECK
#  빌드: node:24.22.2-alpine3.24 (.nvmrc)  →  실행: nginxinc/nginx-unprivileged:1.31.7-alpine3.24 (uid 101, 포트 8080)
#  베이스 이미지는 패치 버전 태그 + digest 로 고정 (보안점검서 I-4)
# =========================================================

# ---------- 1) 빌드 단계: Node ----------
# 베이스 이미지는 패치 버전 태그 + digest 로 고정 (보안점검서 I-4). 갱신 시 태그 · digest 를 함께 바꾸고 Trivy 재검사
FROM node:24.22.2-alpine3.24@sha256:a34ab6d7f6f4813f4d0c5469d74685604b962fbdbf5793a7bc7b4998ecb867c8 AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# VITE_* 는 빌드 시점에 번들에 박제됨 → 비밀값 절대 금지, 경로만 전달
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---------- 2) 실행 단계: 비root Nginx (uid 101) - 보안점검서 I-2 ----------
FROM nginxinc/nginx-unprivileged:1.31.7-alpine3.24@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
