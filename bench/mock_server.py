"""Minimal OpenAI-compatible mock llama-server for unit tests.

Never used in a real run: it exists so the harness can be tested without a model.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


class MockLlamaServer:
    """Scripted responses for /v1/chat/completions plus a /props endpoint."""

    def __init__(
        self,
        script: list[str] | Callable[[dict], str],
        *,
        props: dict | None = None,
    ) -> None:
        self.script = script
        self.requests: list[dict] = []
        self.props = props or {
            "model_path": "mock.gguf",
            "chat_template": "{{ mock }}",
            "build_info": "mock-build-10288",
            "default_generation_settings": {"n_ctx": 8192},
        }
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> str:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # silence
                return

            def _send(self, payload: dict, status: int = 200) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                if self.path == "/props":
                    self._send(outer.props)
                elif self.path == "/v1/models":
                    self._send({"data": [{"id": "mock-model"}]})
                elif self.path == "/health":
                    self._send({"status": "ok"})
                else:
                    self._send({"error": "not found"}, 404)

            def do_POST(self):  # noqa: N802
                if self.path != "/v1/chat/completions":
                    self._send({"error": "not found"}, 404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                with outer._lock:
                    outer.requests.append(payload)
                    if callable(outer.script):
                        text = outer.script(payload)
                    else:
                        if len(outer.script) > 1:
                            text = outer.script.pop(0)
                        else:
                            text = outer.script[0] if outer.script else ""
                if isinstance(text, dict):
                    content = text.get("content", "")
                    reasoning = text.get("reasoning_content", "")
                else:
                    content, reasoning = text, ""
                self._send(
                    {
                        "id": "mock",
                        "object": "chat.completion",
                        "model": "mock-model",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": content,
                                    "reasoning_content": reasoning,
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 5,
                            "total_tokens": 15,
                        },
                    }
                )

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> "MockLlamaServer":
        self.base_url = self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
