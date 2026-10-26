"""Prompt files and message builders (frozen text lives in ``bench/prompts/``)."""

from __future__ import annotations

import hashlib
import pathlib

from bench.props import Property

PROMPT_DIR = pathlib.Path(__file__).resolve().parent / "prompts"


def _read(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def system_prompt(mode: str) -> str:
    if mode not in {"A", "B", "C"}:
        raise ValueError(f"unknown mode: {mode}")
    return _read(f"mode_{mode.lower()}.txt")


def question_text(prop: Property, smiles: str) -> str:
    return _read("question.txt").format(
        smiles=smiles,
        label=prop.label,
        definition=prop.definition,
        format_hint=prop.format_hint,
    )


def build_messages(mode: str, prop: Property, smiles: str) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt(mode)},
        {"role": "user", "content": question_text(prop, smiles)},
    ]


def prompt_hashes() -> dict[str, str]:
    """SHA-256 of every prompt file (for Freeze 2)."""
    hashes = {}
    for path in sorted(PROMPT_DIR.glob("*.txt")):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes
