"""Fetch the two S4 sources into ``C:\\KuroshinHQ\\_hub\\data\\cosmetics``.

The repository never stores the raw product dump (ODbL share-alike) or the raw
CosIng payloads; it stores the derived, gated pool and the hashes that pin
these files -- see ``data/manifest.json``.

    python tools/fetch_cosmetics.py --obf                  # ~104 MB gz dump
    python tools/fetch_cosmetics.py --cosing               # records for the label names
    python tools/fetch_cosmetics.py --check                # sizes and hashes on disk

CosIng is a European Commission document: reuse is allowed under CC BY 4.0
(Commission Decision 2011/833/EU, see the site's legal notice), with credit.
Open Beauty Facts is ODbL-1.0 (database) + DbCL-1.0 (contents).

Why not crawl CosIng page by page: the public search API caps deep paging at
10,000 results while the database holds 36,197 records. The build therefore
asks for exactly the names that occur on real labels (``terms`` query, batches
of 150) and records the coverage instead of pretending to hold the full file.
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cosmetics_sources as S  # noqa: E402

OBF_URL = "https://world.openbeautyfacts.org/data/openbeautyfacts-products.jsonl.gz"
COSING_API = "https://webgate.ec.europa.eu/es/search-api/rest/search"
# Public front-end key: every visitor of the CosIng site receives it.
COSING_KEY = "285a77fd-1257-4271-8507-f0c6b2961203"
BATCH = 50
PAGE = 200
KEEP = (
    "inciName", "nameOfCommonIngredientsGlossary", "chemicalName", "chemicalDescription",
    "casNo", "ecNo", "functionName", "cosmeticRestriction", "otherRestrictions",
    "annexNo", "note", "identifiedIngredient", "maximumConcentration",
    "wordingOfConditions", "productTypeBodyParts", "innName", "phEurName",
    "perfuming", "officialJournalPublication", "substanceId", "status", "itemType",
)


def _post(query: dict, page: int, timeout: int = 90) -> bytes:
    params = urllib.parse.urlencode({
        "apiKey": COSING_KEY, "text": "*", "pageSize": PAGE, "pageNumber": page,
    })
    boundary = "----kurojikken" + hashlib.sha1(
        json.dumps(query, sort_keys=True).encode() + str(page).encode()
    ).hexdigest()[:16]
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="query"; filename="blob"\r\n'
        "Content-Type: application/json\r\n\r\n"
        f"{json.dumps(query)}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    request = urllib.request.Request(
        f"{COSING_API}?{params}", data=body, method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "kuro-jikken/0.1 (dataset build)",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == 3:
                raise SystemExit(f"CosIng query failed after 4 tries: {exc}")
            time.sleep(2.0 * (attempt + 1))
    raise AssertionError("unreachable")


def _clean(values) -> list:
    out = []
    for value in values or []:
        for part in str(value).split(";"):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def _compact(row: dict) -> dict:
    meta = row.get("metadata") or {}
    record = {}
    for field in KEEP:
        values = _clean(meta.get(field))
        if values:
            record[field] = values
    item_type = _clean(meta.get("itemType")) or ["ingredient"]
    record["itemType"] = item_type
    record["reference"] = (row.get("reference") or "").strip()
    substance = _clean(meta.get("substanceId"))
    if substance:
        record["substanceId"] = substance[0]
    return record


def fetch_obf(target: pathlib.Path | None = None) -> pathlib.Path:
    target = target or S.RAW_DIR / S.OBF_NAME
    S.RAW_DIR.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(OBF_URL, headers={"User-Agent": "kuro-jikken/0.1"})
    with urllib.request.urlopen(request, timeout=180) as response, target.open("wb") as handle:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
    print(f"wrote {target} ({target.stat().st_size:,} B, sha256 {S.sha256(target)})")
    return target


def fetch_cosing(min_products: int = 2) -> pathlib.Path:
    obf = S.RAW_DIR / S.OBF_NAME
    if not obf.is_file():
        raise SystemExit(f"missing {obf}; run --obf first")
    counts, _brands, stats = S.count_tokens(S.iter_products(obf))
    names = sorted(name for name, count in counts.items() if count >= min_products)
    print(f"OBF: {stats['products']:,} products, {stats['with_inci']:,} with an INCI list, "
          f"{stats['tokens_total']:,} distinct tokens; querying {len(names):,} with >= {min_products}")

    records, seen, pages, raw = {}, set(), 0, hashlib.sha256()
    started = time.time()

    def query(field: str, batch: list, found: set) -> int:
        """Run one ``terms`` clause (the API rejects bool.should + terms)."""
        nonlocal pages
        query_body = {"terms": {field: batch}}
        page = 1
        hits = 0
        while True:
            body = _post(query_body, page)
            raw.update(body)
            payload = json.loads(body)
            rows = payload.get("results") or []
            pages += 1
            for row in rows:
                record = _compact(row)
                key = record.get("substanceId") or record.get("reference")
                if key and key not in seen:
                    seen.add(key)
                    records[key] = record
                found.update(names_in(record, field))
                hits += 1
            total = int(payload.get("totalResults") or 0)
            if not rows or page * PAGE >= total:
                break
            page += 1
        return hits

    def names_in(record: dict, field: str) -> set:
        return {name.upper() for name in record.get(field, [])}

    matched_names, inci_found = set(), set()
    for start in range(0, len(names), BATCH):
        batch = names[start:start + BATCH]
        query("inciName", batch, inci_found)
        matched_names.update(name for name in batch if name in inci_found)
        done = start + len(batch)
        if (start // BATCH) % 10 == 0 or done >= len(names):
            print(f"  inciName {done:,}/{len(names):,} names, {len(records):,} records "
                  f"({time.time() - started:.0f}s)", flush=True)
        time.sleep(0.1)

    rest = [name for name in names if name not in matched_names]
    print(f"  dotted pass: {len(rest):,} names (CosIng keeps the period in 'ALCOHOL DENAT.')",
          flush=True)
    for start in range(0, len(rest), BATCH):
        batch = rest[start:start + BATCH]
        query("inciName", [name + "." for name in batch], inci_found)
        matched_names.update(name for name in batch if (name + ".") in inci_found)
        done = start + len(batch)
        if (start // BATCH) % 10 == 0 or done >= len(rest):
            print(f"  dotted {done:,}/{len(rest):,} names, {len(records):,} records "
                  f"({time.time() - started:.0f}s)", flush=True)
        time.sleep(0.1)

    rest = [name for name in names if name not in matched_names]
    print(f"  glossary pass: {len(rest):,} names not found by INCI name", flush=True)
    for start in range(0, len(rest), BATCH):
        batch = rest[start:start + BATCH]
        query("nameOfCommonIngredientsGlossary", batch, set())
        done = start + len(batch)
        if (start // BATCH) % 10 == 0 or done >= len(rest):
            print(f"  glossary {done:,}/{len(rest):,} names, {len(records):,} records "
                  f"({time.time() - started:.0f}s)", flush=True)
        time.sleep(0.1)

    present = set()
    for record in records.values():
        present.update(names_in(record, "inciName"))
        present.update(names_in(record, "nameOfCommonIngredientsGlossary"))
    matched = sum(1 for name in names if name in present)
    today = dt.date.today().strftime("%Y%m%d")
    target = S.RAW_DIR / f"cosing_inci_{today}.json"
    document = {
        "schema": "kj-cosing-labels/1",
        "source": "CosIng (European Commission, GROWTH)",
        "licence": S.COSING_LICENCE,
        "attribution": S.COSING_ATTRIBUTION,
        "api": COSING_API,
        "fetched": dt.datetime.now().isoformat(timespec="seconds"),
        "min_products": min_products,
        "names_queried": len(names),
        "names_matched": matched,
        "pages": pages,
        "raw_sha256": raw.hexdigest(),
        "count": len(records),
        "obf_stats": stats,
        "entries": list(records.values()),
    }
    target.write_text(json.dumps(document, ensure_ascii=False, indent=0) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"wrote {target} ({target.stat().st_size:,} B, {len(records):,} records, "
          f"{matched:,}/{len(names):,} names matched)")
    return target


def check() -> int:
    for path in sorted(S.RAW_DIR.glob("*")):
        if path.is_file():
            print(f"{path.name}\t{path.stat().st_size}\t{S.sha256(path)}")
    obf = S.RAW_DIR / S.OBF_NAME
    if obf.is_file():
        try:
            next(iter(S.iter_products(obf)))
        except (OSError, StopIteration) as exc:
            print(f"gzip: NOT readable: {exc}")
            return 1
        print("gzip: readable")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="fetch the S4 source files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cosing", action="store_true", help="fetch CosIng records for label names")
    group.add_argument("--obf", action="store_true", help="download the Open Beauty Facts dump")
    group.add_argument("--check", action="store_true", help="hash what is already on disk")
    parser.add_argument("--min-products", type=int, default=2,
                        help="only query names seen on at least N products (default 2)")
    args = parser.parse_args()
    if args.cosing:
        fetch_cosing(args.min_products)
    elif args.obf:
        fetch_obf()
    else:
        return check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
