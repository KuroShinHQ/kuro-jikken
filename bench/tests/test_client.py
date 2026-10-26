from __future__ import annotations

import pytest

from bench.llama_client import (
    LlamaClient,
    PortGuardError,
    runtime_fingerprint,
    sha256_file,
)
from bench.mock_server import MockLlamaServer


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:1234",
        "https://127.0.0.1:8099",
        "http://192.168.1.10:8099",
        "http://example.com:8099",
    ],
)
def test_port_and_host_guards(url):
    with pytest.raises(PortGuardError):
        LlamaClient(url)


def test_default_port_is_allowed():
    client = LlamaClient("http://127.0.0.1:8099")
    assert client.base_url == "http://127.0.0.1:8099"


def test_chat_parameters_and_props():
    with MockLlamaServer(['{"answer": 1}'], props={"model_path": "mock.gguf"}) as server:
        client = LlamaClient(server.base_url, require_port_8099=False)
        response = client.chat(
            [{"role": "user", "content": "x"}], temperature=0.0, seed=42, max_tokens=64
        )
        assert response.text == '{"answer": 1}'
        assert response.usage["total_tokens"] == 15
        payload = server.requests[0]
        assert payload["temperature"] == 0.0
        assert payload["seed"] == 42
        assert payload["max_tokens"] == 64
        assert payload["stream"] is False
        assert client.props()["model_path"] == "mock.gguf"


def test_reasoning_is_kept_separate():
    with MockLlamaServer(
        [{"content": '{"answer": 1}', "reasoning_content": "thinking..."}]
    ) as server:
        client = LlamaClient(server.base_url, require_port_8099=False)
        response = client.chat([{"role": "user", "content": "x"}])
        assert response.text == '{"answer": 1}'
        assert response.reasoning == "thinking..."


def test_runtime_fingerprint_hashes_existing_model_file(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"weights")
    props = {"model_path": str(model), "chat_template": "{{ x }}", "build_info": "b1"}
    info = runtime_fingerprint(props)
    assert info["model_sha256"] == sha256_file(model)
    assert info["build_info"] == "b1"
    assert info["chat_template_sha256"]
    assert runtime_fingerprint({"model_path": "missing.gguf"})["model_sha256"] is None
