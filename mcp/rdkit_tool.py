"""kuro-jikken · RDKit tool layer.

Pure, deterministic, offline RDKit wrappers used by the study's Mode B tool.
Nothing here touches the network; nothing is random.

Contract (docs/FIRST_TASKS.md Task 3):
* ``parse_smiles`` returns the canonical SMILES, or a clean structured error.
* Every property function returns ``{"value", "unit", "method", "rdkit_version"}``
  and raises nothing — invalid input yields a ``{"ok": False, "error": ...}``
  dict instead of an exception.
* The *exact* definition behind every property is written in its docstring,
  quoting the pinned RDKit (``2026.09.1``) behaviour; the wrapper never
  redefines a property's meaning.
"""

from __future__ import annotations

from typing import Any

import rdkit
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

RDKit_VERSION = rdkit.__version__  # e.g. "2026.09.1"

__all__ = [
    "parse_smiles",
    "formula",
    "molecular_weight",
    "heavy_atom_count",
    "ring_count",
    "hbond_donors",
    "hbond_acceptors",
    "rotatable_bonds",
]


def _ok(value: Any, unit: str, method: str) -> dict:
    """Standard success envelope: never a bare number."""
    return {
        "value": value,
        "unit": unit,
        "method": method,
        "rdkit_version": RDKit_VERSION,
    }


def _fail(message: str) -> dict:
    """Standard clean-error envelope."""
    return {"ok": False, "error": message, "rdkit_version": RDKit_VERSION}


def _with_mol(smiles: str):
    mol = Chem.MolFromSmiles(smiles)  # sanitization is deterministic
    if mol is None:
        return None
    return mol


def parse_smiles(smiles: str) -> dict:
    """Return the canonical SMILES for ``smiles``, or a clean error.

    Definition: RDKit ``Chem.MolFromSmiles`` sanitization (the唯一 default
    pipeline: valence checks, H-counts, ring perception) followed by
    ``Chem.MolToSmiles`` canonicalization. No isotope/stereo massaging beyond
    what these two calls do.

    Failure: explicit ``{"ok": False, "error": ...}``; never None silently.
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return {
        "ok": True,
        "canonical_smiles": Chem.MolToSmiles(mol),
        "method": "rdkit.Chem.MolToSmiles(Chem.MolFromSmiles(smiles))",
        "rdkit_version": RDKit_VERSION,
    }


def formula(smiles: str) -> dict:
    """Molecular formula.

    Definition (pinned rdkit 2026.09.1): ``rdkit.Chem.rdMolDescriptors.
    CalcMolFormula(mol)`` — bundled doc: *"returns the molecule's formula"*,
    called with the defaults ``separateIsotopes=False`` (mono-isotope thrill
    pooled) and ``abbreviateHIsotopes=True``.
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return _ok(
        rdMolDescriptors.CalcMolFormula(mol),
        "formula",
        "rdkit.Chem.rdMolDescriptors.CalcMolFormula(mol) [defaults]",
    )


def molecular_weight(smiles: str) -> dict:
    """Average molecular weight in g/mol.

    Definition (pinned rdkit 2026.09.1): ``rdkit.Chem.Descriptors.MolWt`` —
    bundled doc: *"The average molecular weight of the molecule"*. Average
    atomic weights are used (not monoisotopic), implicit hydrogens included.
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return _ok(
        Descriptors.MolWt(mol),
        "g/mol",
        "rdkit.Chem.Descriptors.MolWt(mol)",
    )


def heavy_atom_count(smiles: str) -> dict:
    """Number of heavy atoms.

    Definition (pinned rdkit 2026.09.1): ``Mol.GetNumHeavyAtoms()`` — bundled
    doc: *"Returns the number of heavy atoms (atomic number >1) in the
    molecule"* — i.e. hydrogens are excluded, everything else counts.
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return _ok(
        mol.GetNumHeavyAtoms(),
        "count",
        "rdkit.Chem.rdchem.Mol.GetNumHeavyAtoms (atomic number > 1)",
    )


