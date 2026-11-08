#!/usr/bin/env bash
# SQL Injection 점검 (보안점검서 B-1) — Backend + 가짜 AI 서버 실행 후, 저장소 최상위에서: bash backend/scripts/sqli-check.sh
# 로그인 · 회원가입 · 경로 변수 · 질문에 SQL 조작 문자열을 넣어 본다
# 기대: 인증 우회 없음(401) · 형식 검증(400) · 500 오류 없음 · 이후 정상 로그인 가능(테이블 무사)
# 상태 코드 · 오류 코드만 출력 (토큰 값은 출력하지 않음)
B=${BASE_URL:-http://localhost:8080}
J="Content-Type: application/json"
TMP=$(mktemp -d)

check() { # 이름 기대값 응답(본문\n코드)
  local code body got
  code=$(tail -n1 <<<"$3"); body=$(sed '$d' <<<"$3")
  got=$(grep -o '"code":"[A-Z_]*"' <<<"$body" | cut -d'"' -f4)
  [ "$code" = "$2" ] && r=OK || r=FAIL
  printf '%-4s %-46s 기대 %s / 실제 %s %s\n' "$r" "$1" "$2" "$code" "$got"
}
# 조작 문자열의 따옴표가 셸에서 깨지지 않도록 JSON 을 파일로 저장해 전송
post() { # 경로 JSON [토큰]
  printf '%s' "$2" > "$TMP/body.json"
  if [ -n "$3" ]; then
    (cd "$TMP" && curl -s -w '\n%{http_code}' -X POST "$B$1" -H "$J" -H "Authorization: Bearer $3" --data-binary @body.json)
  else
    (cd "$TMP" && curl -s -w '\n%{http_code}' -X POST "$B$1" -H "$J" --data-binary @body.json)
  fi
}

echo "[$(date '+%F %T')] SQL Injection 점검"
check "로그인 이메일 · 비밀번호에 ' OR '1'='1"        401 "$(post /api/auth/login '{"email":"'"'"' OR '"'"'1'"'"'='"'"'1","password":"'"'"' OR '"'"'1'"'"'='"'"'1"}')"
check "로그인 이메일 뒤 주석 처리 (student@test.com' --)" 401 "$(post /api/auth/login '{"email":"student@test.com'"'"' -- ","password":"anything"}')"
check "로그인 UNION SELECT"                             401 "$(post /api/auth/login '{"email":"x'"'"' UNION SELECT * FROM members -- ","password":"x"}')"
check "회원가입 이메일에 ' OR '1'='1"                   400 "$(post /api/auth/signup '{"email":"x'"'"' OR '"'"'1'"'"'='"'"'1@test.com","password":"Test1234!"}')"

ST=$(post /api/auth/login '{"email":"student@test.com","password":"Test1234!"}' | sed '$d' | sed -E 's/.*"accessToken":"([^"]+)".*/\1/')
check "자료 삭제 경로에 1 OR 1=1"                        400 "$(curl -s -w '\n%{http_code}' -X DELETE "$B/api/documents/1%20OR%201=1" -H "Authorization: Bearer $ST")"
check "기록 목록 page 파라미터에 1;DROP TABLE"           400 "$(curl -s -w '\n%{http_code}' "$B/api/chats?page=1%3BDROP%20TABLE%20members" -H "Authorization: Bearer $ST")"

printf '%s' '{"question":"'"'"'; DROP TABLE members; -- 테이블 삭제 시도"}' > "$TMP/q.json"
Q=$(cd "$TMP" && curl -N -s -o "$TMP/stream.txt" -w '%{http_code}' -X POST "$B/api/chats/stream" -H "$J" -H "Authorization: Bearer $ST" --data-binary @q.json)
grep -q "event:done" "$TMP/stream.txt" && D="done 수신 (질문은 문자열로 저장)" || D="done 없음"
[ "$Q" = "200" ] && r=OK || r=FAIL
printf '%-4s %-46s 기대 200 / 실제 %s %s\n' "$r" "질문에 '; DROP TABLE members; --" "$Q" "$D"

check "조작 시도 후 정상 로그인 (members 테이블 무사)"   200 "$(post /api/auth/login '{"email":"student@test.com","password":"Test1234!"}')"
rm -rf "$TMP"
