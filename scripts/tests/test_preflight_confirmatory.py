"""Unit tests for scripts/preflight_confirmatory.py (fakes only; read-only)."""

from __future__ import annotations

import hashlib
import pathlib

import pytest

from scripts import preflight_confirmatory as preflight
from scripts.preflight_confirmatory import (
    BLOCKER,
    FAIL,
    PASS,
    Result,
    check_approval,
    check_artefacts,
    check_disk,
    check_git,
    check_port,
    check_power,
    check_processes,
    parse_freeze,
    parse_rows,
    run_checks,
)

FREEZE_TEXT = """# Freeze 2 candidate

| item | value |
|---|---|
| Model | `model-x.gguf` |
| Model bytes | 18,339,420,608 |
| Model SHA-256 | `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` |
| Template | `qwen-fixed-chat-template.jinja` |
| Template SHA-256 | `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` |
| Binary path | `C:\\engines\\llama-server.exe` |
| `llama-server.exe` SHA-256 | `cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc` |
| `llama-server-impl.dll` SHA-256 | `dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd` |

## 3. Prompt files (SHA-256)

| file | SHA-256 |
|---|---|
| `bench/prompts/mode_a.txt` | `1111111111111111111111111111111111111111111111111111111111111111` |
| `bench/prompts/mode_b.txt` | `2222222222222222222222222222222222222222222222222222222222222222` |
| `bench/prompts/mode_c.txt` | `3333333333333333333333333333333333333333333333333333333333333333` |
| `bench/prompts/question.txt` | `4444444444444444444444444444444444444444444444444444444444444444` |

## 4. Molecule ID lists

| file | SHA-256 |
|---|---|
| `bench/data/ids_pilot.txt` (50) | `5555555555555555555555555555555555555555555555555555555555555555` |
| `bench/data/ids_confirmatory.txt` (200) | `6666666666666666666666666666666666666666666666666666666666666666` |
| `bench/data/ids_all.csv` (250) | `7777777777777777777777777777777777777777777777777777777777777777` |
"""


def test_parse_freeze_extracts_every_frozen_artefact():
    plan = parse_freeze(FREEZE_TEXT)
    assert plan["model_name"] == "model-x.gguf"
    assert plan["template_name"] == "qwen-fixed-chat-template.jinja"
    assert plan["hashes"]["model"] == "a" * 64
    assert plan["hashes"]["server_exe"] == "c" * 64
    assert len(plan["prompts"]) == 4
    assert len(plan["ids"]) == 3


def test_parse_rows_ignores_rows_without_a_hash():
    rows = parse_rows("| Model | `model.gguf` |\n| Model bytes | 123 |\n| x | `" + "a" * 64 + "` |")
    assert rows == [("x", "a" * 64)]


def test_parse_freeze_rejects_a_missing_row():
    broken = FREEZE_TEXT.replace("| `llama-server.exe` SHA-256 |", "| something |")
    with pytest.raises(ValueError):
        parse_freeze(broken)


def test_real_freeze_document_parses():
    """The committed document must stay parseable by the gate."""
    plan = parse_freeze(preflight.FREEZE.read_text(encoding="utf-8"))
    assert len(plan["prompts"]) == 4 and len(plan["ids"]) == 3


def _file(tmp_path: pathlib.Path, name: str, content: bytes) -> tuple[pathlib.Path, str]:
    path = tmp_path / name
    path.write_bytes(content)
    return path, hashlib.sha256(content).hexdigest()


def test_check_artefacts_all_match(tmp_path):
    path, digest = _file(tmp_path, "a.bin", b"payload")
    result = check_artefacts([("a.bin", path, digest)], preflight.RealSystem.sha256)
    assert result.status == PASS


def test_check_artefacts_detects_a_mismatch(tmp_path):
    path, _ = _file(tmp_path, "a.bin", b"payload")
    result = check_artefacts([("a.bin", path, "0" * 64)], preflight.RealSystem.sha256)
    assert result.status == FAIL
    assert "mismatched" in result.detail


def test_check_artefacts_detects_a_missing_file(tmp_path):
    result = check_artefacts(
        [("gone.bin", tmp_path / "gone.bin", "0" * 64)], preflight.RealSystem.sha256
    )
    assert result.status == FAIL
    assert "missing" in result.detail


def test_check_git_clean_and_pushed():
    assert check_git("", 0).status == PASS


def test_check_git_dirty():
    result = check_git(" M docs/x.md\n?? new.py\n", 0)
    assert result.status == FAIL
    assert "uncommitted" in result.detail


def test_check_git_unpushed():
    result = check_git("", 8)
    assert result.status == FAIL
    assert "KABUL" in result.detail


def test_check_port():
    assert check_port(True).status == PASS
    assert check_port(False).status == FAIL


def test_check_processes_none():
    assert check_processes(["explorer.exe", "python.exe"]).status == PASS


def test_check_processes_asc_is_a_blocker():
    result = check_processes(["ASCService.exe", "ASCTray.exe"])
    assert result.status == BLOCKER


def test_check_processes_llama_server_is_a_fail():
    assert check_processes(["llama-server.exe"]).status == FAIL