def ring_count(smiles: str) -> dict:
    """Number of rings.

    Definition (pinned rdkit 2026.09.1): ``rdkit.Chem.rdMolDescriptors.
    CalcNumRings(mol)`` — bundled doc: *"returns the number of rings for a
    molecule"*. Rings are those in the molecule's ring perception (SSSR-based
    ring info; aromatic and aliphatic rings both count).
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return _ok(
        rdMolDescriptors.CalcNumRings(mol),
        "count",
        "rdkit.Chem.rdMolDescriptors.CalcNumRings(mol)",
    )


def hbond_donors(smiles: str) -> dict:
    """Hydrogen-bond donor atoms (traditional Lipinski pair).

    Definition (pinned rdkit 2026.09.1): ``rdkit.Chem.rdMolDescriptors.
    CalcNumLipinskiHBD(mol)``. In RDKit's own ``Chem/Lipinski.py`` this is
    ``NHOHCount`` with the bundled doc *"Number of NHs or OHs"*; the RDKit
    source comments NumHDonors→CalcNumHBD as the alternative scheme and notes
    *"if you want traditional Lipinski numbers, you should use NOCounts ...
    instead of HAcceptor"* — we pin the traditional-NHOH pair here because the
    alternative demonstrably scores ``water`` as 0 donors / 0 acceptors under
    this pinned version (verified empirically while building this repo),
    which is wrong for the study's semantics.

    Caveat (kept explicit): H-bond counts are definition-sensitive
    (docs README §2); deltas vs PubChem are reported in
    ``validation/tool_vs_pubchem.md``, never silently reconciled.
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return _ok(
        rdMolDescriptors.CalcNumLipinskiHBD(mol),
        "count",
        "rdkit.Chem.rdMolDescriptors.CalcNumLipinskiHBD(mol) [NHOHCount scheme]",
    )


def hbond_acceptors(smiles: str) -> dict:
    """Hydrogen-bond acceptor atoms (traditional Lipinski pair).

    Definition (pinned rdkit 2026.09.1): ``rdkit.Chem.rdMolDescriptors.
    CalcNumLipinskiHBA(mol)``. In RDKit's ``Chem/Lipinski.py`` this is
    ``NOCount`` with the bundled doc *"Number of Nitrogens and Oxygens"* —
    i.e. roughly the count of N/O acceptor atoms in the traditional scheme.

    Same definition-sensitive caveat applies as for ``hbond_donors``.
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return _ok(
        rdMolDescriptors.CalcNumLipinskiHBA(mol),
        "count",
        "rdkit.Chem.rdMolDescriptors.CalcNumLipinskiHBA(mol) [NOCount scheme]",
    )


def rotatable_bonds(smiles: str) -> dict:
    """Number of rotatable bonds.

    Definition (pinned rdkit 2026.09.1): ``rdkit.Chem.rdMolDescriptors.
    CalcNumRotatableBonds(mol)`` called with the RDKit *default* option
    (``NumRotatableBondsOptions.Default``). Bundled doc for this function:
    *NonStrict = "Simple rotatable bond definition"; Strict = "(default) does
    not count things like amide or ester bonds"; StrictLinkages additionally
    handles ring–ring linkages.* The classic RDKit rule expressed as SMARTS in
    ``Chem/Lipinski.py`` is ``'[!$(*#*)&!D1]-&!@[!$(*#*)&!D1]'`` (single,
    non-ring, non-terminal bonds; triple-bonded atoms excluded). We rely on
    the function default and record the option verbatim.
    """
    mol = _with_mol(smiles)
    if mol is None:
        return _fail(f"RDKit could not parse SMILES: {smiles!r}")
    return _ok(
        rdMolDescriptors.CalcNumRotatableBonds(mol),
        "count",
        "rdkit.Chem.rdMolDescriptors.CalcNumRotatableBonds(mol) "
        "[NumRotatableBondsOptions.Default]",
    )
