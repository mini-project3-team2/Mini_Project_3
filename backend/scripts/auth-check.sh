#!/usr/bin/env bash
# 인증 · 인가 점검 (Backend 실행 후, 저장소 최상위에서: bash backend/scripts/auth-check.sh)
# 상태 코드와 오류 코드만 출력한다 (토큰 값은 출력하지 않음)
B=${BASE_URL:-http://localhost:8080}
EMAIL=${TEST_EMAIL:-newuser@test.com}
PW=${TEST_PASSWORD:-Test1234!}
ADMIN_EMAIL=$(grep '^ADMIN_EMAIL=' .env | cut -d= -f2- | tr -d '\r')
ADMIN_PW=$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2- | tr -d '\r')
J="Content-Type: application/json"

check() { # 이름 기대값 실제응답(본문\n코드)
  local body code got
  code=$(tail -n1 <<<"$3"); body=$(sed '$d' <<<"$3")
  got=$(grep -o '"code":"[A-Z_]*"' <<<"$body" | cut -d'"' -f4)
  [ "$code" = "$2" ] && r=OK || r=FAIL
  printf '%-4s %-42s 기대 %s / 실제 %s %s\n' "$r" "$1" "$2" "$code" "$got"
}
req() { curl -s -w '\n%{http_code}' "$@"; }
field() { sed -E "s/.*\"$1\":\"([^\"]+)\".*/\1/" <<<"$2"; }

req -X POST $B/api/auth/signup -H "$J" -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}" >/dev/null

check "health 공개"                    200 "$(req $B/actuator/health)"
check "토큰 없이 인증 API"             401 "$(req $B/api/chats)"
check "위조 토큰"                      401 "$(req $B/api/chats -H 'Authorization: Bearer abc.def.ghi')"

LOGIN=$(curl -s -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}")
AT=$(field accessToken "$LOGIN"); RT=$(field refreshToken "$LOGIN")
check "유효 토큰 (없는 주소 → 404)"     404 "$(req $B/api/not-exist -H "Authorization: Bearer $AT")"
check "MEMBER 가 /actuator/info"        403 "$(req $B/actuator/info -H "Authorization: Bearer $AT")"

R1=$(req -X POST $B/api/auth/refresh -H "$J" -d "{\"refreshToken\":\"$RT\"}")
check "재발급"                         200 "$R1"
RT2=$(field refreshToken "$(sed '$d' <<<"$R1")")
check "이미 쓴 Refresh 재사용"          401 "$(req -X POST $B/api/auth/refresh -H "$J" -d "{\"refreshToken\":\"$RT\"}")"

check "로그아웃 (토큰 없이)"            401 "$(req -X POST $B/api/auth/logout -H "$J" -d "{\"refreshToken\":\"$RT2\"}")"
check "로그아웃"                       204 "$(req -X POST $B/api/auth/logout -H "$J" -H "Authorization: Bearer $AT" -d "{\"refreshToken\":\"$RT2\"}")"
check "로그아웃한 Refresh 로 재발급"     401 "$(req -X POST $B/api/auth/refresh -H "$J" -d "{\"refreshToken\":\"$RT2\"}")"

if [ -n "$ADMIN_EMAIL" ]; then
  AL=$(curl -s -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PW\"}")
  check "ADMIN 이 /actuator/info"       200 "$(req $B/actuator/info -H "Authorization: Bearer $(field accessToken "$AL")")"
fi