def test_check_processes_blocker_wins():
    result = check_processes(["llama-server.exe", "ASCTray.exe"])
    assert result.status == BLOCKER
    assert "llama-server" in result.detail


def test_check_power_awake():
    text = "Current AC Power Setting Index: 0x00000000\nCurrent DC Power Setting Index: 0x00000384"
    assert check_power(text).status == PASS


def test_check_power_sleeps():
    result = check_power("Current AC Power Setting Index: 0x00000708")
    assert result.status == FAIL
    assert "1800" in result.detail


def test_check_power_unparseable_fails_closed():
    assert check_power("no such setting").status == FAIL


def test_check_disk():
    assert check_disk(50 * 1024**3).status == PASS
    assert check_disk(2 * 1024**3).status == FAIL


def test_check_approval_pending():
    result = check_approval("## Author approval\n\n[AUTHOR APPROVAL PENDING]\n\nnothing approved")
    assert result.status == FAIL
    assert "PENDING" in result.detail


def test_check_approval_given():
    result = check_approval(
        "## Author approval\n\nThe author approves these four decisions as of 2026-10-26."
    )
    assert result.status == PASS


def test_check_approval_missing_sentence_fails():
    assert check_approval("no approval here").status == FAIL


class FakeSystem:
    def __init__(self, **overrides):
        self.hashes = overrides.pop("hashes", {})
        self.status = overrides.pop("status", "")
        self.unpushed = overrides.pop("unpushed", 0)
        self.port_is_free = overrides.pop("port_free", True)
        self.names = overrides.pop("names", ())
        self.power = overrides.pop("power", "Current AC Power Setting Index: 0x00000000")
        self.free = overrides.pop("free", 50 * 1024**3)
        self.draft = overrides.pop("draft", "The author approves these four decisions.")
        if overrides:
            raise TypeError(f"unexpected overrides: {sorted(overrides)}")

    def sha256(self, path):
        return self.hashes[str(path)]

    def git_status(self):
        return self.status

    def git_unpushed(self):
        return self.unpushed

    def port_free(self, port):
        return self.port_is_free

    def process_names(self):
        return self.names

    def power_standby_ac(self):
        return self.power

    def disk_free(self, path):
        return self.free

    def read_text(self, path):
        return self.draft


def _plan(tmp_path):
    items = {}
    entries = []
    for index, (label, name) in enumerate(
        [
            ("model", "model-x.gguf"),
            ("template", "qwen.jinja"),
            ("exe", "llama-server.exe"),
            ("dll", "llama-server-impl.dll"),
            ("prompt_a", "mode_a.txt"),
            ("prompt_b", "mode_b.txt"),
            ("prompt_c", "mode_c.txt"),
            ("prompt_q", "question.txt"),
            ("ids_pilot", "ids_pilot.txt"),
            ("ids_conf", "ids_confirmatory.txt"),
            ("ids_all", "ids_all.csv"),
        ]
    ):
        path, digest = _file(tmp_path, name, f"content-{index}".encode())
        items[str(path)] = digest
        entries.append((label, path, digest))
    return items, entries


def test_run_checks_all_pass(tmp_path, monkeypatch):
    items, entries = _plan(tmp_path)
    monkeypatch.setattr(preflight, "artefact_list", lambda plan, models_dir: entries)
    results = run_checks({}, tmp_path, FakeSystem(hashes=items))
    assert [result.status for result in results] == [PASS] * len(results)


def test_run_checks_blocker_and_failures(tmp_path, monkeypatch):
    items, entries = _plan(tmp_path)
    monkeypatch.setattr(preflight, "artefact_list", lambda plan, models_dir: entries)
    system = FakeSystem(
        hashes=items,
        status=" M x",
        unpushed=8,
        port_free=False,
        names=["ASCService.exe"],
        power="Current AC Power Setting Index: 0x00000384",
        free=1024**3,
        draft="[AUTHOR APPROVAL PENDING]",
    )
    results = {result.name: result.status for result in run_checks({}, tmp_path, system)}
    assert results["git clean and pushed"] == FAIL
    assert results["port 8099 free"] == FAIL
    assert results["forbidden processes"] == BLOCKER
    assert results["power plan awake"] == FAIL
    assert results["disk space"] == FAIL
    assert results["author approval"] == FAIL


def test_main_exit_codes(monkeypatch):
    monkeypatch.setattr(preflight, "parse_freeze", lambda text: {})
    monkeypatch.setattr(preflight, "run_checks", lambda plan, models, system: [Result("x", PASS, "")])
    assert preflight.main(["--models-dir", "."]) == 0

    monkeypatch.setattr(
        preflight,
        "run_checks",
        lambda plan, models, system: [Result("x", PASS, ""), Result("y", BLOCKER, "asc")],
    )
    assert preflight.main(["--models-dir", "."]) == 2


def test_main_fails_closed_when_the_freeze_document_is_unreadable(monkeypatch, tmp_path):
    monkeypatch.setattr(preflight, "FREEZE", tmp_path / "missing.md")
    assert preflight.main(["--models-dir", "."]) == 2
