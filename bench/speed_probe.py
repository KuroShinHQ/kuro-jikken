import json, sys, time

import requests

from bench.prompts import build_messages
from bench.props import PROPERTY_BY_KEY

effort = sys.argv[1] if len(sys.argv) > 1 else "low"
kwargs = {"enable_thinking": effort != "off"}
if effort not in {"off"}:
    kwargs["reasoning_effort"] = effort
msgs = build_messages("A", PROPERTY_BY_KEY["formula"], "c1ccccc1")
started = time.perf_counter()
response = requests.post(
    "http://127.0.0.1:8099/v1/chat/completions",
    json={
        "model": "local",
        "messages": msgs,
        "temperature": 0,
        "seed": 20261026,
        "max_tokens": 2048,
        "stream": False,
        "chat_template_kwargs": kwargs,
    },
    timeout=1200,
)
elapsed = time.perf_counter() - started
data = response.json()
message = data["choices"][0]["message"]
print(json.dumps({
    "effort": effort,
    "http": response.status_code,
    "seconds": round(elapsed, 2),
    "usage": data.get("usage"),
    "content": (message.get("content") or "")[:120],
    "reasoning_len": len(message.get("reasoning_content") or ""),
}, ensure_ascii=False))
