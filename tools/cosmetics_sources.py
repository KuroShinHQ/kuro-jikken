"""Shared readers for the S4 sources: Open Beauty Facts labels + CosIng records.

Both raw files live outside the repository (``C:\\KuroshinHQ\\_hub\\data\\cosmetics``):
the OBF dump is ODbL share-alike, the CosIng payload is a 36k-record Commission
document. Only the derived pool is committed, with the hashes recorded in
``data/manifest.json``.

The tokeniser is deliberately conservative: an INCI label is a comma separated
list, but commas also occur inside names (``1,2-HEXANEDIOL``) and inside
parentheses. A token that cannot be read is left as it is and will simply not
match CosIng -- the build reports that number instead of hiding it.
"""
import gzip
import hashlib
import json
import pathlib
import re

RAW_DIR = pathlib.Path(r"C:\KuroshinHQ\_hub\data\cosmetics")
OBF_NAME = "openbeautyfacts-products.jsonl.gz"
COSING_GLOB = "cosing_inci_*.json"

OBF_LICENCE = "ODbL-1.0 + DbCL-1.0"
COSING_LICENCE = "CC-BY-4.0"
COSING_ATTRIBUTION = "European Commission, CosIng - Cosmetic ingredient database"

_EDGE = "*†‡•·-–—.,;: \t\r\n"
_SPACE = re.compile(r"\s+")
_PAREN = re.compile(r"\([^)]*\)")

# Declared label synonyms: the printed list sometimes carries two or three
# naming conventions for one CosIng entry ("AQUA/WATER/EAU" on French labels,
# "FRAGRANCE" on US ones). Collapsing them is a naming decision, not a data
# edit; the table is deliberately tiny and every entry maps to one INCI name.
ALIASES = {
    "AQUA/WATER": "AQUA",
    "AQUA / WATER": "AQUA",
    "AQUA/WATER/EAU": "AQUA",
    "EAU": "AQUA",
    "FRAGRANCE": "PARFUM",
    "PARFUM/FRAGRANCE": "PARFUM",
    "PERFUME": "PARFUM",
}


def match_key(name: str) -> str:
    """Case/punctuation-insensitive key for joining a label name to CosIng."""
    return _SPACE.sub(" ", str(name).upper()).strip().rstrip(".")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_products(path: pathlib.Path = RAW_DIR / OBF_NAME):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def split_inci(text: str) -> list:
    """Split an INCI list on commas that are neither in parentheses nor digits."""
    parts, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            before = text[index - 1] if index else ""
            after = text[index + 1] if index + 1 < len(text) else ""
            if before.isdigit() and after.isdigit():
                continue  # 1,2-HEXANEDIOL
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return parts


def normalise(token: str) -> str:
    token = token.strip().strip(_EDGE)
    token = _SPACE.sub(" ", token)
    token = token.strip(_EDGE)
    if not token:
        return ""
    stripped = _SPACE.sub(" ", _PAREN.sub(" ", token)).strip(_EDGE)
    if stripped:
        token = stripped
    token = re.sub(r"\s*/\s*", "/", token).upper()
    if len(token) < 2 or not any(ch.isalpha() for ch in token):
        return ""
    for bad in ("MAY CONTAIN", "INGREDIENTS", "CONTAINS", "SEE PACKAGE"):
        if bad in token:
            return ""
    return ALIASES.get(token, token)


def product_tokens(product: dict) -> list:
    """Label text first, structured field second.

    Open Beauty Facts' own ``ingredients`` parser splits on ``/`` and inside
    parentheses: "Caprylic/Capric Triglyceride" becomes "CAPRYLIC" +
    "CAPRIC TRIGLYCERIDE" and "Ricinus Communis (Castor) Seed Oil" becomes
    "RICINUS COMMUNIS" + "SEED OIL". The printed list is the primary evidence,
    so it wins; the parsed field is only a fallback when the text is missing.
    """
    tokens = []
    for key in ("ingredients_text", "ingredients_text_en"):
        text = product.get(key) or ""
        if not text:
            continue
        upper = text.upper()
        marker = upper.find("INGREDIENTS")
        if marker >= 0:
            text = text[marker + len("INGREDIENTS"):].lstrip(" :\t")
        tokens = [normalise(part) for part in split_inci(text)]
        break
    if not tokens:
        for ingredient in product.get("ingredients") or []:
            text = (ingredient.get("text") or "").strip()
            if text:
                tokens.extend(normalise(part) for part in split_inci(text))
    seen, out = set(), []
    for token in tokens:
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def count_tokens(products) -> tuple:
    """Return (per-token product counts, per-token brand sets, stats)."""
    counts, brands = {}, {}
    stats = {"products": 0, "with_inci": 0, "tokens_total": 0}
    for product in products:
        stats["products"] += 1
        tokens = product_tokens(product)
        if len(tokens) < 2:
            continue
        stats["with_inci"] += 1
        brand = (product.get("brands") or "").split(",")[0].strip()
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
            if brand:
                brands.setdefault(token, set()).add(brand)
    stats["tokens_total"] = len(counts)
    return counts, brands, stats


def cosing_files() -> list:
    return sorted(RAW_DIR.glob(COSING_GLOB))


def load_cosing(path: pathlib.Path | None = None) -> dict:
    path = path or (cosing_files()[-1] if cosing_files() else None)
    if path is None:
        raise SystemExit(f"no {COSING_GLOB} in {RAW_DIR}; run tools/fetch_cosmetics.py --cosing")
    document = json.loads(path.read_text(encoding="utf-8"))
    index = {}
    for record in document["entries"]:
        for name in record.get("inciName") or []:
            index.setdefault(match_key(name), []).append(record)
        for name in record.get("nameOfCommonIngredientsGlossary") or []:
            index.setdefault(match_key(name), []).append(record)
    return {"document": document, "index": index, "path": path}
