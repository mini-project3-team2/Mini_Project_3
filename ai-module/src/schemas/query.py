"""질의 요청 검증(Pydantic). FastAPI 자동 검증 대신 라우터에서 model_validate로 호출한다.

라우터는 내부 토큰 확인 → JSON 파싱 → QueryRequest.model_validate(raw) 순서로 쓴다.
ValidationError가 나면 QueryInputError로 바꿔 400 {"error":"INVALID_INPUT"}로 응답한다
(API 설계서 6.3: FastAPI 기본 422 대신 400 통일, 내부 필드 구조 미노출).
"""

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    question: str
    owner_uuid: str = Field(alias="ownerUuid")
    document_ids: list[int] = Field(alias="documentIds")

    @field_validator("question")
    @classmethod
    def _check_question(cls, value: str) -> str:
        # 앞뒤 공백 제거 후 길이를 센다. 저장은 정리된 값으로 한다(프롬프트에 그대로 사용).
        if not isinstance(value, str):
            raise ValueError("question")
        trimmed = value.strip()
        if not (QUESTION_MIN <= len(trimmed) <= QUESTION_MAX):
            raise ValueError("question")
        return trimmed

    @field_validator("owner_uuid")
    @classmethod
    def _check_owner_uuid(cls, value: str) -> str:
        # 하이픈 포함 UUID 형태만 허용하고 소문자 표준형으로 정규화한다(검색 필터와 일치).
        if not isinstance(value, str) or not _UUID_RE.fullmatch(value):
            raise ValueError("ownerUuid")
        return str(UUID(value))

    @field_validator("document_ids")
    @classmethod
    def _check_document_ids(cls, value: list[int]) -> list[int]:
        # 1개 이상의 정수 배열. 각 값은 1~Java Long 상한. bool은 int가 아니다.
        if not isinstance(value, list) or not value:
            raise ValueError("documentIds")
        for item in value:
            if isinstance(item, bool) or type(item) is not int:
                raise ValueError("documentIds")
            if not (1 <= item <= DOCUMENT_ID_MAX):
                raise ValueError("documentIds")
        return value
