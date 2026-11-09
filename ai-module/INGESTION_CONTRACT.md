# C1 — 적재 입력·오류·중복 정책 결정

2026-11-07 KST · 구현 기준 61e50e9

상태: C1 정책에 따라 C2~C4 서비스·POST API를 구현했다. C4 오류 계약은 API 설계서 6.1과 Mock에 반영했으며, 모의 임베딩·임시 Chroma로 HTTP 검증했다. 실제 모델 API·Backend E2E·DELETE 연동 검증은 남아 있다.

## 1. 유지하는 계약

- POST /internal/documents, multipart/form-data. file / documentId / ownerUuid / documentName 각 1개 필수.
- 정상: 200 {"documentId":12,"chunkCount":57}. chunkCount는 실제 저장 완료한 양수 정수.
- 추출 불가: 422 {"error":"TEXT_EXTRACTION_FAILED"}.
- 인증: 기존 require_internal_token 사용, 실패 시 401 {"detail":"Unauthorized"}. 임베딩·Chroma 생성/호출과 사용자 코드의 PDF 처리는 인증 성공 뒤 시작한다. 프레임워크의 multipart 파싱·임시 스풀링까지 인증 전에 발생하지 않는다고 보장하지 않는다.
- ownerUuid는 Backend가 JWT에서 얻는다. AI의 UUID 형식 검증은 DB 소유권 검증을 대신하지 않는다.

## 2. 입력 검증 기준

| 입력 | 결정 | 경계 검증 |
|---|---|---|
| documentId | ASCII 십진 정수, 1~9223372036854775807(Java Long 범위). 부호·소수·지수 표기·공백 거부 | 0, -1, 1.0, 상한+1 거부 |
| ownerUuid | 36자 하이픈 UUID 형태, 대소문자 허용 후 소문자 표준형 저장. 공백·축약형·URN 거부 | 실제 Member UUID와 호환 |
| documentName | 공백만 있는 값 금지, 최대 255 UTF-16 코드 단위(Backend String.length와 일치), 경로 구분자·제어 문자 거부. 유효한 원문 보존 | 255/256, 한글·보조 평면 문자 경계 |
| file | 업로드 파일 1개, filename 필수, 마지막 확장자 .pdf 대소문자 무시, 실제 선두 %PDF- | MIME 단독 판정 금지 |
| 크기 | 1~10,485,760바이트(10MiB), 분할 읽기로 실측. Content-Length만 신뢰하지 않음 | 0 → 400, 상한 허용, 상한+1 → 413 |
| multipart | 필수 필드 누락·중복·잘못된 자료형 거부. 미정의 필드는 사용하지 않고 무시 | 같은 이름의 file 2개 거부 |

documentName은 출처 표시용이고 파일 경로로 사용하지 않는다. file.filename과 documentName의 문자열 동일성은 강제하지 않는다. PDF 확장자는 file.filename으로 검사한다.

구현 순서: 인증 → 크기가 제한된 multipart 파싱 → 필드 → 파일명/크기/헤더·PDF 추출 → 문서 작업 등록·기존 청크 확인 → 임베딩 → 저장. 현재 C2 준비 함수를 재사용하므로 중복 문서도 PDF 추출은 수행하지만 임베딩 호출·기존 청크 변경은 하지 않는다. 전체 multipart는 11MiB, 파일 1개, 일반 필드 최대 16개·각 1KiB로 제한한다. 임시 파일은 서버 생성 경로만 사용한다.

파일 바이트 제한은 PDF 내부의 압축 해제 후 메모리·페이지 수·추출 시간 제한과 다르다. C2에서는 무제한 자원 사용을 보장한다고 표현하지 않고, 파서 격리와 추출량 제한 필요성을 구현 시 검토한다.

## 3. 오류 매핑

인증 외 오류는 {"error":"CODE"}. 사용자 입력값·공급자 오류 원문·키·로컬 경로를 본문에 넣지 않는다.

| 상황 | HTTP | CODE | 현재 Backend 결과 |
|---|---|---|---|
| 필드 누락·형식·범위·중복 오류 | 400 | INVALID_INPUT | AI_UNAVAILABLE |
| 빈 파일 | 400 | EMPTY_FILE | AI_UNAVAILABLE |
| 확장자 또는 PDF 헤더 오류 | 400 | INVALID_FILE_TYPE | AI_UNAVAILABLE |
| 파일 10MiB 초과 | 413 | FILE_TOO_LARGE | AI_UNAVAILABLE |
| 읽을 수 없는 PDF·전체 공백 텍스트 | 422 | TEXT_EXTRACTION_FAILED | TEXT_EXTRACTION_FAILED |
| 해당 소유자·문서 청크 이미 존재 | 409 | DOCUMENT_ALREADY_EXISTS | AI_UNAVAILABLE + 삭제 시도 |
| 동일 소유자·문서 적재 진행 중 | 409 | INGESTION_IN_PROGRESS | AI_UNAVAILABLE + 삭제 시도 |
| 임베딩 공급자 401/429/연결 오류·잘못된 반환 벡터 | 503 | EMBEDDING_ERROR | AI_UNAVAILABLE |
| Chroma 접근·저장·확인·실패 정리 오류 | 503 | STORAGE_ERROR | AI_UNAVAILABLE |
| 내부 전체 시간 예산 초과 | 503 | INGESTION_TIMEOUT | AI_UNAVAILABLE |
| 분류하지 못한 내부 버그·자원/임시파일 오류 | 500 | INTERNAL_ERROR | AI_UNAVAILABLE |

