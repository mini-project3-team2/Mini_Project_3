#!/usr/bin/env bash
# 자료 업로드 · 삭제 점검 (Backend + 가짜 AI 서버 실행 후, 저장소 최상위에서: bash backend/scripts/document-check.sh)
# 상태 코드 · 오류 코드만 출력 (토큰 값은 출력하지 않음)
B=${BASE_URL:-http://localhost:8080}
AI=${AI_URL:-http://127.0.0.1:8000}
J="Content-Type: application/json"
TMP=$(mktemp -d)
printf '%%PDF-1.4\n%% test pdf\n' > "$TMP/sample.pdf"

check() {
  local code body got
  code=$(tail -n1 <<<"$3"); body=$(sed '$d' <<<"$3")
  got=$(grep -o '"code":"[A-Z_]*"' <<<"$body" | cut -d'"' -f4)
  [ "$code" = "$2" ] && r=OK || r=FAIL
  printf '%-4s %-40s 기대 %s / 실제 %s %s\n' "$r" "$1" "$2" "$code" "$got"
}
req() { curl -s -w '\n%{http_code}' "$@"; }
token() {
  curl -s -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$1\",\"password\":\"Test1234!\"}" \
    | sed -E 's/.*"accessToken":"([^"]+)".*/\1/'
}

ST=$(token student@test.com)
OT=$(token other@test.com)

# Windows curl 이 /tmp 경로를 못 찾으므로 임시 폴더로 이동해 상대 경로로 전송
UP=$(cd "$TMP" && req -X POST $B/api/documents -H "Authorization: Bearer $ST" -F "file=@sample.pdf;type=application/pdf")
check "업로드 (가짜 AI mode=ok 기준)" 201 "$UP"
ID=$(sed '$d' <<<"$UP" | grep -o '"id":[0-9]*' | cut -d: -f2)
echo "     업로드 응답 status: $(sed '$d' <<<"$UP" | grep -o '"status":"[A-Z]*"' | cut -d'"' -f4), id=$ID"
echo "     AI 적재 목록: $(curl -s $AI/debug/documents)"

check "토큰 없이 업로드"                401 "$(cd "$TMP" && req -X POST $B/api/documents -F "file=@sample.pdf")"
check "없는 자료 삭제"                  404 "$(req -X DELETE $B/api/documents/999999 -H "Authorization: Bearer $ST")"

if [ -n "$ID" ]; then
  check "남의 자료 삭제 (other → student)" 403 "$(req -X DELETE $B/api/documents/$ID -H "Authorization: Bearer $OT")"
  check "내 자료 삭제"                     204 "$(req -X DELETE $B/api/documents/$ID -H "Authorization: Bearer $ST")"
  echo "     AI 적재 목록: $(curl -s $AI/debug/documents)"
fi
rm -rf "$TMP"
