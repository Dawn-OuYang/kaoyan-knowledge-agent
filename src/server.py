from __future__ import annotations

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from rag_engine import KaoyanAgent, KnowledgeBase


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
KB = KnowledgeBase(ROOT / "data" / "knowledge_base.json")
AGENT = KaoyanAgent(KB)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(
                {
                    "status": "ok",
                    "project": "kaoyan-knowledge-agent",
                    "model_gateway": AGENT.model_gateway.status(),
                }
            )
            return
        if path == "/api/status":
            self._json(
                {
                    "project": "考研各专业知识库问答智能体",
                    "skill_version": "0.3.0",
                    "knowledge_items": len(KB.docs),
                    "specialties": KB.specialties(),
                    "model_gateway": AGENT.model_gateway.status(),
                    "runtime_claim": "local-demo" if not AGENT.model_gateway.enabled else "external-model-connected",
                }
            )
            return
        if path == "/api/specialties":
            self._json({"specialties": KB.specialties()})
            return
        if path == "/":
            self._file(STATIC / "index.html")
            return
        target = (STATIC / path.lstrip("/")).resolve()
        if STATIC.resolve() in target.parents and target.exists() and target.is_file():
            self._file(target)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = self._read_json()
        if path == "/api/ask":
            question = str(payload.get("question", "")).strip()
            specialty = str(payload.get("specialty", "全部")).strip() or "全部"
            mode = str(payload.get("mode", "qa")).strip() or "qa"
            profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
            if not question:
                self._json({"error": "question is required"}, status=400)
                return
            self._json(AGENT.answer(question, specialty=specialty, mode=mode, profile=profile))
            return
        if path == "/api/skill/invoke":
            try:
                self._json(AGENT.invoke_skill(payload))
            except ValueError as exc:
                self._json({"error": str(exc)}, status=400)
            return
        self.send_error(404, "Not found")

    def log_message(self, fmt: str, *args) -> None:
        print("[server]", fmt % args)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path) -> None:
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("KAOYAN_HOST", "127.0.0.1")
    port = int(os.environ.get("KAOYAN_PORT", "7860"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Kaoyan Knowledge Agent running at http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
