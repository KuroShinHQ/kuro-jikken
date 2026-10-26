"""OpenAI-compatible client for the one local llama-server on port 8099.

Guards (prereg section 3.3 / task instruction):
* loopback host only, port 8099 by default, 8080/8081 always refused;
* no redirects are followed, so a local endpoint cannot bounce the request out;
* no retries here - the caller decides, and every call is logged by the caller.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8099"
FORBIDDEN_PORTS = {8080, 8081}
DEFAULT_PORT = 8099


class PortGuardError(ValueError):
    pass


@dataclass
class LlamaResponse:
    text: str
    reasoning: str
    raw: dict
    model: str
    usage: dict
    http_ms: float

    def to_log(self) -> dict:
        return {
            "text": self.text,
            "reasoning": self.reasoning,
            "model": self.model,
            "usage": self.usage,
            "http_ms": round(self.http_ms, 3),
        }


def sha256_file(path: pathlib.Path | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LlamaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 900.0,
        require_port_8099: bool = True,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "http":
            raise PortGuardError(f"only http is allowed, got {parsed.scheme!r}")
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise PortGuardError(f"only loopback is allowed, got {parsed.hostname!r}")
        port = parsed.port or 80
        if port in FORBIDDEN_PORTS:
            raise PortGuardError(f"port {port} is forbidden")
        if require_port_8099 and port != DEFAULT_PORT:
            raise PortGuardError(f"only port {DEFAULT_PORT} is allowed, got {port}")
        self.base_url = f"http://{parsed.hostname}:{port}"
        self.timeout = timeout
        self._session = requests.Session()
        self._session.trust_env = False  # ignore proxy environment variables

    # -- read-only endpoints -------------------------------------------------
    def _get(self, path: str) -> dict:
        response = self._session.get(
            self.base_url + path, timeout=self.timeout, allow_redirects=False
        )
        if response.status_code != 200:
            raise RuntimeError(f"GET {path} -> {response.status_code}: {response.text[:300]}")
        return response.json()

    def props(self) -> dict:
        return self._get("/props")

    def models(self) -> dict:
        return self._get("/v1/models")

    def health(self) -> bool:
        try:
            self._get("/health")
            return True
        except Exception:
            return False

    # -- generation ----------------------------------------------------------
    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.0,
        seed: int = 20261026,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
        chat_template_kwargs: dict | None = None,
    ) -> LlamaResponse:
        payload: dict[str, Any] = {
            "model": "local",
            "messages": messages,
            "temperature": temperature,
            "seed": seed,
            "max_tokens": max_tokens,
            "stream": False,
            "cache_prompt": True,
        }
        if stop:
            payload["stop"] = stop
        if chat_template_kwargs is not None:
            payload["chat_template_kwargs"] = chat_template_kwargs
        started = _now()
        response = self._session.post(
            self.base_url + "/v1/chat/completions",
            json=payload,
            timeout=self.timeout,
            allow_redirects=False,
        )
        elapsed = (_now() - started) * 1000.0
        if response.status_code != 200:
            raise RuntimeError(
                f"POST /v1/chat/completions -> {response.status_code}: {response.text[:400]}"
            )
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        text = message.get("content") or ""
        reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
        return LlamaResponse(
            text=text,
            reasoning=reasoning,
            raw=data,
            model=data.get("model", ""),
            usage=data.get("usage") or {},
            http_ms=elapsed,
        )


def runtime_fingerprint(props: dict, model_path: str | None = None) -> dict:
    """What Freeze 2 needs about the server, without guessing."""
    path = model_path or props.get("model_path")
    info = {
        "model_path": path,
        "model_sha256": None,
        "props_keys": sorted(props),
        "chat_template_sha256": None,
        "build_info": props.get("build_info") or props.get("build"),
    }
    if path and pathlib.Path(path).is_file():
        info["model_sha256"] = sha256_file(path)
    template = props.get("chat_template")
    if isinstance(template, str) and template:
        info["chat_template_sha256"] = hashlib.sha256(template.encode("utf-8")).hexdigest()
    return info


def _now() -> float:
    import time

    return time.perf_counter()


__all__ = [
    "DEFAULT_BASE_URL",
    "LlamaClient",
    "LlamaResponse",
    "PortGuardError",
    "runtime_fingerprint",
    "sha256_file",
]
