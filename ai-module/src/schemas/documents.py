"""Validate multipart identity without FastAPI's default 422 response."""

from dataclasses import dataclass
import re
import unicodedata
from uuid import UUID

from pydantic import BaseModel, Field
from starlette.datastructures import FormData, UploadFile

from src.services.ingest import IngestionError


@dataclass(frozen=True)
class IngestInput:
    file: UploadFile
    document_id: int
    owner_uuid: str
    document_name: str

    @classmethod
    def from_form(cls, form: FormData):
        names = ("file", "documentId", "ownerUuid", "documentName")
        if any(len(form.getlist(name)) != 1 for name in names):
            raise IngestionError("INVALID_INPUT", 400)
        upload, doc_id, owner, name = (form[key] for key in names)
        if (not isinstance(upload, UploadFile)
                or not all(isinstance(value, str) for value in (doc_id, owner, name))):
            raise IngestionError("INVALID_INPUT", 400)
        if not re.fullmatch(r"[0-9]{1,19}", doc_id) or not 0 < int(doc_id) <= 9223372036854775807:
            raise IngestionError("INVALID_INPUT", 400)
        if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", owner):
            raise IngestionError("INVALID_INPUT", 400)
        try:
            name_units = len(name.encode("utf-16-le")) // 2
        except UnicodeEncodeError:
            raise IngestionError("INVALID_INPUT", 400) from None
        if (not name.strip() or name_units > 255 or "/" in name or "\\" in name
                or any(unicodedata.category(char) == "Cc" for char in name)):
            raise IngestionError("INVALID_INPUT", 400)
        return cls(upload, int(doc_id), str(UUID(owner)), name)


class IngestResponse(BaseModel):
    documentId: int = Field(gt=0)
    chunkCount: int = Field(gt=0)
