#!/usr/bin/env bash
# RAG 소유자 우회 - 실제 AI 재확인 (보안점검서 6.3) + 거절 답변 출처 미저장 확인
# docker compose up -d 로 전체 기동 후, 저장소 최상위에서: bash backend/scripts/rag-real-check.sh
#  - A: 정보보안학01.pdf 업로드 / B: 3_ReactJS.pdf 업로드
#  - B 토큰 + body 에 A 의 ownerUuid · documentIds 를 넣어 A 자료 내용을 질문
#  - 조치됨: B 결과의 출처에 정보보안학01.pdf 가 없고, 카이사르 암호 설명이 나오지 않음
# 토큰 값은 출력하지 않음
B=${BASE_URL:-http://127.0.0.1}
J="Content-Type: application/json"
PW='Test1234!'
PDFS="$(cd "$(dirname "$0")/../../mock-data/pdfs" && pwd)"
PY=$(command -v python || command -v python3 || command -v py)
TMP=$(mktemp -d)

field() { sed -E "s/.*\"$1\":\"?([^\",}]+)\"?.*/\1/" <<<"$2"; }
account() { # 이메일 → 로그인 응답
  curl -s -o /dev/null -X POST $B/api/auth/signup -H "$J" -d "{\"email\":\"$1\",\"password\":\"$PW\"}"
  curl -s -X POST $B/api/auth/login -H "$J" -d "{\"email\":\"$1\",\"password\":\"$PW\"}"
}
upload() { # 토큰 파일명 → 업로드 응답
  # Windows curl 은 -F 한글 파일명을 CP949 로 보내 이름이 깨짐 → Python 으로 UTF-8 multipart 전송
  "$PY" - "$B/api/documents" "$1" "$(cygpath -w "$PDFS/$2" 2>/dev/null || echo "$PDFS/$2")" <<'PYEOF'
import os, sys, uuid, urllib.request, urllib.error
sys.stdout.reconfigure(encoding='utf-8')
url, token, path = sys.argv[1:4]
name = os.path.basename(path)
bd = uuid.uuid4().hex
body = (f'--{bd}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
        'Content-Type: application/pdf\r\n\r\n').encode('utf-8') + open(path, 'rb').read() + f'\r\n--{bd}--\r\n'.encode()
req = urllib.request.Request(url, data=body, method='POST', headers={
    'Authorization': 'Bearer ' + token, 'Content-Type': 'multipart/form-data; boundary=' + bd})
try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 시스템 프록시 무시 (로컬 호출)
    print(opener.open(req, timeout=180).read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(e.read().decode('utf-8', 'replace'))
PYEOF
}
ask() { # 토큰 JSON본문 → 출처 · 답변 요약 (한글 JSON 은 UTF-8 파일로 전송)
  printf '%s' "$2" > "$TMP/q.json"
  (cd "$TMP" && curl -N -s -m 90 -X POST $B/api/chats/stream -H "$J" -H "Authorization: Bearer $1" --data-binary @q.json) \
    | "$PY" -c "
import json,sys
sys.stdout.reconfigure(encoding='utf-8')  # Windows 콘솔 한글 파일명 깨짐 방지
ev=None; src=[]; ans=''
for raw in sys.stdin.buffer:
    line=raw.decode('utf-8').rstrip('\r\n')
    if line.startswith('event:'): ev=line[6:].strip()
    elif line.startswith('data:'):
        try: d=json.loads(line[5:])
        except ValueError: d={'code':line[5:].strip()}
        if ev=='sources': src=sorted({s['documentName'] for s in d})
        elif ev=='token': ans+=d.get('text','')
        elif ev=='error': ans+='[error '+str(d.get('code', d) if isinstance(d,dict) else d)+']'
print('   출처:', ', '.join(src) or '(없음)')
print('   답변:', ans[:120].replace(chr(10),' '))"
}

S=$RANDOM
AL=$(account "rag-a$S@test.com"); AT=$(field accessToken "$AL"); A_UUID=$(field uuid "$AL")
BL=$(account "rag-b$S@test.com"); BT=$(field accessToken "$BL")
case "$AT$BT" in *'<'*|*' '*|'') echo "로그인 실패 (Backend 가 아직 기동 중이거나 꺼져 있음) → docker compose ps 로 backend 가 healthy 인지 확인 후 다시 실행"; exit 1;; esac

echo "== 업로드 (실제 적재라 수십 초 걸릴 수 있음)"
AD=$(upload "$AT" 정보보안학01.pdf); A_DOC=$(field id "$AD")
echo "   A 정보보안학01.pdf → id=$A_DOC status=$(field status "$AD")"
BD=$(upload "$BT" 3_ReactJS.pdf)
echo "   B 3_ReactJS.pdf    → id=$(field id "$BD") status=$(field status "$BD")"

Q='카이사르 암호는 어떤 방식이야?'
echo "== 1. A 본인 질문 (대조군: A 자료에서 답이 나와야 함)"
ask "$AT" "{\"question\":\"$Q\"}"

echo "== 2. B 토큰 + body 에 A 의 ownerUuid · documentIds 조작"
ask "$BT" "{\"question\":\"$Q\",\"ownerUuid\":\"$A_UUID\",\"documentIds\":[$A_DOC]}"
echo "   → 출처에 정보보안학01.pdf 가 없고 카이사르 설명이 없으면 조치됨 (B 는 자기 자료로만 검색)"

echo "== 3. 거절 답변 기록의 출처 (B 의 최신 질문 기록)"
curl -s "$B/api/chats?page=0&size=1" -H "Authorization: Bearer $BT" | "$PY" -c "
import json,sys
sys.stdout.reconfigure(encoding='utf-8')
c=json.load(sys.stdin.buffer)['data']['content'][0]
print('   답변:', c['answer'][:40]); print('   저장된 출처:', c['sources'])"
echo "   → 저장된 출처가 [] 이면 정상 (거절 답변에는 관련 없는 출처를 기록하지 않음)"
rm -rf "$TMP"
