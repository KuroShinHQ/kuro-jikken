"""Preflight gate for the confirmatory run (Freeze 2).

Read-only. It never starts a server, never writes to the repository and never
touches ``runs/``. Every expected SHA-256 is read from
``prereg/freeze2_candidate.md`` so the document stays the single source of truth.

Checks, in order:

1. artefact hashes - model, template, server exe + dll, the four prompt files
   and the three ID lists;
2. git - working tree clean and HEAD pushed (``origin/main..HEAD`` = 0);
3. port 8099 free;
4. no forbidden process (Advanced SystemCare is a BLOCKER, everything else is a
   FAIL);
5. the power plan keeps the machine awake (standby AC timeout = 0);
6. free disk space on the repository drive;
7. ``docs/osf_freeze2_update_draft.md`` no longer contains
   ``[AUTHOR APPROVAL PENDING]``.

Exit code 0 only when every check is PASS; 2 otherwise.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Iterable

REPO = pathlib.Path(__file__).resolve().parents[1]
FREEZE = REPO / "prereg" / "freeze2_candidate.md"
DRAFT = REPO / "docs" / "osf_freeze2_update_draft.md"
DEFAULT_MODELS_DIR = pathlib.Path(r"C:\KuroshinHQ\_hub\models")
PORT = 8099
APPROVAL_PLACEHOLDER = "[AUTHOR APPROVAL PENDING]"
MIN_FREE_GB = 20.0

PASS = "PASS"
FAIL = "FAIL"
BLOCKER = "BLOCKER"

# process stem -> severity; anything in this table must not be running
FORBIDDEN_PROCESSES = {
    "ascservice": BLOCKER,
    "asctray": BLOCKER,
    "advanced systemcare": BLOCKER,
    "lm studio": FAIL,
    "lms": FAIL,
    "ollama": FAIL,
    "ollama_llama_server": FAIL,
    "llama-server": FAIL,
    "llama_server": FAIL,
    "razer cortex": FAIL,
    "razercortex": FAIL,
    "razercentralservice": FAIL,
    "razer synapse": FAIL,
}

ROW = re.compile(r"^\|\s*(?P<label>[^|]+?)\s*\|\s*`(?P<hash>[0-9a-fA-F]{64})`\s*\|\s*$")
AC_STANDBY = re.compile(r"Current AC Power Setting Index:\s*0x([0-9a-fA-F]+)")


@dataclass
class Result:
    name: str
    status: str
    detail: str


def _norm(text: str) -> str:
    return text.replace("`", "").strip()


def parse_rows(text: str) -> list[tuple[str, str]]:
    rows = []
    for line in text.splitlines():
        match = ROW.match(line.strip())
        if match:
            rows.append((_norm(match.group("label")), match.group("hash").lower()))
    return rows


def _one(rows: list[tuple[str, str]], predicate: Callable[[str], bool], what: str) -> str:
    hits = [value for label, value in rows if predicate(label)]
    if len(hits) != 1:
        raise ValueError(f"{what}: expected exactly one row in the freeze document, found {len(hits)}")
    return hits[0]


def parse_freeze(text: str) -> dict:
    """All frozen hashes, plus the paths that the document names itself."""
    rows = parse_rows(text)
    prompt_names = ["mode_a.txt", "mode_b.txt", "mode_c.txt", "question.txt"]
    plan = {
        "hashes": {
            "model": _one(rows, lambda label: label == "Model SHA-256", "model"),
            "template": _one(rows, lambda label: label == "Template SHA-256", "template"),
            "server_exe": _one(
                rows, lambda label: label == "llama-server.exe SHA-256", "server exe"
            ),
            "server_dll": _one(
                rows, lambda label: label == "llama-server-impl.dll SHA-256", "server dll"
            ),
        },
        "prompts": {
            name: _one(
                rows,
                lambda label, name=name: label.endswith(f"bench/prompts/{name}"),
                f"prompt {name}",
            )
            for name in prompt_names
        },
        "ids": {
            "ids_pilot.txt": _one(
                rows, lambda label: label.startswith("bench/data/ids_pilot.txt"), "ids_pilot"
            ),
            "ids_confirmatory.txt": _one(
                rows,
                lambda label: label.startswith("bench/data/ids_confirmatory.txt"),
                "ids_confirmatory",
            ),
            "ids_all.csv": _one(
                rows, lambda label: label.startswith("bench/data/ids_all.csv"), "ids_all"
            ),
        },
    }
    model_row = next(
        (match.group(0) for match in re.finditer(r"^\|\s*Model\s*\|.*$", text, re.M)), ""
    )
    name_match = re.search(r"`([^`]+\.gguf)`", model_row)
    if not name_match:
        raise ValueError("model file name not found in the freeze document")
    plan["model_name"] = name_match.group(1)

    template_row = next(
        (match.group(0) for match in re.finditer(r"^\|\s*Template\s*\|.*$", text, re.M)), ""
    )
    template_match = re.search(r"`([^`]+\.jinja)`", template_row)
    if not template_match:
        raise ValueError("template file name not found in the freeze document")
    plan["template_name"] = template_match.group(1)

    binary_row = next(
        (match.group(0) for match in re.finditer(r"^\|\s*Binary path\s*\|.*$", text, re.M)), ""
    )
    binary_match = re.search(r"`([^`]+llama-server\.exe)`", binary_row)
    if not binary_match:
        raise ValueError("server binary path not found in the freeze document")
    plan["server_path"] = pathlib.Path(binary_match.group(1))
    return plan


def artefact_list(plan: dict, models_dir: pathlib.Path) -> list[tuple[str, pathlib.Path, str]]:
    """(label, path, expected hash) for everything that has a frozen hash."""
    items = [
        ("model", models_dir / plan["model_name"], plan["hashes"]["model"]),
        ("template", models_dir / plan["template_name"], plan["hashes"]["template"]),
        ("llama-server.exe", plan["server_path"], plan["hashes"]["server_exe"]),
        (
            "llama-server-impl.dll",
            plan["server_path"].parent / "llama-server-impl.dll",
            plan["hashes"]["server_dll"],
        ),
    ]
    for name, expected in plan["prompts"].items():
        items.append((f"prompts/{name}", REPO / "bench" / "prompts" / name, expected))
    for name, expected in plan["ids"].items():
        items.append((f"data/{name}", REPO / "bench" / "data" / name, expected))
    return items


def check_artefacts(items: Iterable[tuple[str, pathlib.Path, str]], hasher) -> Result:
    bad, missing, done = [], [], []
    for label, path, expected in items:
        if not path.is_file():
            missing.append(f"{label} ({path})")
            continue
        actual = hasher(path)
        if actual.lower() != expected.lower():
            bad.append(f"{label}: {actual.lower()} != {expected.lower()}")
        else:
            done.append(label)
    if missing or bad:
        return Result(
            "artefact hashes",
            FAIL,
            f"{len(done)} ok, {len(missing)} missing, {len(bad)} mismatched"
            + ("; missing: " + ", ".join(missing) if missing else "")
            + ("; mismatched: " + "; ".join(bad) if bad else ""),
        )
    return Result("artefact hashes", PASS, f"{len(done)}/{len(done)} match the freeze document")


def check_git(status_porcelain: str, unpushed: int) -> Result:
    dirty = [line for line in status_porcelain.splitlines() if line.strip()]
    problems = []
    if dirty:
        problems.append(f"{len(dirty)} uncommitted path(s): " + ", ".join(dirty[:5]))
    if unpushed:
        problems.append(f"{unpushed} commit(s) not pushed (KABUL missing)")
    if problems:
        return Result("git clean and pushed", FAIL, "; ".join(problems))
    return Result("git clean and pushed", PASS, "worktree clean, origin/main == HEAD")


def check_port(free: bool) -> Result:
    if free:
        return Result(f"port {PORT} free", PASS, f"nothing listens on 127.0.0.1:{PORT}")
    return Result(f"port {PORT} free", FAIL, f"127.0.0.1:{PORT} is taken")


def check_processes(names: Iterable[str]) -> Result:
    running = {}
    for raw in names:
        stem = raw.lower().removesuffix(".exe").strip()
        if stem in FORBIDDEN_PROCESSES:
            running.setdefault(FORBIDDEN_PROCESSES[stem], []).append(stem)
    if not running:
        return Result("forbidden processes", PASS, "none running")
    parts = []
    status = PASS
    if BLOCKER in running:
        status = BLOCKER
        parts.append("BLOCKER: " + ", ".join(sorted(set(running[BLOCKER]))))
    if FAIL in running:
        if status == PASS:
            status = FAIL
        parts.append("forbidden: " + ", ".join(sorted(set(running[FAIL]))))
    return Result("forbidden processes", status, "; ".join(parts))


def check_power(query_output: str) -> Result:
    match = AC_STANDBY.search(query_output)
    if not match:
        return Result(
            "power plan awake", FAIL, "standby AC timeout not found in powercfg output"
        )
    seconds = int(match.group(1), 16)
    if seconds == 0:
        return Result("power plan awake", PASS, "AC standby timeout = 0 (never sleeps)")
    return Result(
        "power plan awake",
        FAIL,
        f"AC standby timeout = {seconds} s; set it to 0 before an overnight run",
    )


def check_disk(free_bytes: int, minimum_gb: float = MIN_FREE_GB) -> Result:
    free_gb = free_bytes / (1024**3)
    status = PASS if free_gb >= minimum_gb else FAIL
    return Result(
        "disk space",
        status,
        f"{free_gb:.1f} GB free (minimum {minimum_gb:.0f} GB)",
    )


def check_approval(draft_text: str) -> Result:
    if APPROVAL_PLACEHOLDER in draft_text:
        return Result(
            "author approval", FAIL, f"draft still contains {APPROVAL_PLACEHOLDER}"
        )
    if "The author approves" not in draft_text:
        return Result(
            "author approval", FAIL, "no approval sentence in the draft"
        )
    return Result("author approval", PASS, "approval sentence present, placeholder gone")


def run_checks(plan: dict, models_dir: pathlib.Path, system) -> list[Result]:
    results = [
        check_artefacts(artefact_list(plan, models_dir), system.sha256),
        check_git(system.git_status(), system.git_unpushed()),
        check_port(system.port_free(PORT)),
        check_processes(system.process_names()),
        check_power(system.power_standby_ac()),
        check_disk(system.disk_free(REPO)),
        check_approval(system.read_text(DRAFT)),
    ]
    return results


class RealSystem:
    """Read-only access to the machine."""

    @staticmethod
    def sha256(path: pathlib.Path) -> str:
        import hashlib

        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _run(args: list[str], encoding: str | None = None) -> tuple[int, str, str]:
        import locale

        completed = subprocess.run(args, capture_output=True, check=False)
        codec = encoding or locale.getpreferredencoding(False)
        return (
            completed.returncode,
            completed.stdout.decode(codec, errors="replace"),
            completed.stderr.decode(codec, errors="replace"),
        )

    @staticmethod
    def _git(*args: str) -> str:
        code, out, err = RealSystem._run(
            ["git", "-C", str(REPO), *args], encoding="utf-8"
        )
        if code != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {err.strip()}")
        return out

    def git_status(self) -> str:
        return self._git("status", "--porcelain")

    def git_unpushed(self) -> int:
        return int(self._git("rev-list", "--count", "origin/main..HEAD").strip() or 0)

    @staticmethod
    def port_free(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", port)) != 0

    @staticmethod
    def process_names() -> list[str]:
        _, out, _ = RealSystem._run(["tasklist", "/fo", "csv", "/nh"])
        names = []
        for line in out.splitlines():
            if line.startswith('"'):
                names.append(line.split('","')[0].strip('"'))
        return names

    @staticmethod
    def power_standby_ac() -> str:
        _, out, _ = RealSystem._run(
            ["powercfg", "/query", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"]
        )
        return out

    @staticmethod
    def disk_free(path: pathlib.Path) -> int:
        return shutil.disk_usage(path).free

    @staticmethod
    def read_text(path: pathlib.Path) -> str:
        return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze 2 confirmatory preflight (read-only)")
    parser.add_argument(
        "--models-dir", default=str(DEFAULT_MODELS_DIR), help="directory holding model + template"
    )
    args = parser.parse_args(argv)

    try:
        plan = parse_freeze(FREEZE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"PREFLIGHT could not read the freeze document: {exc}")
        return 2

    try:
        results = run_checks(plan, pathlib.Path(args.models_dir), RealSystem())
    except Exception as exc:  # a check that cannot be evaluated is a failure
        print(f"PREFLIGHT error: {exc}")
        return 2

    width = max(len(result.name) for result in results)
    for result in results:
        print(f"{result.name.ljust(width)}  {result.status:<8} {result.detail}")
    blocking = [result for result in results if result.status != PASS]
    print()
    if blocking:
        print(f"PREFLIGHT: {len(blocking)} check(s) not passing -> do NOT start BASLAT")
        return 2
    print("PREFLIGHT: all checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
