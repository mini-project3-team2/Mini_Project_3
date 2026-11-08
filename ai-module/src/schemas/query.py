"""질의 요청 검증(Pydantic). FastAPI 자동 검증 대신 라우터에서 model_validate로 호출한다.

라우터는 내부 토큰 확인 → JSON 파싱 → QueryRequest.model_validate(raw) 순서로 쓴다.
ValidationError가 나면 QueryInputError로 바꿔 400 {"error":"INVALID_INPUT"}로 응답한다
(API 설계서 6.3: FastAPI 기본 422 대신 400 통일, 내부 필드 구조 미노출).
"""

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

QUESTION_MIN = 1
QUESTION_MAX = 1000
DOCUMENT_ID_MAX = 9223372036854775807  # Java Long 상한
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")


class QueryInputError(Exception):
    """질의 입력 검증 실패. 라우터가 400 {"error":"INVALID_INPUT"}로 변환한다.

    값·내부 필드 구조를 메시지에 담지 않는다(코드만).
    """

    def __init__(self, code: str = "INVALID_INPUT", status_code: int = 400):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


class QueryRequest(BaseModel):
    # camelCase 본문(question/ownerUuid/documentIds)을 받고, 정의되지 않은 필드는 거부한다.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # strict 타입으로 받아 lax 강제 변환을 차단한다. 예) "12"→12, True→1, 12.0→12
    # 같은 자동 변환을 막는다(API 설계서 6.3: 정수 배열 / 문자열 question·ownerUuid).
    question: StrictStr
    owner_uuid: StrictStr = Field(alias="ownerUuid")
    document_ids: list[StrictInt] = Field(alias="documentIds")

    @field_validator("question")
    @classmethod
    def _check_question(cls, value: str) -> str:
        # 타입은 StrictStr이 보장. 여기서는 앞뒤 공백 제거 후 길이만 검사하고,
        # 저장은 정리된 값으로 한다(프롬프트에 그대로 사용).
        trimmed = value.strip()
        if not (QUESTION_MIN <= len(trimmed) <= QUESTION_MAX):
            raise ValueError("question")
        return trimmed

    @field_validator("owner_uuid")
    @classmethod
    def _check_owner_uuid(cls, value: str) -> str:
        # 하이픈 포함 UUID 형태만 허용하고 소문자 표준형으로 정규화한다(검색 필터와 일치).
        if not _UUID_RE.fullmatch(value):
            raise ValueError("ownerUuid")
        return str(UUID(value))

    @field_validator("document_ids")
    @classmethod
    def _check_document_ids(cls, value: list[int]) -> list[int]:
        # 요소 타입(순수 int, bool·문자열·float 제외)은 StrictInt가 보장한다.
        # 여기서는 개수(1개 이상)와 각 값의 범위(1~Java Long 상한)만 검사한다.
        if not value:
            raise ValueError("documentIds")
        for item in value:
            if not (1 <= item <= DOCUMENT_ID_MAX):
                raise ValueError("documentIds")
        return value
