# =========================================================
#  Frontend (React · Vite) - 멀티스테이지 · 비root · HEALTHCHECK
#  빌드: node:24-alpine (.nvmrc)  →  실행: nginxinc/nginx-unprivileged (uid 101, 포트 8080)
#  ※ 배포 전 베이스 이미지 태그를 버전까지 고정 (보안점검서 I-4)
# =========================================================

# ---------- 1) 빌드 단계: Node ----------
FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# VITE_* 는 빌드 시점에 번들에 박제됨 → 비밀값 절대 금지, 경로만 전달
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---------- 2) 실행 단계: 비root Nginx (uid 101) - 보안점검서 I-2 ----------
FROM nginxinc/nginx-unprivileged:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
