"""In-process tool registry for modes B and C.

The set matches ``mcp/server.py`` (same functions, same envelopes) plus
``rotatable_bonds``, which the benchmark needs as one of the seven properties;
``mcp/rdkit_tool.py`` already exports it, the MCP server just does not wrap it
(see bench/README.md). No network access is possible from here.
"""

from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO / "mcp") not in sys.path:
    sys.path.insert(0, str(REPO / "mcp"))

import esol as E  # noqa: E402
import rdkit_tool as R  # noqa: E402

TOOLS = {
    "parse_smiles": R.parse_smiles,
    "formula": R.formula,
    "molecular_weight": R.molecular_weight,
    "heavy_atom_count": R.heavy_atom_count,
    "ring_count": R.ring_count,
    "hbd_lipinski": R.hbd_lipinski,
    "hbd_plain": R.hbd_plain,
    "hba_lipinski": R.hba_lipinski,
    "hba_plain": R.hba_plain,
    "rotatable_bonds": R.rotatable_bonds,
    "esol_predict": E.esol_published,
}

TOOL_NAMES: tuple[str, ...] = tuple(sorted(TOOLS))


class UnknownTool(KeyError):
    pass


def call_tool(name: str, smiles: str) -> dict:
    """Run one tool in-process. Never raises for bad chemistry (clean errors)."""
    if name not in TOOLS:
        raise UnknownTool(name)
    return TOOLS[name](smiles)


def canonical_smiles(smiles: str) -> str | None:
    result = R.parse_smiles(smiles)
    return result.get("canonical_smiles") if result.get("ok") else None
