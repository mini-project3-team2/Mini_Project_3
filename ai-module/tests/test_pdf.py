import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject, DictionaryObject, NameObject,
)

from src.services.pdf import (
    MAX_PDF_BYTES, PdfProcessingError, prepare_pdf, staged_pdf,
)


def synthetic_pdf(texts, password=None):
    """Reproducible PDF with real text objects, no additional dependency."""
    writer = PdfWriter()
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
        })
        content = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(content)
    if password:
        writer.encrypt(password)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class PdfTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.identity = dict(
            owner_uuid="8f14e45f-ea4d-4bb0-9f17-a93e15de9032",
            document_id=12, document_name="수업자료.pdf",
        )

    def prepare(self, data, filename="sample.pdf"):
        return prepare_pdf(
            io.BytesIO(data), filename, temp_directory=self.root, **self.identity
        )

    def assert_clean(self):
        self.assertEqual(list(self.root.iterdir()), [])

    def test_real_pdf_blank_page_preserves_page_and_metadata(self):
        chunks = self.prepare(synthetic_pdf(["first page", "   ", "third page"]))
        self.assertEqual([c.page_content for c in chunks], ["first page", "third page"])
        self.assertEqual([c.metadata["page"] for c in chunks], [1, 3])
        for chunk in chunks:
            self.assertEqual(chunk.metadata, {
                "owner_uuid": self.identity["owner_uuid"], "document_id": 12,
                "document_name": "수업자료.pdf", "page": chunk.metadata["page"],
            })
        self.assert_clean()

    def test_chunk_size_and_overlap_without_crossing_pages(self):
        text = ("abcdefghijklmnopqrstuvwxyz" * 66)[:1700]
        chunks = self.prepare(synthetic_pdf([text, "second"]))
        self.assertEqual([len(c.page_content) for c in chunks], [800, 800, 300, 6])
        self.assertEqual([c.page_content for c in chunks[:3]],
                         [text[:800], text[700:1500], text[1400:]])
        self.assertEqual([c.metadata["page"] for c in chunks], [1, 1, 1, 2])
        self.assert_clean()

    def test_invalid_files_and_parser_failures_clean_up(self):
        cases = [
            (b"", "a.pdf", "EMPTY_FILE", 400),
            (b"%PDF-", None, "INVALID_FILE_TYPE", 400),
            (b"%PDF-", "a.pdf.exe", "INVALID_FILE_TYPE", 400),
            (b"hello", "a.pdf", "INVALID_FILE_TYPE", 400),
            (b"%PDF-1.7\ninvalid", "a.pdf", "TEXT_EXTRACTION_FAILED", 422),
            (synthetic_pdf(["", "  "]), "a.pdf", "TEXT_EXTRACTION_FAILED", 422),
            (synthetic_pdf(["secret"], "password"), "a.pdf", "TEXT_EXTRACTION_FAILED", 422),
        ]
        for data, filename, code, status in cases:
            with self.subTest(code=code, filename=filename):
                with self.assertRaises(PdfProcessingError) as caught:
                    self.prepare(data, filename)
                self.assertEqual((caught.exception.code, caught.exception.status_code), (code, status))
                self.assertEqual(str(caught.exception), code)
                self.assert_clean()

    def test_exact_size_boundary_and_generated_path(self):
        data = b"%PDF-" + b"x" * (MAX_PDF_BYTES - 5)
        with staged_pdf(io.BytesIO(data), "../../untrusted.PDF", temp_directory=self.root) as path:
            self.assertEqual(path.stat().st_size, MAX_PDF_BYTES)
            self.assertTrue(path.is_relative_to(self.root))
            self.assertNotIn("untrusted", str(path))
        self.assert_clean()
        with self.assertRaises(PdfProcessingError) as caught:
            self.prepare(data + b"x")
        self.assertEqual(caught.exception.code, "FILE_TOO_LARGE")
        self.assert_clean()

    def test_short_reads_and_source_ownership(self):
        class ShortReads(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 2))
        source = ShortReads(b"%PDF-test")
        with staged_pdf(source, "a.pdf", temp_directory=self.root) as path:
            self.assertEqual(path.read_bytes(), b"%PDF-test")
        self.assertFalse(source.closed)
        self.assert_clean()

    def test_consumer_failure_and_base_exception_clean_up(self):
        for error in (RuntimeError("test"), KeyboardInterrupt()):
            with self.assertRaises(type(error)):
                with staged_pdf(io.BytesIO(b"%PDF-test"), "a.pdf", temp_directory=self.root):
                    raise error
            self.assert_clean()

    def test_unexpected_parser_error_is_not_422(self):
        for error in (OSError("disk error"), RuntimeError("bug")):
            with patch("src.services.pdf.PyPDFLoader", side_effect=error):
                with self.assertRaises(type(error)):
                    self.prepare(synthetic_pdf(["text"]))
            self.assert_clean()

    def test_source_read_failure_cleans_up(self):
        class BrokenStream(io.BytesIO):
            def read(self, size=-1):
                raise OSError("read failure")
        with self.assertRaises(OSError):
            with staged_pdf(BrokenStream(), "a.pdf", temp_directory=self.root):
                self.fail("must not yield")
        self.assert_clean()


if __name__ == "__main__":
    unittest.main()
