# 8.45 MiB PDF 적재 시간 측정

2026-11-08 23:41 KST, 커밋 `6dd45ef`의 로컬 Compose에서 측정했다. 문서가 없는 전용 계정으로 Backend의 `POST /api/documents`에 PDF를 한 번 업로드했다. 이번 환경의 첫 실제 적재였으며 임베딩 모델은 OpenAI `text-embedding-3-small`이었다.

| 측정 항목 | 결과 |
|---|---|
| 입력 파일 | `pkpadmin,+1091-5090-1-CE.pdf`, 8,859,093바이트, 38페이지 |
| 파일 SHA-256 | `eb175d20214833f5334c1c5204cc0c4a1277cef0854293c44ce1abff1b819ec3` |
| 클라이언트 전체 시간 | 5.315초. 로컬 Backend 직접 업로드 호출 시작부터 HTTP 201 응답 수신까지 Stopwatch로 측정 |
| Backend → AI | 5.057초. Backend 로그의 내부 POST 시작 23:41:31.823부터 응답 본문 수신 완료(`response_completed`) 23:41:36.880까지. AI는 HTTP 200 반환 |
| MariaDB 조회 | 문서 ID 1, 파일 크기 8,859,093바이트, 상태 `READY` |
| Chroma 조회 | DB에서 확인한 소유자 UUID와 문서 ID 1로 조회. 고유 청크 267개, 페이지 37개 |

이 요청은 Backend → AI 120초 이내 응답과 DB의 `READY` 조건을 모두 충족했다. 앞선 별도 로컬 전처리에서도 37페이지에서 267개 청크가 생성됐다. 이번 값은 이 PDF의 첫 요청 1회 측정값이며 최대 지연이나 정확한 10 MiB 경계 동작을 측정한 값은 아니다.
