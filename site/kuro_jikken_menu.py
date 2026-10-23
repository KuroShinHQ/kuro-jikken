"""
Kuro-Jikken TUI Control Deck (skeleton) — BAT-15.10 3-ekran standardi.

Ekran-1: boot animasyonu + health-check
Ekran-2: ana menu (fazlar + dil + cikis)
Ekran-3: temiz kapanis paneli (auto-close)
Her eylem logger'a yazilir (cmd olse bile kayit kalir).
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

CONSOLE = Console()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(ROOT, "logs", "kuro_jikken.log")
LANG_FILE = os.path.join(ROOT, ".lang")

STR = {
    "en": {
        "boot": "Kuro-Jikken boot animation",
        "soul": "claim -> evidence -> publication | can an LLM act like a scientist?",
        "menu_title": "Kuro-Jikken Control Deck",
        "faz1": "FAZ 1 - Basic computation (RDKit)",
        "faz2": "FAZ 2 - Molecular simulation",
        "faz3": "FAZ 3 - Bio / system",
        "faz4": "FAZ 4 - Research agent",
        "m5": "Language FR",
        "exit": "Exit",
        "wip": "Skeleton: this phase opens in a later commit.",
        "bye": "Screen-3: clean exit. See you at the next phase.",
        "lang_q": "Language (en/tr)",
    },
    "tr": {
        "boot": "Kuro-Jikken baslama animasyonu",
        "soul": "iddia -> kanit -> yayin | LLM bilim insani gibi calisabilir mi?",
        "menu_title": "Kuro-Jikken Kumanda Merkezi",
        "faz1": "FAZ 1 - Basit hesaplama (RDKit)",
        "faz2": "FAZ 2 - Molekuler simulasyon",
        "faz3": "FAZ 3 - Biyo/sistem",
        "faz4": "FAZ 4 - Research agent",
        "m5": "Dil secimi",
        "exit": "Cikis",
        "wip": "Iskelet: bu faz sonraki commit'te aciliyor.",
        "bye": "Ekran-3: temiz kapanis. Sonraki fazda gorusuruz.",
        "lang_q": "Dil (en/tr)",
    },
}


def log(msg: str) -> None:
    """Logger zorunlulugu: her eylem jurnale yazilir (module disi durumda bile)."""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}\n")
    except OSError:
        pass


def load_lang() -> str:
    lang = "en"
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, encoding="utf-8") as f:
                val = f.read().strip().lower()
                lang = val if val in ("en", "tr") else "en"
        except OSError:
            lang = "en"
    return lang


def save_lang(lang: str) -> None:
    with open(LANG_FILE, "w", encoding="utf-8") as f:
        f.write(lang)


def ekran1_boot(t: dict) -> None:
    """Boot animasyonu + health-check tablosu."""
    CONSOLE.print(Text("kuro-jikken", style="bold cyan"), justify="center")
    CONSOLE.print(Text("deney deck - faz pipeline", style="dim"), justify="center")
    CONSOLE.print(Text(t["soul"], style="dim italic"), justify="center")
    for ch in r"/-\\|/-\\|":
        CONSOLE.print(f"  [{ch}]", end="\r")
        time.sleep(0.05)
    CONSOLE.print(" ")
    tbl = Table(title=t["boot"], border_style="dim")
    tbl.add_column("check", min_width=34)
    tbl.add_column("result")
    tbl.add_row("python", f"{sys.version_info.major}.{sys.version_info.minor}")
    try:
        import rich  # noqa: F401
        tbl.add_row("rich", "OK")
    except ImportError:
        tbl.add_row("rich", "MISSING (pip install -r requirements.txt)")
    tbl.add_row("mode", "local-only / zeroprofile")
    CONSOLE.print(tbl)
    log("boot OK")


def ekran2_menu(t: dict) -> str:
    """Ana menu: faz secimleri + dil + cikis."""
    tbl = Table.grid()
    rows = ["faz1", "faz2", "faz3", "faz4"]
    keys = ["1", "2", "3", "4"]
    for k, r in zip(keys, rows):
        tbl.add_row(f"[bold]{k}[/bold]", t[r])
    tbl.add_row("[bold]5[/bold]", t["m5"])
    tbl.add_row("[bold]q[/bold]", t["exit"])
    CONSOLE.print(Panel(tbl, title=t["menu_title"], border_style="cyan"))
    choice = Prompt.ask("secim", choices=["1", "2", "3", "4", "5", "q"], show_choices=False)
    return choice


def ekran3_exit(t: dict) -> None:
    CONSOLE.print(Panel(Text(t["bye"], style="green"), border_style="green"))
    log("exit")


def main() -> int:
    lang = "en"
    t = STR[lang]
    ekran1_boot(t)
    while True:
        choice = ekran2_menu(t)
        log(f"menu secim={choice}")
        if choice == "q":
            ekran3_exit(t)
            return 0
        if choice == "5":
            yeni = Prompt.ask(t["lang_q"], choices=["en", "tr"], default=lang)
            if yeni != lang:
                lang = yeni
                t = STR[lang]
                save_lang(lang)
                log(f"lang={lang}")
            continue
        # fazlar: iskelet — sonraki commit'te acilir (B11 placeholder)
        CONSOLE.print(Panel(Text(t["wip"], style="yellow"), border_style="yellow"))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("keyboard-interrupt exit")
        sys.exit(0)
