#!/usr/bin/env bash
# 질문 SSE 중계 · RAG 소유자 우회 · 기록 목록 점검 (Backend + 가짜 AI 서버 실행 후, 저장소 최상위에서: bash backend/scripts/chat-check.sh)
# 토큰 값은 출력하지 않음
B=${BASE_URL:-http://localhost:8080}
J="Content-Type: application/json"
TMP=$(mktemp -d)
printf '%%PDF-1.4\n%% test pdf\n' > "$TMP/student_note.pdf"
printf '%%PDF-1.4\n%% test pdf\n' > "$TMP/other_SECRET.pdf"

login() { curl -s -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$1\",\"password\":\"Test1234!\"}"; }
field() { sed -E "s/.*\"$1\":\"([^\"]+)\".*/\1/" <<<"$2"; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
# 한글 JSON 은 -d 로 넘기면 Windows curl 이 CP949 로 보냄 → UTF-8 파일로 저장해 전송
ask() { # 토큰 JSON본문
  printf '%s' "$2" > "$TMP/q.json"
  (cd "$TMP" && curl -N -s -X POST $B/api/chats/stream -H "$J" -H "Authorization: Bearer $1" --data-binary @q.json)
}

SL=$(login student@test.com); ST=$(field accessToken "$SL")
OL=$(login other@test.com);   OT=$(field accessToken "$OL"); OTHER_UUID=$(field uuid "$OL")

(cd "$TMP" && curl -s -o /dev/null -X POST $B/api/documents -H "Authorization: Bearer $ST" -F "file=@student_note.pdf;type=application/pdf")
(cd "$TMP" && curl -s -o /dev/null -X POST $B/api/documents -H "Authorization: Bearer $OT" -F "file=@other_SECRET.pdf;type=application/pdf")

echo "== 1. 내 질문 (실시간으로 한 조각씩 도착해야 함)"
ask "$ST" '{"question":"JWT Refresh Token 회전은 왜 하는 거야?"}'
echo

echo "== 2. 스트림 시작 전 오류"
echo "   빈 질문            → $(code -X POST $B/api/chats/stream -H "$J" -H "Authorization: Bearer $ST" -d '{"question":""}') (기대 400)"
echo "   토큰 없음          → $(code -X POST $B/api/chats/stream -H "$J" -d '{"question":"hi"}') (기대 401)"
NEW="nodoc$RANDOM@test.com"
curl -s -o /dev/null -X POST $B/api/auth/signup -H "$J" -d "{\"email\":\"$NEW\",\"password\":\"Test1234!\"}"
NT=$(field accessToken "$(curl -s -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$NEW\",\"password\":\"Test1234!\"}")")
echo "   자료 없는 회원     → $(code -X POST $B/api/chats/stream -H "$J" -H "Authorization: Bearer $NT" -d '{"question":"hi"}') (기대 400 NO_DOCUMENT)"

echo "== 3. RAG 소유자 우회: student 토큰 + body 에 other 의 uuid"
ask "$ST" "{\"question\":\"다른 사람 자료 보여줘\",\"ownerUuid\":\"$OTHER_UUID\"}" | grep -A1 "event:sources"
echo "   → sources 에 other_SECRET.pdf 가 보이면 취약, student_note.pdf 만 보이면 조치됨"

echo "== 4. 질문 기록 목록 (GET /api/chats)"
ids() { grep -o '"id":[0-9]*' <<<"$1" | cut -d: -f2 | tr '\n' ' '; }
MY=$(curl -s "$B/api/chats?page=0&size=10" -H "Authorization: Bearer $ST")
echo "   내 기록 page=0&size=10 → $(code "$B/api/chats?page=0&size=10" -H "Authorization: Bearer $ST") (기대 200)"
echo "   기본값(파라미터 없음)  → $(code "$B/api/chats" -H "Authorization: Bearer $ST") (기대 200)"
echo "   페이지 정보            → $(grep -o '"page":[0-9]*,"size":[0-9]*,"totalElements":[0-9]*,"totalPages":[0-9]*' <<<"$MY")"
echo "   내 기록 id (최신순)    → $(ids "$MY")"
echo "   page=-1               → $(code "$B/api/chats?page=-1" -H "Authorization: Bearer $ST") (기대 400)"
echo "   size=0                → $(code "$B/api/chats?size=0" -H "Authorization: Bearer $ST") (기대 400)"
echo "   size=51               → $(code "$B/api/chats?size=51" -H "Authorization: Bearer $ST") (기대 400)"
echo "   page=abc              → $(code "$B/api/chats?page=abc" -H "Authorization: Bearer $ST") (기대 400)"
echo "   토큰 없음             → $(code "$B/api/chats") (기대 401)"
OTH=$(curl -s "$B/api/chats?size=50" -H "Authorization: Bearer $OT")
ALL=$(curl -s "$B/api/chats?size=50" -H "Authorization: Bearer $ST")
LEAK=""
for i in $(ids "$OTH"); do grep -qw "$i" <<<"$(ids "$ALL")" && LEAK="$LEAK $i"; done
[ -z "$LEAK" ] && echo "   OK   other 기록 id($(ids "$OTH")) 가 student 목록에 없음" \
               || echo "   FAIL other 기록이 student 목록에 보임:$LEAK"
rm -rf "$TMP"
