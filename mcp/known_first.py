"""Known-first solubility resolver (P1b): KNOWN -> PREDICTED -> RED."""
from __future__ import annotations

import csv
import statistics
import sys
from functools import lru_cache
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import inchi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from esol import esol_published  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "solubility" / "raw" / "aqsoldb_20261025.tab"
DATASET = {
    "name": "AqSolDB",
    "snapshot": "2026-10-25",
    "doi": "10.7910/DVN/OVHAW8",
    "license": "CC0-1.0",
    "citation": "Sorkun, Khetan, Er, Sci. Data 6, 143 (2019)",
}
@lru_cache(maxsize=1)
def _index() -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    with open(DATA, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            key = (row.get("InChIKey") or "").strip()
            try:
                value = float(row["Solubility"])
            except (KeyError, TypeError, ValueError):
                continue
            if not key:
                continue
            index.setdefault(key, []).append(
                {
                    "row_id": row.get("ID") or "",
                    "name": row.get("Name") or "",
                    "logS": value,
                    "sd": row.get("SD") or "",
                    "occurrences": row.get("Ocurrences") or "",
                }
            )
    return index
def resolve(smiles: str) -> dict:
    """Return the best answer for logS: KNOWN, PREDICTED, or RED."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"status": "RED", "reason": f"RDKit could not parse SMILES: {smiles!r}"}
    key = inchi.MolToInchiKey(mol)
    rows = _index().get(key, [])
    if rows:
        value = statistics.median(row["logS"] for row in rows)
        return {
            "status": "KNOWN",
            "property": "logS",
            "value": value,
            "unit": "log10(mol/L)",
            "in_domain": True,
            "method": "experimental, AqSolDB snapshot",
            "source": {
                **DATASET,
                "inchi_key": key,
                "rows": [
                    {
                        "row_id": row["row_id"],
                        "name": row["name"],
                        "sd": row["sd"],
                        "occurrences": row["occurrences"],
                    }
                    for row in rows
                ],
            },
        }
    pred = esol_published(smiles)
    if not pred.get("ok"):
        return {"status": "RED", "reason": pred.get("error", "ESOL failed")}
    if not pred.get("in_domain"):
        reasons = ", ".join(pred.get("domain_reasons") or [])
        return {
            "status": "RED",
            "reason": f"out of applicability domain: {reasons}",
            "in_domain": False,
        }
    return {
        "status": "PREDICTED",
        "property": "logS",
        "value": pred["value"],
        "unit": "log10(mol/L)",
        "in_domain": True,
        "error_bar": pred.get("error_bar_logS"),
        "method": pred.get("method"),
        "note": pred.get("uncertainty_note"),
    }
def main() -> int:
    import json

    if len(sys.argv) != 2:
        print("usage: python mcp/known_first.py <SMILES>", file=sys.stderr)
        return 2
    result = resolve(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())



