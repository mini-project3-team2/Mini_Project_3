"""페이지 수 상한(#81) 재현용 PDF 생성. 이미 설치된 pypdf만 사용(새 패키지 없음).

보안점검서의 "수정 전 → 수정 후" 근거용으로, 수동 업로드에 쓸 PDF를 만든다.
각 페이지에 짧은 텍스트를 넣어 TEXT_EXTRACTION_FAILED가 아니라 TOO_MANY_PAGES로
거부되게 한다(빈 페이지만이면 추출 실패로 분류됨).

생성 파일은 ai-module/data/ 아래에 저장한다. 이 경로는 .gitignore(/ai-module/data/)에
이미 포함되어 커밋되지 않는다. 스크립트 자체에는 키·비밀정보가 없다.

사용 예:
    uv run --no-sync python scripts/make_big_pdf.py --pages 501
    uv run --no-sync python scripts/make_big_pdf.py --pages 501 --verify
"""
import argparse
import io
from pathlib import Path
import sys

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

ROOT = Path(__file__).resolve().parents[1]  # ai-module/
DEFAULT_OUTPUT = ROOT / "data" / "big.pdf"
MAX_PDF_BYTES = 10 * 1024 * 1024


def build_pdf(pages: int) -> bytes:
    """글자가 있는 page쪽짜리 PDF 바이트를 만든다(test_pdf.synthetic_pdf와 같은 방식)."""
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    for index in range(1, pages + 1):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
        })
        content = DecodedStreamObject()
        content.set_data(f"BT /F1 12 Tf 72 720 Td (page {index}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def verify_extractable(data: bytes) -> int:
    """생성한 PDF에서 실제로 텍스트가 추출되는지 extract_chunks로 확인한다(API 호출 없음)."""
    sys.path.insert(0, str(ROOT))
    from src.services.pdf import staged_pdf, extract_chunks

    with staged_pdf(io.BytesIO(data), "big.pdf") as path:
        chunks = extract_chunks(
            path, owner_uuid="8f14e45f-ea4d-4bb0-9f17-a93e15de9032",
            document_id=1, document_name="big.pdf",
        )
    return len(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description="페이지 수 상한 재현용 PDF 생성(pypdf만 사용).")
    parser.add_argument("--pages", type=int, default=501, help="페이지 수(기본 501).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="출력 경로(기본 ai-module/data/big.pdf, .gitignore 대상).")
    parser.add_argument("--verify", action="store_true",
                        help="생성 후 extract_chunks로 텍스트 추출 가능 여부를 확인한다.")
    args = parser.parse_args()
    if args.pages < 1:
        print("--pages 는 1 이상이어야 합니다.")
        return 2

    data = build_pdf(args.pages)
    size = len(data)
    if size > MAX_PDF_BYTES:
        print(f"경고: 생성 파일이 {size} 바이트로 10MiB를 초과합니다. 페이지 수를 줄이세요.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"생성: {args.output} (pages={args.pages}, size={size} bytes)")

    if args.verify:
        count = verify_extractable(data)
        print(f"추출 확인: chunk {count}개 (텍스트 추출 OK, TEXT_EXTRACTION_FAILED 아님)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
