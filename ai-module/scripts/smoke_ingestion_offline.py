"""Local HTTP smoke check using synthetic settings/PDF and fake embeddings.

Run from ai-module: uv run --locked python scripts/smoke_ingestion_offline.py
Uses test fixtures, loopback only, an ephemeral port, and a temporary Chroma DB.
Does not load .env or construct an OpenAI client. Prints a safe JSON summary.
"""

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch

AI_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_DIR))
sys.path.insert(0, str(AI_DIR / "tests"))

import httpx
import uvicorn

from src.api.main import create_app
from src.services.vectorstore import open_collection
from test_pdf import synthetic_pdf
from test_resources import test_settings


def main():
    calls = []

    class FakeEmbeddings:
        async def aembed_documents(self, texts):
            calls.append(len(texts))
            return [[0.1] * 1536 for _ in texts]

    @asynccontextmanager
    async def embeddings_factory(settings):
        yield FakeEmbeddings()

    with tempfile.TemporaryDirectory(prefix="asknote-smoke-") as directory:
        settings = test_settings(directory)
        app = create_app(lambda: settings)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        base_url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        with patch("src.core.resources.open_embeddings", embeddings_factory):
            try:
                thread.start()
                start_deadline = time.monotonic() + 10
                while not server.started:
                    if not thread.is_alive() or time.monotonic() >= start_deadline:
                        raise RuntimeError("server_start_failed")
                    time.sleep(0.02)
                with httpx.Client(base_url=base_url, timeout=10, trust_env=False) as client:
                    health = client.get("/health")
                    assert health.status_code == 200 and health.json() == {"status": "ok"}
                    unauthorized = client.post("/internal/documents", content=b"invalid")
                    assert unauthorized.status_code == 401
                    headers = {"X-Internal-Token": "test-only-token"}
                    data = {"documentId": "12", "ownerUuid": "8f14e45f-ea4d-4bb0-9f17-a93e15de9032",
                            "documentName": "synthetic.pdf"}
                    pdf = synthetic_pdf(["first page", "", "third page"])
                    files = {"file": ("synthetic.pdf", pdf, "application/pdf")}
                    uploaded = client.post("/internal/documents", headers=headers, data=data, files=files)
                    assert uploaded.status_code == 200
                    assert uploaded.json() == {"documentId": 12, "chunkCount": 2}
                    duplicate = client.post("/internal/documents", headers=headers, data=data, files=files)
                    assert duplicate.status_code == 409
                    assert duplicate.json() == {"error": "DOCUMENT_ALREADY_EXISTS"}
                    invalid = client.post("/internal/documents", headers=headers,
                                          data=data | {"documentId": "0"}, files=files)
                    assert invalid.status_code == 400
                    assert invalid.json() == {"error": "INVALID_INPUT"}
                    second = client.post("/internal/documents", headers=headers,
                                         data=data | {"documentId": "13"}, files=files)
                    assert second.status_code == 200
                    for _ in range(2):
                        deleted = client.delete("/internal/documents/13", headers=headers,
                                                params={"ownerUuid": data["ownerUuid"]})
                        assert deleted.status_code == 204 and deleted.content == b""
                    assert calls == [2, 2]
            finally:
                server.should_exit = True
                thread.join(timeout=15)
                listener.close()
                if thread.is_alive():
                    raise RuntimeError("server_shutdown_failed")

        async def inspect_saved():
            async with open_collection(settings) as collection:
                rows = collection.get(include=["metadatas"])
                assert len(rows["ids"]) == 2
                assert all(meta["document_id"] == 12 for meta in rows["metadatas"])
                pages = sorted(metadata["page"] for metadata in rows["metadatas"])
                assert pages == [1, 3]
                return pages

        pages = asyncio.run(inspect_saved())
    print(json.dumps({
        "success": True, "transport": "real_uvicorn_loopback_http",
        "embedding": "synthetic_fake_no_provider_calls", "storage": "temporary_chroma",
        "health_status": 200, "unauthorized_status": 401,
        "ingest_status": 200, "chunk_count": 2,
        "duplicate_status": 409, "invalid_input_status": 400,
        "delete_and_retry_status": 204, "deleted_chunks_after_reopen": 0,
        "embedding_batch_sizes": calls, "pages_after_storage_reopen": pages,
        "server_stopped": True, "temporary_storage_removed": True,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"success": False, "error_type": type(error).__name__}))
        sys.exit(1)
