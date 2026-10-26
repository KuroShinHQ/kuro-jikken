"""Append-only JSONL logging under ``runs/`` (prereg sections 5 and README rule 4.2)."""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class JsonlLogger:
    """One file per run; every write appends one line and never rewrites."""

    def __init__(self, path: pathlib.Path | str) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict) -> dict:
        record = dict(record)
        record.setdefault("logged_at", utc_now())
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
        with open(self.path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        return record

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
