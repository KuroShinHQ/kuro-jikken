# kuro-jikken — Deney deck (faz-pipeline in-silico arastirma hatti)

![Status](https://img.shields.io/badge/status-skeleton-blue) ![License](https://img.shields.io/badge/license-private-lightgrey)

Kuro-Jikken is the research side of the KuroShinHQ ecosystem: a staged pipeline that
turns chat-driven research hypotheses into **verifiable in-silico experiments**
(computation -> molecular simulation -> bio/system modelling) and publishes the
results as clean, reproducible docs.

## Features
- Staged FAZ pipeline (F1 computation, F2 molecular sim, F3 bio/system, F4 research-agent)
- Evidence-first working rules (kanit zorunlu), Q&A decision flow
- Rich TUI control deck with EN/TR, boot animation and auto-close exit
- BAT-15.1 standard launcher set (single bat + go.ps1 + uninstall)

## Tech Stack
- Python 3.10+ (rich TUI), PowerShell bootstrap (go.ps1)
- opencode + MCP integration (research side; planned: RDKit, fairchem, aizynthfinder, Talk2Biomodels ...) — tools are chosen per phase by research, not fixed

## Installation
```bash
git clone https://github.com/KuroShinHQ/kuro-jikken.git
cd kuro-jikken
# Windows: double-click kuro-jikken.bat  (or: powershell -File script\go.ps1)
```

## Usage
Run `kuro-jikken.bat`, pick a phase in the menu; results and evidence land in
`docs/` and `logs/`. Language preference is remembered in `.lang` (EN default).

## Folder structure
| Path | Content |
|------|---------|
| `site/kuro_jikken_menu.py` | TUI control deck (boot / menu / exit screens) |
| `script/go.ps1` | bootstrap: python/deps/menu start |
| `script/uninstall.ps1` | modular uninstall |
| `docs/` | research notes (published subset) |

## License & Rules
Private KuroShinHQ repo. No paid tools; fully local-first. Evidence rules
(DEVAM.md SABIT KURALLAR) apply: no claim without proof; commit/push require
explicit user approval. GIF demo (`docs/img/readme_demo.gif`) and menu photo are
scheduled right after the first functional phase.
