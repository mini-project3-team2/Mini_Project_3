from contextlib import asynccontextmanager
import asyncio
import tempfile
import threading
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from src.api.main import create_app
from src.services.ingest import IngestionError
from src.services.pdf import prepare_pdf
from test_pdf import synthetic_pdf
from test_resources import test_settings
from src.api.routers.documents import finish_before_cancelling


class DocumentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = test_settings(self.temp.name)
        self.embeddings = AsyncMock()
        self.embeddings.aembed_documents.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]

        @asynccontextmanager
        async def fake_embeddings(settings):
            yield self.embeddings

        self.factory = self.enterContext(patch("src.core.resources.open_embeddings", fake_embeddings))
        self.app = create_app(lambda: self.settings)
        self.client = self.enterContext(TestClient(self.app))
        self.pdf = synthetic_pdf(["first page", "", "third page"])
        self.fields = {"documentId": "12", "ownerUuid": "8f14e45f-ea4d-4bb0-9f17-a93e15de9032",
                       "documentName": "교안.pdf"}
        self.headers = {"X-Internal-Token": "test-only-token"}

    def post(self, fields=None, body=None, filename="sample.pdf"):
        return self.client.post("/internal/documents", headers=self.headers,
                                data=self.fields if fields is None else fields,
                                files={"file": (filename, self.pdf if body is None else body, "application/pdf")})

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(response.json(), {"error": code})

    def test_http_pdf_to_chroma_success_duplicate_and_upload_closed(self):
        streams = []
        def capture(source, *args, **kwargs):
            streams.append(source)
            return prepare_pdf(source, *args, **kwargs)
        with patch("src.api.routers.documents.prepare_pdf", side_effect=capture):
            response = self.post(fields=self.fields | {"ownerUuid": self.fields["ownerUuid"].upper()})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"documentId": 12, "chunkCount": 2})
        self.assertTrue(streams[0].closed)
        collection = self.client.portal.call(self.app.state.resources.collection)
        rows = collection.get(include=["metadatas"])
        self.assertEqual({m["page"] for m in rows["metadatas"]}, {1, 3})
        self.assertTrue(all(m["owner_uuid"] == self.fields["ownerUuid"] for m in rows["metadatas"]))
        self.assert_error(self.post(), 409, "DOCUMENT_ALREADY_EXISTS")
        self.embeddings.aembed_documents.assert_awaited_once()
        self.assertEqual(collection.count(), 2)

    def test_authentication_precedes_parsing_and_side_effects(self):
        for headers in ({}, {"X-Internal-Token": "wrong"},
                        [("X-Internal-Token", "test-only-token"), ("X-Internal-Token", "test-only-token")]):
            with patch("src.api.routers.documents.prepare_pdf") as pdf:
                response = self.client.post("/internal/documents", headers=headers, content=b"malformed")
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Unauthorized"})
                pdf.assert_not_called()
        self.assertIsNone(self.app.state.resources._collection)
        self.assertIsNone(self.app.state.resources._embeddings)
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_delete_removes_only_target_and_is_repeatable(self):
        owner = self.fields["ownerUuid"]
        other = "12345678-1234-1234-1234-123456789abc"
        for fields in (self.fields, self.fields | {"documentId": "13"},
                       self.fields | {"ownerUuid": other}):
            self.assertEqual(self.post(fields=fields).status_code, 200)
        collection = self.client.portal.call(self.app.state.resources.collection)
        rows = collection.get(include=["metadatas"])
        expected = {key for key, meta in zip(rows["ids"], rows["metadatas"])
                    if (meta["owner_uuid"], meta["document_id"]) != (owner, 12)}
        self.assertEqual(len(expected), 4)
        for _ in range(2):
            response = self.client.delete("/internal/documents/12", headers=self.headers,
                                          params={"ownerUuid": owner.upper()})
            self.assertEqual(response.status_code, 204, response.text)
            self.assertEqual(response.content, b"")
            self.assertEqual(set(collection.get(include=[])["ids"]), expected)

    def test_delete_checks_auth_and_identity_before_storage(self):
        path = "/internal/documents/"
        for headers in ({}, {"X-Internal-Token": "wrong"}):
            self.assertEqual(self.client.delete(path + "bad", headers=headers).status_code, 401)
        owner = self.fields["ownerUuid"]
        for doc_id, owners in (("0", [owner]), ("9223372036854775808", [owner]),
                               ("12", []), ("12", ["bad"]), ("12", [owner, owner])):
            response = self.client.delete(path + doc_id, headers=self.headers,
                                          params=[("ownerUuid", value) for value in owners])
            self.assert_error(response, 400, "INVALID_INPUT")
        self.assertIsNone(self.app.state.resources._collection)

    def test_delete_storage_failure_and_incomplete_removal(self):
        self.assertEqual(self.post().status_code, 200)
        collection = self.client.portal.call(self.app.state.resources.collection)
        for failure in (RuntimeError("private storage detail"), None):
            with patch.object(collection, "delete", side_effect=failure):
                response = self.client.delete("/internal/documents/12", headers=self.headers,
                                              params={"ownerUuid": self.fields["ownerUuid"]})
            self.assert_error(response, 503, "STORAGE_ERROR")

    def test_invalid_fields_never_extract_or_create_clients(self):
        cases = []
        for key in self.fields:
            cases.append({k: v for k, v in self.fields.items() if k != key})
        for value in ("0", "-1", "1.0", "1e2", " 12", "9223372036854775808", "１２"):
            cases.append(self.fields | {"documentId": value})
        for value in ("bad", self.fields["ownerUuid"].replace("-", ""), " " + self.fields["ownerUuid"]):
            cases.append(self.fields | {"ownerUuid": value})
        for value in (" ", "x" * 256, "😀" * 128, "../test.pdf", "a\\b.pdf", "a\x00.pdf"):
            cases.append(self.fields | {"documentName": value})
        with patch("src.api.routers.documents.prepare_pdf") as pdf:
            for fields in cases:
                with self.subTest(fields=fields):
                    self.assert_error(self.post(fields=fields), 400, "INVALID_INPUT")
            pdf.assert_not_called()
        self.assertIsNone(self.app.state.resources._collection)
        self.assertIsNone(self.app.state.resources._embeddings)

    def test_long_id_and_utf16_filename_boundary(self):
        response = self.post(fields=self.fields | {
            "documentId": "9223372036854775807", "documentName": "😀" * 127 + "x",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["documentId"], 9223372036854775807)

    def test_duplicate_fields_files_missing_file_and_malformed_body(self):
        base = [(key, (None, value)) for key, value in self.fields.items()]
        file = ("file", ("a.pdf", self.pdf, "application/pdf"))
        for parts in (base, base + [file, file], base + [file, ("documentId", (None, "13"))]):
            response = self.client.post("/internal/documents", headers=self.headers, files=parts)
            self.assert_error(response, 400, "INVALID_INPUT")
        response = self.client.post("/internal/documents", headers=self.headers, json=self.fields)
        self.assert_error(response, 400, "INVALID_INPUT")
        response = self.client.post("/internal/documents", headers=self.headers | {
            "Content-Type": "multipart/form-data"}, content=b"bad multipart")
        self.assert_error(response, 400, "INVALID_INPUT")
        self.assertIsNone(self.app.state.resources._collection)

    def test_file_errors_and_both_size_limits(self):
        for body, filename, status, code in (
            (b"", "a.pdf", 400, "EMPTY_FILE"),
            (b"bad", "a.pdf", 400, "INVALID_FILE_TYPE"),
            (self.pdf, "a.exe", 400, "INVALID_FILE_TYPE"),
            (b"%PDF-1.7\ncorrupt", "a.pdf", 422, "TEXT_EXTRACTION_FAILED"),
            (synthetic_pdf([""]), "a.pdf", 422, "TEXT_EXTRACTION_FAILED"),
            (b"%PDF-" + b"x" * (10 * 1024 * 1024), "a.pdf", 413, "FILE_TOO_LARGE"),
            (b"%PDF-" + b"x" * (11 * 1024 * 1024), "a.pdf", 413, "FILE_TOO_LARGE"),
        ):
            with self.subTest(code=code, size=len(body)):
                self.assert_error(self.post(body=body, filename=filename), status, code)
        self.assertIsNone(self.app.state.resources._collection)

    def test_domain_errors_and_internal_errors_are_sanitized(self):
        for code, status in (("INGESTION_IN_PROGRESS", 409), ("STORAGE_ERROR", 503),
                             ("INGESTION_TIMEOUT", 503)):
            with patch.object(self.app.state.resources.ingestion, "ingest", side_effect=IngestionError(code, status)):
                self.assert_error(self.post(), status, code)
        with patch("src.api.routers.documents.prepare_pdf", side_effect=RuntimeError("secret path")):
            with self.assertLogs("src.api.routers.documents", level="ERROR") as logs:
                self.assert_error(self.post(), 500, "INTERNAL_ERROR")
            self.assertNotIn("secret path", str(logs.output))

    def test_client_initialization_errors_are_not_pdf_errors(self):
        with patch.object(self.app.state.resources, "collection", side_effect=RuntimeError("private DB error")):
            self.assert_error(self.post(), 503, "STORAGE_ERROR")
        with patch.object(self.app.state.resources, "embeddings", side_effect=RuntimeError("private key error")):
            self.assert_error(self.post(), 503, "EMBEDDING_ERROR")

    def test_pdf_time_is_deducted_before_external_calls(self):
        def slow(*args, **kwargs):
            time.sleep(0.02)
            return prepare_pdf(*args, **kwargs)
        with patch("src.api.routers.documents.DEFAULT_BUDGET_SECONDS", 0.001), \
             patch("src.api.routers.documents.prepare_pdf", side_effect=slow):
            self.assert_error(self.post(), 503, "INGESTION_TIMEOUT")
        self.assertIsNone(self.app.state.resources._collection)

    def test_openapi_describes_multipart_contract(self):
        spec = self.client.get("/openapi.json").json()["paths"]["/internal/documents"]["post"]
        fields = spec["requestBody"]["content"]["multipart/form-data"]["schema"]["required"]
        self.assertEqual(set(fields), {"file", "documentId", "ownerUuid", "documentName"})


class PreparationCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_repeated_cancel_drains_worker_before_returning(self):
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        def worker():
            started.set()
            release.wait(2)
            finished.set()
        task = asyncio.create_task(finish_before_cancelling(asyncio.to_thread(worker)))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 1))
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
        finally:
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(finished.is_set())


if __name__ == "__main__":
    unittest.main()