422는 PDF 파서가 확인한 해석 실패와 텍스트 없음에만 사용한다. 모든 예외를 추출 실패로 묶지 않는다. 임베딩 개별 호출 타임아웃은 EMBEDDING_ERROR, 전체 처리 예산 소진은 INGESTION_TIMEOUT으로 구분한다.

FastAPI 요청 검증 오류의 400 변환은 이 POST 경로에만 적용한다. 다른 라우터, 공개 health, 인증 형식은 유지한다. 정리 자체가 실패하면 STORAGE_ERROR로 반환하고 원인 종류와 정리 실패를 내부 최소 로그에 남긴다.

## 4. 저장과 중복 정책

- 컬렉션은 기존 settings.collection_name, 벡터 1536차원. 메타데이터는 owner_uuid(str), document_id(int), document_name(str), page(int, 1부터).
- 페이지별 800자·100자 오버랩 분할. 공백 페이지를 건너뛰어도 원본 PDF 페이지 번호 유지.
- 청크 ID: {정규 UUID}:{documentId}:{0부터 청크 순번}. 메타데이터 page와 청크 순번은 다른 값이다.
- 동일 문서의 범위는 owner_uuid AND document_id. 문서 ID 단독 조회·삭제 금지.
- 단일 프로세스 작업 등록 후 기존 청크를 검사한다. 진행 중이면 즉시 409, 기존 청크가 하나라도 있으면 409. upsert·선삭제·자동 덮어쓰기 하지 않는다.
- 409 거부 경로는 기존 청크를 정리하지 않는다. 이 요청이 저장을 시작한 뒤에만 자신이 저장 시도한 ID를 정리한다.
- 실패 잔재가 있으면 재요청도 409다. D단계 명시적 삭제로 정리 후 재적재한다. 내용 해시 없는 요청을 같은 내용으로 가정해 성공 처리하지 않는다.
- 다른 소유자·문서 적재는 독립. 다중 워커 안전성을 주장하지 않으며 C/D 검증은 단일 worker 기준이다.

### Backend 연동 주의 — 현재 코드로 보존 보장 불가

AiDocumentClient는 422 외 오류를 BusinessException(AI_UNAVAILABLE)로 바꾸고 DocumentService.upload는 이를 받으면 cleanUp을 호출한다. 따라서 같은 문서 ID를 재사용하는 호출이 추가되면 409 응답 이후 기존/진행 중 청크에 DELETE가 들어올 수 있다.

현재 정상 upload는 매번 새 DB ID를 만들므로 일반 재업로드는 다른 문서다. C단계의 ‘409 시 기존 청크 유지’는 AI POST 직접 검증 범위다. Backend 전체 흐름에서도 보존된다고 보고하지 않는다.

통합 보완안: Backend에서 내부 409를 구분하고 기존/진행 중 문서를 무조건 삭제하지 않도록 처리하거나, 요청 시도 식별자를 포함한 정리 계약을 합의한다. Backend 담당 변경 및 D단계 DELETE 경합 검증 대상으로 남긴다. 이 결정만으로 공용 API나 Backend 코드를 변경하지 않는다.

## 5. 처리 제한

- 임베딩 배치 최대 64, 자동 재시도 0. B단계 SDK 요청 제한 30초 유지하며 남은 전체 예산이 더 짧으면 남은 시간을 적용한다.
- 내부 처리 예산 목표 100초 + 실패 정리 목표 10초. 처리 예산은 인증/입력 검증 후 파일 읽기 시작부터 계산한다. 전송·프레임워크 파싱 시간을 포함한 HTTP 전체 120초 보장은 아니다.
- 값은 AI 내부 정책 모듈에 이름 있는 상수로 모은다. C1에서는 새 환경변수·Compose 변경을 도입하지 않는다. 운영 튜닝이 필요하면 검증 가능한 설정으로 승격한다.
- asyncio 취소는 작업 스레드를 중단하지 못한다. 처리 예산을 하드 종료 보장으로 표현하지 않는다. C3/C4에서 저장 중 취소의 완료 확인·정리를 설계하고 D에서 DELETE와 함께 검증한다.
- 입력 토큰 상한·배치 토큰 상한은 C3 착수 시 설치 SDK/모델 계약 확인으로 정한다. C1의 파일·필드 제한과 구분한다.

## 6. C1 확인 결과와 후속 산출물

- [x] 기존 성공·422·401 본문과 일치하는 정책 결정.
- [x] Java Long, UUID, 파일명 길이, 파일 크기 경계 결정.
- [x] 422 오분류 방지와 오류별 Backend 처리 확인.
- [x] 중복/부분 실패 정책 및 Backend 후속 DELETE 위험 기록.
- [x] C2/C3/C4에서 구현할 검증 경계와 제한 구분.
- [x] C4에서 docs/4.API설계서.md 6.1, mock-data/gen.py와 internal/ 예시 동시 반영. 기존 성공·422 예시는 유지.
- [x] C4 HTTP 테스트에서 입력·인증·오류 매핑과 임시 Chroma 저장을 검증. 실제 Backend E2E 검증을 대체하지 않는다.

현재 PdfValidator.validate는 TODO다. Backend 선행 검사 완료를 가정하지 않으며 AI 내부 검증을 구현한다. UI에 내부 400/413이 그대로 전달된다고 가정하지 않는다.

확인한 근거: AiDocumentClient.java, DocumentService.java, PdfValidator.java, Member.java, core/security.py, API 설계서 6장, mock-data/gen.py의 내부 적재 응답 2종.
