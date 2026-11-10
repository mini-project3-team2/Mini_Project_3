# 최종 배포 보안 재점검

2026-11-10 KST. 팀이 제공한 운영 EC2의 HTTP 엔드포인트, GitHub main, Docker Hub의 linux/amd64 이미지, 로컬 격리 환경을 확인했다.

## 릴리스 식별

- main은 PR #113 병합 커밋 `641113f229a56993ecb7bf9dcfefb81498255049`다. 이전 로컬 검토 대상 `e70821b`와 Git 트리 해시가 `4a382ffa36cc34fb8aa1a0e3b80246138f833007`로 일치한다. 이후 develop의 #114는 Frontend 명세서 변경이다.
- 해당 SHA의 [Secret Scan](https://github.com/mini-project3-team2/Mini_Project_3/actions/runs/42763094740)과 [Docker Build & Push](https://github.com/mini-project3-team2/Mini_Project_3/actions/runs/42763094587)는 성공했다.
- 운영 HTML이 참조한 `/assets/index-miiqsVg5.js`의 SHA-256은 `3df1f3bddd092a048c8b5b9619375511da2eb4c90a65a38bb83852c6fa632a78`로, 최종 태그 Frontend 이미지에서 추출한 파일과 동일하다. EC2에서 실행 중인 Backend·AI의 실제 digest와 LLM 모델 설정은 서버 내부 대조가 필요하다.

## 운영 EC2 외부 실측

| 시험 | 관찰 |
|---|---|
| 웹·보호 경로 | GET / 200, /.env 및 /actuator/health 404, 무인증 /api/documents 및 /api/chats 401. 다섯 응답 모두 CSP, nosniff, X-Frame-Options DENY 포함 |
| 외부 포트 | HTTP 80 응답. 이 클라이언트에서 TCP 443·3306·8000·8080 연결 불가. 로그인과 토큰 전송 경로에 TLS가 없는 상태 |
| 인증 요청 제한 | 실제 계정 정보 없이 빈 JSON으로 순차 요청. 16번째 요청에 429 TOO_MANY_REQUESTS를 확인하고 중지 |
| 자료 접근 제어 | 독립된 A·B 계정이 각각 합성 PDF를 올려 READY 확인. B 토큰으로 A 자료 삭제 시 매회 403 |
| 실제 RAG 양성 대조 | A 자료에 관측치 347개를 명시. A 질문에 347을 답했고 자신의 PDF가 출처에 포함됐다. SSE done과 저장된 답변·출처 1개를 확인 |
| 실제 RAG 소유자 조작 | B 토큰으로 A의 ownerUuid 및 documentIds를 넣어 같은 질문을 전송. A의 숫자·출처가 나오지 않았고, 거절 답변의 저장 출처는 0개 |
| 응답 품질 관찰 | 앞선 두 번의 검증 코드 문구 질문에서는 A의 출처가 내려왔지만 기대한 영문 또는 숫자 표식이 답변에 없었다. 두 번째는 관련 자료가 없다는 응답이었다. 위의 일반 수업 질문으로 양성 대조를 별도로 확보했다. 이 결과만으로 거절 원인이나 빈도는 특정할 수 없다. |

운영에 테스트 계정 6개를 만들었다. 합성 PDF 6개의 삭제와 각 세션의 로그아웃은 모두 204였다. 테스트 계정과 질의 이력은 운영 DB에 남을 수 있다. 실제 사용자 자료와 토큰 값은 증적에 포함하지 않았다.

## 동일 배포 이미지에서 재현한 기존 발견

운영 Compose를 별도 프로젝트와 루프백 포트, 임시 자격증명으로 기동했다. 레지스트리 최종 태그의 3개 앱과 DB가 모두 healthy 상태였다. 아래 장애·오류 유발 시험은 로컬에서 수행했다.

| 조건 | 관찰 |
|---|---|
| 동일 로그인에 X-Forwarded-For 추가 | 두 요청 모두 401. 감사 IP가 게이트웨이에서 클라이언트 지정값 198.51.100.77로 변경됨 |
| 가입 비밀번호 20자·UTF-8 74바이트 | HTTP 500 재현 |
| 운영 Compose의 IMAGE_TAG 빈 값 | config --images가 세 앱 모두 latest로 해석 |
| Backend 단독 재생성 시 이전 IP를 다른 임시 컨테이너가 점유 | 새 Backend가 healthy인데도 Nginx 경유 보호 API가 502. Frontend 재시작 후 정상 무인증 응답 401로 복구 |

## 서버 내부에서 남은 확인

운영 담당자가 실행 컨테이너 digest, 4개 서비스 health, IMAGE_TAG와 LLM 공급자·모델, .env 권한, 감사 로그의 IP·비밀 값 출력, SSH 키 전용 인증, IMDSv2, OS 패치를 확인해야 한다. 외부 포트 시험은 보안그룹 규칙 전체에 대한 검증을 대신할 수 없다. 공급자 키 권한·비용 한도는 공급자 콘솔에서 확인해야 한다.

## 최종 이미지 취약점 재검사

Trivy 0.58.1이 보고한 linux/amd64 패키지별 탐지 건수다. 이전 태그와 등급·취약점 ID·패키지·설치 버전을 비교했다.

| 최종 이미지 및 스캔 원본 | HIGH | CRITICAL | 이전 결과 대비 추가·제거 행 |
|---|---:|---:|---:|
| [frontend](trivy-frontend-sha-641113f.json) | 9 | 1 | 0 |
| [backend](trivy-backend-sha-641113f.json) | 2 | 0 | 0 |
| [ai](trivy-ai-sha-641113f.json) | 51 | 2 | 0 |
