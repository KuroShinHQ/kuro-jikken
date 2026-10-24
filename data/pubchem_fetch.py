import json, time, hashlib, sys
import urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw_pubchem"
SET = ROOT / "data" / "sample_set.json"
UA = "kuro-jikken/0.1 (open reproducible research repo; KuroShinHQ)"
BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
TAGS = ["CanonicalSMILES", "IsomericSMILES", "MolecularFormula", "MolecularWeight",
        "HeavyAtomCount", "HBondDonorCount", "HBondAcceptorCount", "RotatableBondCount"]
GAP = 0.25
_last = [0.0]

def gap():
    d = time.monotonic() - _last[0]
    if d < GAP:
        time.sleep(GAP - d)
    _last[0] = time.monotonic()

def load_set():
    data = json.loads(SET.read_text(encoding="utf-8"))
    return [(m["name"], m["cid"]) for m in data["molecules"]]

def http(cid, tags, tries=3):
    url = f"{BASE}{cid}/property/{chr(44).join(tags)}/JSON"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for i in range(tries):
        gap()
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read()
        except urllib.error.HTTPError:
            time.sleep(2 ** i)
        except Exception:
            time.sleep(2 ** i)
    return None, b""

def save_raw(cid, body):
    OUT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    f = OUT / f"cid_{cid}_{ts}.json"
    n = 1
    while f.exists():
        f = OUT / f"cid_{cid}_{ts}_{n}.json"
        n += 1
    f.write_bytes(body)
    with open(OUT / "manifest.csv", "a", encoding="utf-8") as m:
        m.write(f"{cid},{f.name},{datetime.now(timezone.utc).isoformat()}\n")
    return f

def canon(body):
    p = json.loads(body)["PropertyTable"]["Properties"][0]
    return hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), p

def verify(pairs):
    ok = True
    for name, cid in pairs:
        olds = sorted(OUT.glob(f"cid_{cid}_*.json"))
        if not olds:
            print(name, cid, "NO_RAW"); ok = False; continue
        h1, p1 = canon(olds[-1].read_bytes())
        st, body = http(cid, TAGS)
        if st != 200:
            print(name, cid, "FETCH_FAIL", st); ok = False; continue
        h2, p2 = canon(body)
        core = ["MolecularFormula","MolecularWeight","HeavyAtomCount","HBondDonorCount","HBondAcceptorCount","RotatableBondCount"]
        if {k: p1.get(k) for k in core} == {k: p2.get(k) for k in core}:
            print(name, cid, "MATCH", h1[:12])
        else:
            keys = sorted({k for k in set(p1) | set(p2) if p1.get(k) != p2.get(k)})
            print(name, cid, "DIFF", h1[:10], h2[:10], keys); ok = False
    return 0 if ok else 1

def main():
    pairs = load_set()
    if "--verify-existing" in sys.argv:
        return verify(pairs)
    ok = 0
    for name, cid in pairs:
        st, body = http(cid, TAGS)
        if st == 200:
            f = save_raw(cid, body); print(name, cid, "OK", f.name); ok += 1
        else:
            print(name, cid, "FAIL", st)
    print("SUMMARY", ok, "/", len(pairs))
    return 0 if ok == len(pairs) else 1

if __name__ == "__main__":
    raise SystemExit(main())



