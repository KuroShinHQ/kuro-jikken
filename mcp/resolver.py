"""Name -> identifiers, deterministic and offline (P3.5b).

No fuzzy matching and no network: either the name is in the local tables or the
answer is a refusal. An ambiguous name returns its candidates instead of picking
one. Sources, in order: CAS number, SMILES, Turkish synonym map, explicit
mixture table, ``chemicals`` name index; then the PubChemQC sigma index fills in
SMILES / InChIKey for the CAS.
"""
import os
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

FOLD = str.maketrans("çğıöşü", "cgiosu")

# Turkish everyday names -> the name the tables use (exact, no stemming)
TR_NAMES = {
    "etanol": "ethanol",
    "aseton": "acetone",
    "gliserin": "glycerol",
    "su": "water",
    "metanol": "methanol",
    "hekzan": "hexane",
    "toluen": "toluene",
    "izopropanol": "propan-2-ol",
    "isopropanol": "propan-2-ol",
    "vazelin": "petrolatum",
    "mum": "wax",
    "parafin": "paraffin wax",
    "mineral yagi": "mineral oil",
    "tuz": "sodium chloride",
    "sofra tuzu": "sodium chloride",
}

# mixtures: a CAS exists, but there is no single structure and often no enthalpy
MIXTURES = {
    "petrolatum": ("8009-03-8", "mixture: no Hansen entry, no Hfus"),
    "paraffin wax": ("8002-74-2", "mixture: Tm only, no Hfus"),
    "mineral oil": ("8042-47-5", "mixture: no Hansen entry, no melting data"),
    "wax": ("8009-03-8", "generic 'wax': treated as petrolatum only for lookups"),
}

# names that genuinely point at more than one substance -> one question, no pick
AMBIGUOUS = {
    "wax": ["petrolatum", "paraffin wax"],
    "mum": ["petrolatum", "paraffin wax"],
}


class NotFound(LookupError):
    """The name is not in any local table."""


class Ambiguous(ValueError):
    """The name matches more than one substance; the caller must ask."""

    def __init__(self, query, candidates):
        self.query = query
        self.candidates = list(candidates)
        super().__init__(f"{query}: {len(self.candidates)} candidates ({', '.join(self.candidates)})")


def normalise(text) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower().translate(FOLD))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9\-\. ]", " ", text).split())


def format_cas(raw):
    """Digits -> dashed CAS with a checksum check; invalid input returns None."""
    digits = re.sub(r"\D", "", str(raw))
    if not 5 <= len(digits) <= 10:
        return None
    body, check = digits[:-1], int(digits[-1])
    total = sum(i * int(ch) for i, ch in enumerate(reversed(body), start=1))
    if total % 10 != check:
        return None
    front, middle = body[:-2], body[-2:]  # CAS is always front(2-7)-middle(2)-check(1)
    return f"{front}-{middle}-{check}"


_SIGMA = None


def _sigma() -> dict:
    """CAS -> (SMILES, InChIKey) from the local PubChemQC index (lazy, once)."""
    global _SIGMA
    if _SIGMA is None:
        path = pathlib.Path(
            os.environ.get("KURO_SIGMA_DIR", r"C:\KuroshinHQ\_hub\data\formulation_sigma")
        ) / "sigma_profile_index.parquet"
        if not path.is_file():
            _SIGMA = {}
        else:
            import pandas as pd

            frame = pd.read_parquet(path, columns=["CAS", "SMILES", "InChIKey"])
            _SIGMA = {
                str(row.CAS): (row.SMILES, row.InChIKey)
                for row in frame.itertuples(index=False)
                if row.CAS
            }
    return _SIGMA


def _from_smiles(text):
    try:
        from rdkit import Chem
    except ImportError:
        return None
    mol = Chem.MolFromSmiles(text)
    if mol is None or "." in text:
        return None
    return {
        "smiles": Chem.MolToSmiles(mol),
        "inchikey": Chem.MolToInchiKey(mol),
    }


def _from_chemicals(name):
    from chemicals import search_chemical

    try:
        chem = search_chemical(name)
    except (ValueError, KeyError):
        return None
    casrn = format_cas(chem.CAS)
    if casrn is None:
        return None
    smiles, inchikey = _sigma().get(casrn, (None, None))
    return {
        "name": name,
        "casrn": casrn,
        "smiles": smiles or chem.smiles,
        "inchikey": inchikey,
        "source": "chemicals name index",
    }


def resolve(text: str) -> dict:
    """Resolve one name, CAS or SMILES; raise NotFound / Ambiguous otherwise."""
    query = normalise(text)
    if not query:
        raise NotFound("empty name")
    key = TR_NAMES.get(query, query)

    if key in AMBIGUOUS:
        raise Ambiguous(query, AMBIGUOUS[key])

    casrn = format_cas(query) if re.fullmatch(r"[\d\-]{5,}", query) else None
    if casrn:
        smiles, inchikey = _sigma().get(casrn, (None, None))
        return {
            "query": text, "name": None, "casrn": casrn,
            "smiles": smiles, "inchikey": inchikey,
            "source": "CAS number (sigma index)" if smiles else "CAS number",
        }

    if key in MIXTURES:
        casrn, note = MIXTURES[key]
        return {
            "query": text, "name": key, "casrn": casrn,
            "smiles": None, "inchikey": None,
            "source": "mixture table", "notes": [note],
        }

    # SMILES is case sensitive, so it must be tried before the lowercased name
    structure = _from_smiles(str(text).strip())
    if structure:
        return {"query": text, "name": None, "casrn": None, **structure, "source": "SMILES (RDKit)"}

    found = _from_chemicals(key)
    if found:
        return {"query": text, **found, "notes": []}

    raise NotFound(f"no local entry for {text!r}")


def ids(text: str) -> dict:
    """The payload a gate can use: only the identifiers that exist."""
    out = resolve(text)
    return {k: out[k] for k in ("smiles", "casrn", "inchikey") if out.get(k)}


def candidates(text: str) -> list:
    try:
        return [resolve(c) for c in AMBIGUOUS.get(normalise(text), [])]
    except (NotFound, Ambiguous):
        return []
