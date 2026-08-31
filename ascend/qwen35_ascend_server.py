from __future__ import annotations

import argparse
import json
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class Qwen35Runtime:
    def __init__(self, model_path: str, model_name: str) -> None:
        import torch
        import torch_npu  # noqa: F401
        from transformers import AutoProcessor

        try:
            from transformers import AutoModelForImageTextToText as ModelClass
        except ImportError:
            from transformers import AutoModelForCausalLM as ModelClass

        self.torch = torch
        self.model_name = model_name
        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, use_fast=False)
        self.model = ModelClass.from_pretrained(
            model_path,
            dtype=torch.bfloat16,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        ).to("npu")
        self.model.eval()
        self.lock = threading.Lock()

    def generate(self, messages: list[dict[str, Any]], max_tokens: int, temperature: float) -> dict[str, Any]:
        started = time.perf_counter()
        processor_messages = self._processor_messages(messages)
        inputs = self.processor.apply_chat_template(
            processor_messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        inputs = {key: value.to("npu") if hasattr(value, "to") else value for key, value in inputs.items()}
        input_tokens = int(inputs["input_ids"].shape[-1])
        self.torch.npu.synchronize()
        preparation_ms = (time.perf_counter() - started) * 1000

        generation_args = {
            "max_new_tokens": max_tokens,
            "do_sample": temperature > 0,
            "temperature": max(temperature, 1e-5),
            "pad_token_id": getattr(self.processor, "tokenizer", self.processor).eos_token_id,
        }
        queue_started = time.perf_counter()
        with self.lock, self.torch.inference_mode():
            queue_wait_ms = (time.perf_counter() - queue_started) * 1000
            self.torch.npu.reset_peak_memory_stats()
            generation_started = time.perf_counter()
            output = self.model.generate(**inputs, **generation_args)
            self.torch.npu.synchronize()
            generation_ms = (time.perf_counter() - generation_started) * 1000
            peak_memory_mb = self.torch.npu.max_memory_allocated() / (1024 * 1024)

        generated = output[0][input_tokens:]
        text = self.processor.decode(generated, skip_special_tokens=True).strip()
        elapsed = time.perf_counter() - started
        completion_tokens = int(generated.shape[-1])
        return {
            "text": text,
            "prompt_tokens": input_tokens,
            "completion_tokens": completion_tokens,
            "preparation_ms": round(preparation_ms, 2),
            "queue_wait_ms": round(queue_wait_ms, 2),
            "generation_ms": round(generation_ms, 2),
            "elapsed_ms": round(elapsed * 1000, 2),
            "completion_tokens_per_second": round(completion_tokens / (generation_ms / 1000), 3) if generation_ms else 0.0,
            "peak_npu_memory_mb": round(peak_memory_mb, 2),
        }

    @staticmethod
    def _processor_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize text messages for the multimodal Qwen processor."""
        normalized: list[dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("each message must be an object")
            role = str(message.get("role", "")).strip()
            if not role:
                raise ValueError("each message requires a role")

            content = message.get("content", "")
            if isinstance(content, str):
                parts = [{"type": "text", "text": content}]
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, str):
                        parts.append({"type": "text", "text": part})
                    elif isinstance(part, dict):
                        normalized_part = dict(part)
                        if normalized_part.get("type") == "input_text":
                            normalized_part["type"] = "text"
                        parts.append(normalized_part)
                    else:
                        raise ValueError("message content parts must be strings or objects")
            else:
                raise ValueError("message content must be a string or list")
            normalized.append({"role": role, "content": parts})
        return normalized


RUNTIME: Qwen35Runtime


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._json({"status": "ok", "model": RUNTIME.model_name, "device": "Ascend NPU"})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/qwen/generate":
            self.send_error(404)
            return
        payload = self._read_json()
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            self._json({"error": {"message": "messages is required"}}, status=400)
            return
        try:
            result = RUNTIME.generate(
                messages,
                max_tokens=int(payload.get("max_new_tokens", 768)),
                temperature=float(payload.get("temperature", 0.1)),
            )
        except Exception as exc:
            traceback.print_exc()
            self._json({"error": {"message": str(exc)}}, status=500)
            return

        self._json(
            {
                "request_id": f"qwen-{uuid.uuid4().hex}",
                "created": int(time.time()),
                "model": RUNTIME.model_name,
                "answer": result["text"],
                "runtime": {"device": "Ascend NPU", "framework": "torch_npu"},
                "usage": {
                    "prompt_tokens": result["prompt_tokens"],
                    "completion_tokens": result["completion_tokens"],
                    "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
                    "preparation_ms": result["preparation_ms"],
                    "queue_wait_ms": result["queue_wait_ms"],
                    "generation_ms": result["generation_ms"],
                    "total_inference_ms": result["elapsed_ms"],
                    "completion_tokens_per_second": result["completion_tokens_per_second"],
                    "peak_npu_memory_mb": result["peak_npu_memory_mb"],
                },
            }
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[qwen35-npu]", fmt % args)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def _json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    global RUNTIME
    parser = argparse.ArgumentParser(description="Qwen3.5 inference service on Ascend NPU.")
    parser.add_argument("--model-path", required=True, help="Exported HuggingFace model directory")
    parser.add_argument("--model-name", default="Qwen3.5-0.8B")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    RUNTIME = Qwen35Runtime(args.model_path, args.model_name)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Qwen3.5 NPU server: http://{args.host}:{args.port}/api/qwen/generate")
    server.serve_forever()


if __name__ == "__main__":
    main()
