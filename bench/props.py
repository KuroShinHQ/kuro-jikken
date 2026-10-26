"""The seven benchmark properties and their plain-word definitions.

Reference values come from the tested functions in ``mcp/rdkit_tool.py``
(prereg section 3.2). The definition text below is what the model sees in the
question, so a correct answer is well defined.
"""

from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Callable

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO / "mcp") not in sys.path:
    sys.path.insert(0, str(REPO / "mcp"))

import rdkit_tool as R  # noqa: E402  (path set above)


@dataclass(frozen=True)
class Property:
    key: str
    label: str
    kind: str  # "formula" | "float" | "int"
    unit: str
    definition: str
    format_hint: str
    tolerance: float | None
    fn: Callable[[str], dict]

    def reference(self, smiles: str) -> Any:
        """Reference value from the tested tool layer (raises on bad SMILES)."""
        result = self.fn(smiles)
        if not result.get("ok", True):
            raise ValueError(f"{self.key}: {result.get('error')}")
        return result["value"]


PROPERTIES: tuple[Property, ...] = (
    Property(
        key="formula",
        label="molecular formula",
        kind="formula",
        unit="formula",
        definition=(
            "Hill notation: carbon first, then hydrogen, then all other elements "
            "in alphabetical order; counts follow the element symbol and a count "
            "of 1 is omitted."
        ),
        format_hint='a JSON string, e.g. "C6H6"',
        tolerance=None,
        fn=R.formula,
    ),
    Property(
        key="molecular_weight",
        label="molecular weight",
        kind="float",
        unit="g/mol",
        definition=(
            "average molecular weight in g/mol, using standard average atomic "
            "weights and including implicit hydrogens."
        ),
        format_hint="a JSON number in g/mol, e.g. 78.11",
        tolerance=0.05,
        fn=R.molecular_weight,
    ),
    Property(
        key="heavy_atom_count",
        label="heavy-atom count",
        kind="int",
        unit="count",
        definition="number of heavy atoms, i.e. every atom except hydrogen.",
        format_hint="a JSON integer, e.g. 6",
        tolerance=None,
        fn=R.heavy_atom_count,
    ),
    Property(
        key="ring_count",
        label="ring count",
        kind="int",
        unit="count",
        definition=(
            "number of rings in the smallest set of smallest rings (SSSR); "
            "aromatic and aliphatic rings both count, and each ring of a fused "
            "system counts separately."
        ),
        format_hint="a JSON integer, e.g. 1",
        tolerance=None,
        fn=R.ring_count,
    ),
    Property(
        key="hbd_lipinski",
        label="hydrogen-bond donors (Lipinski)",
        kind="int",
        unit="count",
        definition=(
            "Lipinski hydrogen-bond donors: the number of N-H and O-H hydrogens "
            "(water = 2, urea = 4)."
        ),
        format_hint="a JSON integer, e.g. 2",
        tolerance=None,
        fn=R.hbd_lipinski,
    ),
    Property(
        key="hba_lipinski",
        label="hydrogen-bond acceptors (Lipinski)",
        kind="int",
        unit="count",
        definition=(
            "Lipinski hydrogen-bond acceptors: the number of nitrogen and oxygen "
            "atoms."
        ),
        format_hint="a JSON integer, e.g. 3",
        tolerance=None,
        fn=R.hba_lipinski,
    ),
    Property(
        key="rotatable_bonds",
        label="rotatable bonds (strict)",
        kind="int",
        unit="count",
        definition=(
            "rotatable bonds under RDKit's default (strict) definition: single, "
            "non-ring bonds between non-terminal heavy atoms; amide and ester "
            "C-N/C-O bonds are not counted."
        ),
        format_hint="a JSON integer, e.g. 2",
        tolerance=None,
        # same calculator the tool layer exports; the MCP server itself does not
        # expose rotatable_bonds, see bench/README.md
        fn=R.rotatable_bonds,
    ),
)

PROPERTY_BY_KEY: dict[str, Property] = {p.key: p for p in PROPERTIES}
PROPERTY_KEYS: tuple[str, ...] = tuple(p.key for p in PROPERTIES)


def reference_row(smiles: str) -> dict[str, Any]:
    """All seven reference values for one molecule."""
    return {p.key: p.reference(smiles) for p in PROPERTIES}
