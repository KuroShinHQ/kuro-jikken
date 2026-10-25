"""Thin MCP server (stdio) for kuro-jikken tools (Task 12)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mcp.server.mcpserver import MCPServer
import rdkit_tool as R
import esol as E

mcp = MCPServer("kuro-jikken")
ERR = "validation results, NOT locked: typical RMSE ~2.23 log units overall; ~1.22 on ESOL-like domain (neutral single-component, MW<=500)"

def wrap(d):
    d = dict(d); d["error_bar"] = ERR; return d

@mcp.tool()
def parse_smiles(smiles: str) -> dict:
    """Canonical SMILES or a clean error."""
    return wrap(R.parse_smiles(smiles))

@mcp.tool()
def formula(smiles: str) -> dict:
    """Molecular formula (RDKit CalcMolFormula)."""
    return wrap(R.formula(smiles))

@mcp.tool()
def molecular_weight(smiles: str) -> dict:
    """Average molecular weight, g/mol (RDKit MolWt)."""
    return wrap(R.molecular_weight(smiles))

@mcp.tool()
def heavy_atom_count(smiles: str) -> dict:
    """Heavy atom count (atomic number > 1)."""
    return wrap(R.heavy_atom_count(smiles))

@mcp.tool()
def ring_count(smiles: str) -> dict:
    """Number of rings (RDKit CalcNumRings, SSSR)."""
    return wrap(R.ring_count(smiles))

@mcp.tool()
def hbd_lipinski(smiles: str) -> dict:
    """H-bond donors, Lipinski scheme (NH/OH hydrogen count)."""
    return wrap(R.hbd_lipinski(smiles))

@mcp.tool()
def hbd_plain(smiles: str) -> dict:
    """H-bond donors, plain RDKit scheme (donor atoms)."""
    return wrap(R.hbd_plain(smiles))

@mcp.tool()
def hba_lipinski(smiles: str) -> dict:
    """H-bond acceptors, Lipinski scheme (N+O count)."""
    return wrap(R.hba_lipinski(smiles))

@mcp.tool()
def hba_plain(smiles: str) -> dict:
    """H-bond acceptors, plain RDKit scheme."""
    return wrap(R.hba_plain(smiles))

@mcp.tool()
def esol_predict(smiles: str) -> dict:
    """ESOL aqueous-solubility prediction, logS (mol/L), Delaney 2004 coefficients.
    Returns in_domain flag (neutral, single-component, no metal, MW<=500, no phosphorus),
    matched error bar (in-domain ~1.2, out-of-domain ~5 log units, locked-set report),
    and an explicit unreliability caveat when out of domain."""
    return wrap(E.esol_published(smiles))

if __name__ == "__main__":
    mcp.run()

