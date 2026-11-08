#!/usr/bin/env bash
# 답변 피드백 · IDOR 점검 (보안점검서 B-2 · 6.4)
# Backend 를 local 프로필로 실행 (테스트 계정 · 기록 자동 생성) 후, 저장소 최상위에서: bash backend/scripts/feedback-check.sh
#  - 조치 전: "남의 기록 피드백" 이 200 이고, other 의 기록 값이 바뀜 → IDOR
#  - 조치 후: 403 FORBIDDEN 이고, other 의 기록 값이 그대로
# 상태 코드 · 오류 코드만 출력 (토큰 값은 출력하지 않음)
B=${BASE_URL:-http://localhost:8080}
J="Content-Type: application/json"
PY=$(command -v python || command -v python3 || command -v py)

check() { # 이름 기대값 응답(본문\n코드)
  local code body got
  code=$(tail -n1 <<<"$3"); body=$(sed '$d' <<<"$3")
  got=$(grep -o '"code":"[A-Z_]*"' <<<"$body" | cut -d'"' -f4)
  [ "$code" = "$2" ] && r=OK || r=FAIL
  printf '%-4s %-42s 기대 %s / 실제 %s %s\n' "$r" "$1" "$2" "$code" "$got"
}
token() {
  curl -s -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$1\",\"password\":\"Test1234!\"}" \
    | sed -E 's/.*"accessToken":"([^"]+)".*/\1/'
}
first_id() { # 기록 목록에서 첫 번째 기록 id
  curl -s "$B/api/chats?page=0&size=1" -H "Authorization: Bearer $1" | grep -o '"id":[0-9]*' | head -n1 | cut -d: -f2
}
feedback_of() { # 기록 목록(size=50)에서 해당 id 의 feedback 값 (출처 객체가 섞여 있어 JSON 으로 해석)
  curl -s "$B/api/chats?size=50" -H "Authorization: Bearer $1" | "$PY" -c "
import json,sys
d=json.load(sys.stdin.buffer)['data']['content']  # Windows 에서도 UTF-8 로 읽기
print(next((str(c['feedback']) for c in d if c['id']==$2),'없음'))"
}
patch() { # 기록id 값 [토큰]
  if [ -n "$3" ]; then
    curl -s -w '\n%{http_code}' -X PATCH "$B/api/chats/$1/feedback" -H "$J" -H "Authorization: Bearer $3" -d "{\"feedback\":\"$2\"}"
  else
    curl -s -w '\n%{http_code}' -X PATCH "$B/api/chats/$1/feedback" -H "$J" -d "{\"feedback\":\"$2\"}"
  fi
}

ST=$(token student@test.com)
OT=$(token other@test.com)
MINE=$(first_id "$ST")
THEIRS=$(first_id "$OT")
echo "[$(date '+%F %T')] 피드백 점검 — student 기록 id=$MINE, other 기록 id=$THEIRS"
[ -z "$MINE" ] || [ -z "$THEIRS" ] && { echo "기록이 없습니다. Backend 를 local 프로필로 실행했는지 확인하세요"; exit 1; }

check "내 기록 피드백 HELPFUL"                200 "$(patch "$MINE" HELPFUL "$ST")"
check "내 기록 피드백 NOT_HELPFUL 로 변경"    200 "$(patch "$MINE" NOT_HELPFUL "$ST")"
check "같은 값 다시 보내기 (멱등)"            200 "$(patch "$MINE" NOT_HELPFUL "$ST")"
check "잘못된 값 (GOOD)"                      400 "$(patch "$MINE" GOOD "$ST")"
check "없는 기록"                             404 "$(patch 999999 HELPFUL "$ST")"
check "토큰 없이"                             401 "$(patch "$MINE" HELPFUL)"

BEFORE=$(feedback_of "$OT" "$THEIRS")
# 지금 값과 반대 값을 보내야 바뀌었는지 보인다 (몇 번을 실행해도 같은 방식으로 확인)
[ "$BEFORE" = "NOT_HELPFUL" ] && ATTACK=HELPFUL || ATTACK=NOT_HELPFUL
check "남의 기록 피드백 (student → other)"    403 "$(patch "$THEIRS" "$ATTACK" "$ST")"
AFTER=$(feedback_of "$OT" "$THEIRS")
[ "$BEFORE" = "$AFTER" ] && r=OK || r=FAIL
printf '%-4s %-42s 시도 전 %s / 시도 후 %s\n' "$r" "other 기록 값이 그대로인지" "${BEFORE:-null}" "${AFTER:-null}"
