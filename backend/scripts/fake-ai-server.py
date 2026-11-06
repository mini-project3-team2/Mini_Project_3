"""
로컬 확인용 가짜 AI Module (실제 AI Module 이 준비되기 전까지 Backend 업로드 · 삭제 흐름 확인용)
실행 (저장소 최상위에서): python backend/scripts/fake-ai-server.py
  FAKE_AI_MODE=ok(기본) | 422(글자 추출 실패) | 500(AI 오류)  — 예: FAKE_AI_MODE=422 python backend/scripts/fake-ai-server.py
- X-Internal-Token 은 저장소 최상위 .env 의 AI_INTERNAL_TOKEN 과 비교 (다르면 401)
- GET /debug/documents : 현재 "적재된" 문서 id 목록 (적재 실패 정리 · 삭제 확인용)
파일 내용은 출력하지 않는다
"""
import json
import os
import re
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def read_token():
    try:
        with open(".env", encoding="utf-8") as f:
            for line in f:
                if line.startswith("AI_INTERNAL_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return ""


TOKEN = read_token()
MODE = os.environ.get("FAKE_AI_MODE", "ok")
STORE = {}  # documentId -> {"ownerUuid", "documentName"}


class Handler(BaseHTTPRequestHandler):

    def _send(self, status, body=None):
        self.send_response(status)
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_header("Content-Length", "0")
            self.end_headers()

    def _authorized(self):
        if self.headers.get("X-Internal-Token") != TOKEN or not TOKEN:
            print("401 X-Internal-Token 불일치")
            self._send(401, {"error": "UNAUTHORIZED"})
            return False
        return True

    def _read_body(self):
        """Content-Length 또는 Transfer-Encoding: chunked (WebClient 기본) 본문 읽기"""
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            chunks = []
            while True:
                size = int(self.rfile.readline().split(b";")[0].strip(), 16)
                if size == 0:
                    self.rfile.readline()
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.readline()
            return b"".join(chunks)
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send(200, {"status": "ok"})
        if path == "/debug/documents":
            return self._send(200, {"documentIds": sorted(STORE)})
        self._send(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        if urlparse(self.path).path != "/internal/documents":
            return self._send(404, {"error": "NOT_FOUND"})
        if not self._authorized():
            return
        raw = self._read_body()
        msg = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + raw)
        fields, file_size = {}, 0
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            payload = part.get_payload(decode=True) or b""
            if name == "file":
                file_size = len(payload)
            else:
                fields[name] = payload.decode("utf-8")
        if "documentId" not in fields:
            print("400 본문에서 documentId 를 찾지 못함")
            return self._send(400, {"error": "INVALID_REQUEST"})
        doc_id = int(fields["documentId"])
        print(f"적재 요청 documentId={doc_id} ownerUuid={fields.get('ownerUuid')} "
              f"name={fields.get('documentName')} size={file_size} mode={MODE}")
        if MODE == "422":
            return self._send(422, {"error": "TEXT_EXTRACTION_FAILED"})
        if MODE == "500":
            return self._send(500, {"error": "EMBEDDING_ERROR"})
        STORE[doc_id] = {"ownerUuid": fields.get("ownerUuid"), "documentName": fields.get("documentName")}
        self._send(200, {"documentId": doc_id, "chunkCount": 3})

    def do_DELETE(self):
        url = urlparse(self.path)
        m = re.fullmatch(r"/internal/documents/(\d+)", url.path)
        if not m:
            return self._send(404, {"error": "NOT_FOUND"})
        if not self._authorized():
            return
        doc_id = int(m.group(1))
        owner = parse_qs(url.query).get("ownerUuid", [""])[0]
        if doc_id in STORE and STORE[doc_id]["ownerUuid"] == owner:
            del STORE[doc_id]
        print(f"청크 삭제 documentId={doc_id} ownerUuid={owner}")
        self._send(204)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"가짜 AI Module http://localhost:8000 mode={MODE} token={'설정됨' if TOKEN else '없음(.env 확인)'}")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
