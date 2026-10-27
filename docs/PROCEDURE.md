# Procedure lane (`kj-recipe/1`)

An engine answers a property question with a number. A procedure answers a
*doing* question ("what do I actually do at home?") with an ordered document.
The failure mode is different: a paragraph that sounds medical. This lane exists
so that a procedure can be shipped **without** pretending to be an engine or a
clinician.

## What the gate checks (`mcp/recipe.py`)

| Check | Rule |
|---|---|
| sources | every source has `id`, `title`, `url`, `accessed`, `licence`; ids are unique and **all used** |
| attribution | every ingredient and step names a source id or the literal `design` |
| temperature | `temperature_role: setpoint` may be `design`; `limit` must cite a source |
| medical claim | cure/treat/prevent verbs outside `claim_boundary`/`does_not_say` are refused; negation is allowed ("not a medicine") |
| reaction | a declared equation must be atom-balanced (own parser, 118 elements) |
| translation | `tr.steps/safety/does_not_say` must have the same length as the English |
| boundary | `claim_boundary` and `does_not_say` are mandatory and printed verbatim |

`design` is not a source. It is an explicit statement that the number is a
choice of this recipe (a 5-minute steep), not a measured fact.

## Commands

```powershell
.venv_inventory\Scripts\python.exe mcp\recipe.py data\recipes\mint_lemon.json
.venv_inventory\Scripts\python.exe mcp\recipe.py data\recipes\mint_lemon.json --markdown
.venv_inventory\Scripts\python.exe mcp\recipe.py data\recipes\*.json --check-urls   # network, report only
.venv_inventory\Scripts\python.exe tools\recipe_page.py --all
.venv_inventory\Scripts\python.exe tools\recipe_page.py --all --check               # exit 1 on a stale page
```

The same gate is on the MCP surface: `kj_recipe(recipe, markdown=False, check_http=False)`
in `mcp/tools_server.py` (`kj-tools`, 10 tools). `recipe` is a path or the document
itself; a bad document comes back as `{"verdict": "RED", "reason": ...}`, not as an
exception, and the tool never returns a chemistry number.

The page generator embeds the whole JSON (`const R = ...; // kj-recipe-json`), so
the page and the gated document cannot drift. `--check` compares the generated
bytes with the file on disk.

## The two demos

| id | kind | question it answers | what it refuses |
|---|---|---|---|
| `mint-lemon-warm-drink` | food | how to make a warm mint-lemon drink | that it cures a cold/flu; a vitamin C dose |
| `silver-tarnish-cell` | household-chemistry | how to remove silver sulfide tarnish with foil, soda and hot water | that it repairs scratches/plating or makes an item food-safe |

Both pages show the step's temperature as a **target** (or a cited **limit**),
never as a measurement. The break button asks for a medical claim and gets the
fixed refusal sentence with an em dash.

## Evidence

* `pytest mcp/tests/test_recipe.py tools/tests/test_recipe_page.py -q` -> 18 passed
* `pytest mcp/tests/test_tools_server.py -q` (inventory env) -> 15 passed, including
  the three `kj_recipe` tests (PASS, document-as-dict, RED-is-a-result)
* `tools/recipe_page.py --all --check` -> exit 0, `stale: false` for both
* live MCP handshake (`tools/list`) -> **10 tools**, `kj_recipe` among them; a call
  with `mint_lemon.json` returns `PASS`
* `shot.mjs` on both pages -> mint 54 parts / 27 356 tris / 61 fps, silver
  25 parts / 16 086 tris / 61 fps; PNGs in `%TEMP%\opencode\labshots\`
* `--check-urls` (2026-10-27): 6 fetches HTTP 200 (NIST, IARC, WHO x2, LibreTexts,
  UW-Madison); CDC x2 and NIOSH 403 (bot wall); Canada.ca timeout twice (30/45 s).
  The page keeps the citation and the reader opens it by hand.
* full consistency report: `docs/RECIPE_VALIDATION.md`

## What this lane does not do

It does not generate a procedure from free text. The document is authored, then
gated; the LLM may draft it, but it cannot bypass `validate()`. There is no
toxicity/ADMET, no TEWL, no binding, no medical advice: those stay RED.
