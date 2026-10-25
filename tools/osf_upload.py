"""OSF upload for pre-registration artifacts (kuro-jikken).

Uploads plan.md, LOCK.sha256 and LOCK_ACCESS_LOG.md to ONE new OSF project.
Modes:
  --dry-run   (default) plan only; no network, no token needed
  --confirm   real upload (token required)
  --public    only with --confirm; makes the project public after verification

TOKEN RULES: token comes from os.environ["OSF_TOKEN"] or, as a fallback, the
user-level environment value stored in the registry (HKCU\\Environment). The
value itself is NEVER printed, logged, written to files or placed in command
lines by this script. Missing token -> clean error.
Endpoints per developer.osf.io: create node (POST /v2/nodes/), upload file
(PUT <root-folder links.upload>?meta=...), list files (GET .../files),
set public (PATCH /v2/nodes/{id}).
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "validation/solubility/plan.md",
    "validation/solubility/LOCK.sha256",
    "validation/solubility/LOCK_ACCESS_LOG.md",
]
TITLE = "kuro-jikken: ESOL solubility validation (plan and lock)"
DESCRIPTION = (
    "Plan and lock hash were committed to Git before the evaluation; "
    "they were uploaded to OSF afterwards. Code: "
    "https://github.com/KuroShinHQ/kuro-jikken\n"
    "Archive DOI: 10.5281/zenodo.23633859"
)
API = "https://api.osf.io/v2"

def err(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(2)

def token_present() -> bool:
    if os.environ.get("OSF_TOKEN"):
        return True
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, "OSF_TOKEN")
            return bool(val)
    except OSError:
        return False

def token() -> str:
    t = os.environ.get("OSF_TOKEN")
    if not t:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                t, _ = winreg.QueryValueEx(k, "OSF_TOKEN")
        except OSError:
            t = None
    if not t:
        err("OSF_TOKEN missing (env var not set)")
    return t

def local_plan():
    plan = []
    for rel in FILES:
        p = ROOT / rel
        data = p.read_bytes()
        plan.append({
            "path": rel,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return plan

def plan_out():
    out = {
        "project_title": TITLE,
        "project_description": DESCRIPTION,
        "files": local_plan(),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))

# ---- network layer (thin seams, easy to mock in tests) ----
import requests  # noqa: E402

def new_session():  # seam: tests monkeypatch this to intercept calls
    return requests.Session()

def _headers():
    return {"Authorization": f"Bearer {token()}"}

def create_project(session):
    r = session.post(
        f"{API}/nodes/",
        headers=_headers(),
        json={"data": {"type": "nodes", "attributes": {"category": "project", "title": TITLE, "description": DESCRIPTION}}},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["data"]["id"]

def provider_url(session, node_id):
    r = session.get(f"{API}/nodes/{node_id}/files/", headers=_headers(), timeout=60)
    r.raise_for_status()
    for d in r.json().get("data", []):
        if d.get("attributes", {}).get("name") == "osfstorage":
            return (d.get("links") or {}).get("upload")

def upload_file(session, upload_url, path):
    import urllib.parse
    data = (ROOT / path).read_bytes()
    q = urllib.parse.urlencode({"name": Path(path).name, "kind": "file", "size": len(data)})
    r = session.put(upload_url + "?" + q, headers={**_headers(), "Content-Type": "application/octet-stream"}, data=data, timeout=120)
    r.raise_for_status()
    return r.status_code

def list_files(session, upload_url):
    r = session.get(upload_url + "?format=json", headers=_headers(), timeout=60)
    r.raise_for_status()
    found = {}
    for item in r.json().get("data", []):
        a = item.get("attributes", {})
        if a.get("kind") == "file":
            found[a.get("name")] = {"size": a.get("size"), "hashes": (a.get("extra") or {}).get("hashes", {})}
    return found

def verify(session, upload_url, plan):
    remote = list_files(session, upload_url)
    ok = True
    for f in plan:
        name = Path(f["path"]).name
        r = remote.get(name)
        status = "OK" if r and r.get("size") == f["size"] else "MISMATCH"
        if status == "MISMATCH":
            ok = False
        print(f"{status} {name} (local size {f['size']}, remote {r.get('size') if r else 'absent'})")
        if r:
            h = r.get("hashes", {}).get("sha256")
            if h:
                match = "sha256 OK" if h == f["sha256"] else "sha256 MISMATCH"
                print(f"  {match}")
                if match != "sha256 OK":
                    ok = False
    return ok

def run_confirm():
    if not token_present():
        err("OSF_TOKEN missing (env var not set)")
    s = new_session()
    node_id = create_project(s)
    print("project created:", node_id)
    upload_url = provider_url(s, node_id)
    if not upload_url:
        err("no provider upload url (unexpected API shape)")
    for f in local_plan():
        upload_file(s, upload_url, f["path"])
        print("uploaded:", Path(f["path"]).name)
    ok = verify(s, upload_url, local_plan())
    print("VERIFICATION:", "OK" if ok else "MISMATCH")
    return node_id, ok

def make_public(session, node_id):
    r = session.patch(f"{API}/nodes/{node_id}/", headers=_headers(), json={"data": {"type": "nodes", "id": node_id, "attributes": {"public": True}}}, timeout=60)
    r.raise_for_status()
    print("project set public")

def main(argv=None):
    argv = argv or sys.argv[1:]
    if "--public" in argv and "--confirm" not in argv:
        err("--public requires --confirm")
    if "--confirm" in argv:
        node_id, ok = run_confirm()
        if "--public" in argv:
            if not ok:
                err("verification MISMATCH -> NOT making public")
            make_public(new_session(), node_id)
    else:
        plan_out()
    return 0

if __name__ == "__main__":
    sys.exit(main())
