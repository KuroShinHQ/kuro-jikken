# P1 validation - two questions, end to end

**Date:** 2026-10-27. **Lane:** procedure (`kj-recipe/1`). **Question under test:**
does the pipeline answer a real person's "what do I do at home?" question in a way
that is *close to the science* and *honest about what it is not*?

The lane is deliberately different from the engine lanes: it produces **no number**
and no medical claim. The number lanes stay separate (`kj_ask`); here the output is
an ordered document with a boundary.

## The two questions

| # | field | question as a person asks it | document |
|---|---|---|---|
| 1 | biology / food | "I have a cold and want to make something at home" | `data/recipes/mint_lemon.json` (`mint-lemon-warm-drink`) |
| 2 | chemistry / household | "how do I get the tarnish off silver?" | `data/recipes/silver_tarnish.json` (`silver-tarnish-cell`) |

## The chain, per question

```
question -> recipe lane (no engine number) -> kj-recipe/1 gate
         -> markdown answer (sources inline) -> three.js page -> PNG
```

The gate checks the source ids, the mandatory claim boundary, the atom balance of
a declared equation and the Turkish mirror. It refuses a document that cannot be
checked; it never computes chemistry.

## Every number, its role and its source

| document | number | role | source |
|---|---|---|---|
| mint-lemon | 100 °C | setpoint (boiling) | `nist-water` |
| mint-lemon | 65 °C | **limit** (drink temperature) | `iarc-2016` |
| mint-lemon | 5 / 2 / 1 min | design | `design` |
| mint-lemon | 200 ml / 5 g / 2 slices / 5 g | design | `design` |
| silver | 80 °C | setpoint (hot water) | `uw-madison` |
| silver | 10 min | design | `design` |
| silver | 10 g / 500 ml / 1 sheet | design | `design` |

Rule enforced in code: a temperature used as a **limit** must cite a source; a
setpoint may be `design`. `design` is not a source - it says "this is a choice of
this recipe, not a measured fact".

## Cross-checks (independent of the recipes)

1. **Water.** NIST gives 99.97 °C at 101.325 kPa, so the 100 °C setpoint is the
   boiling point at sea level, not a round guess; the page prints "at altitude
   water boils below 100 °C".
2. **Very hot drinks.** IARC (2016) classifies beverages above 65 °C as Group 2A,
   so 65 °C is a *limit* with a citation, not a taste preference.
3. **Honey under 12 months.** CDC's infant-botulism page is the reason the safety
   line exists; honey is marked optional for that reason.
4. **The reaction.** `3 Ag2S(s) + 2 Al(s) + 6 H2O(l) -> 6 Ag(s) + 2 Al(OH)3(s) + 3 H2S(g)`
   is atom-balanced by the gate's own parser: Ag 6, Al 2, H 12, O 6, S 3 on both
   sides. The equation is not decoration: it explains why the foil is consumed and
   why the item must touch it.
5. **Hydrogen sulfide.** NIOSH is the source of the ventilation line; the gas is
   the reason the method is "ventilate the room", not "do it in a sealed box".
6. **What tarnish is.** Silver sulfide, not dirt; the electrochemical cell moves
   the sulfide to the aluminium. It cannot repair a scratch or a worn plating
   (Canadian Conservation Institute).

## What the lane refuses, live

| input | result |
|---|---|
| "Ask it to cure the flu" (page break button) | fixed refusal, no number, no claim |
| cure/treat/prevent verb in title/summary/step | `RED` (`RecipeError`) - 13 tests in `mcp/tests/test_recipe.py` |
| unbalanced equation | `RED` with the element diff |
| a source that is cited but never used | `RED` |
| TR list with a different length | `RED` |
| `kj_recipe` over MCP with a malformed document | `{"verdict": "RED", "reason": ...}` - a result, not an exception |

## Honest limits

* **No clinical claim.** The drink is warm liquid; no RCT is cited and no dose is
  claimed. The boundary sentence says so in both languages.
* **Silver cleaning is cosmetic.** It removes silver sulfide; it does not
  sterilise, does not make an item food-safe, and repeated use removes a little
  silver, so museum/antique pieces are out of scope.
* **Source reachability (2026-10-27, `--check-urls`).** 6 fetches returned HTTP
  200 (NIST, IARC, WHO x2, LibreTexts, UW-Madison). CDC (x2) and NIOSH returned
  403 (bot wall); Canada.ca timed out twice (30 s, 45 s). Those three pages are
  cited for safety notes and were **not re-read today** - the citation stands, the
  live check does not.
* **The lane has no engine.** It cannot say whether the drink "works"; it can only
  refuse to say it. Property questions belong to `kj_ask`.

## Reproduce

```powershell
.venv\Scripts\python.exe mcp\recipe.py data\recipes\mint_lemon.json --markdown
.venv\Scripts\python.exe mcp\recipe.py data\recipes\silver_tarnish.json --markdown
.venv\Scripts\python.exe mcp\recipe.py data\recipes\mint_lemon.json data\recipes\silver_tarnish.json --check-urls
.venv\Scripts\python.exe tools\recipe_page.py --all --check
node .opencode\skills\lab\scripts\shot.mjs .opencode\skills\lab\labs\recipe_mint_lemon.html mint.png --w 1600 --h 900
```

Evidence PNGs: `%TEMP%\opencode\labshots\kj_mint_e2e.png` (54 parts, 27 356 tris,
61 fps) and `kj_silver_e2e.png` (25 parts, 16 086 tris, 61 fps).
