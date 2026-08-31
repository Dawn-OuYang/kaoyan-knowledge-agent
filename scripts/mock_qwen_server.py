from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/api/qwen/generate":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or "0")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        answer = "外部模型链路测试成功。回答依据检索证据生成，并保留官方来源提示。[1]"
        body = json.dumps(
            {
                "model": payload.get("model", "mock-qwen3.5"),
                "answer": answer,
                "runtime": {"device": "test-double", "framework": "mock"},
                "usage": {"prompt_tokens": 128, "completion_tokens": 24, "total_tokens": 152},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
