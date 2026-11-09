#!/usr/bin/env bash
# Brute Force 점검 (Backend 실행 후, 저장소 최상위에서: bash backend/scripts/bruteforce-check.sh)
# 틀린 비밀번호로 연속 로그인 → 마지막에 올바른 비밀번호로 로그인
# 조치 전: 모두 401 이고 마지막 로그인 200 (무제한 시도 가능 = 취약)
# 조치 후: 5회 실패 뒤 423 ACCOUNT_LOCKED, 올바른 비밀번호도 423 (잠금 중)
B=${BASE_URL:-http://localhost:8080}
EMAIL=${TEST_EMAIL:-brute@test.com}
PW=${TEST_PASSWORD:-Test1234!}
TRIES=${TRIES:-10}
J="Content-Type: application/json"

curl -s -o /dev/null -X POST $B/api/auth/signup -H "$J" -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}"

login() {
  local res code body
  res=$(curl -s -w '\n%{http_code}' -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$EMAIL\",\"password\":\"$1\"}")
  code=$(tail -n1 <<<"$res"); body=$(sed '$d' <<<"$res")
  printf '%-14s %-12s -> %s %s\n' "$2" "$3" "$code" "$(grep -o '"code":"[A-Z_]*"' <<<"$body" | cut -d'"' -f4)"
}

echo "[$(date '+%F %T')] 대상 $EMAIL, 틀린 비밀번호 ${TRIES}회 후 올바른 비밀번호"
for i in $(seq 1 "$TRIES"); do
  login "Wrong${i}234!" "시도 $i" "틀린 비밀번호"
done
login "$PW" "마지막" "올바른 비밀번호"
