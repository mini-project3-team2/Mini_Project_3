#!/usr/bin/env bash
# 파일 업로드 검증 점검 (보안점검서 B-10) — Backend + 가짜 AI 서버 실행 후, 저장소 최상위에서: bash backend/scripts/upload-check.sh
# 확장자만 바꾼 파일 · 빈 파일 · PDF 가 아닌 확장자 · 10MB 초과 · 경로가 들어간 파일명
# 상태 코드 · 오류 코드만 출력 (토큰 값은 출력하지 않음)
B=${BASE_URL:-http://localhost:8080}
J="Content-Type: application/json"
TMP=$(mktemp -d)

printf '%%PDF-1.4\n%% test pdf\n' > "$TMP/real.pdf"
printf 'MZ this is not a pdf (exe renamed)\n' > "$TMP/fake.pdf"
: > "$TMP/empty.pdf"
printf '%%PDF-1.4\n%% pdf content but txt name\n' > "$TMP/note.txt"
{ printf '%%PDF-1.4\n'; head -c $((10 * 1024 * 1024 + 1024)) /dev/zero; } > "$TMP/big.pdf"

check() {
  local code body got
  code=$(tail -n1 <<<"$3"); body=$(sed '$d' <<<"$3")
  got=$(grep -o '"code":"[A-Z_]*"' <<<"$body" | cut -d'"' -f4)
  [ "$code" = "$2" ] && r=OK || r=FAIL
  printf '%-4s %-44s 기대 %s / 실제 %s %s\n' "$r" "$1" "$2" "$code" "$got"
}
up() { # 파일명 [업로드할 때 보낼 이름]
  (cd "$TMP" && curl -s -w '\n%{http_code}' -X POST $B/api/documents -H "Authorization: Bearer $ST" -F "file=@$1;filename=${2:-$1}")
}

ST=$(curl -s -X POST $B/api/auth/login -H "$J" -d '{"email":"student@test.com","password":"Test1234!"}' \
  | sed -E 's/.*"accessToken":"([^"]+)".*/\1/')

echo "[$(date '+%F %T')] 파일 업로드 검증 점검"
check "정상 PDF"                                    201 "$(up real.pdf)"
check "확장자만 .pdf 인 가짜 파일 (내용이 PDF 아님)" 400 "$(up fake.pdf)"
check "빈 파일 (0바이트)"                           400 "$(up empty.pdf)"
check "내용은 PDF · 확장자 .txt"                    400 "$(up note.txt)"
check "10MB 초과 (10MB + 1KB)"                      413 "$(up big.pdf)"
R=$(up real.pdf "../../etc/passwd.pdf")
check "경로가 들어간 파일명 (../../etc/passwd.pdf)"  201 "$R"
echo "     저장된 파일명: $(sed '$d' <<<"$R" | grep -o '"originalFilename":"[^"]*"' | cut -d'"' -f4)  (경로 문자 제거 → passwd.pdf)"
rm -rf "$TMP"
