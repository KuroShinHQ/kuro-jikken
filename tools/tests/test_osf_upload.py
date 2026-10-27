"""Mocked tests: no network; token hygiene enforced."""
import sys, types
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import osf_upload as O  # noqa: E402


class FakeResp:
    def __init__(self, j=None, code=201):
        self._j = j or {}; self.status_code = code
    def json(self): return self._j
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(f"HTTP {self.status_code}")

class FakeSession:
    def post(self, url, **k): return FakeResp({"data": {"id": "fakeid"}})
    def get(self, url, **k):
        if url.rstrip("/").endswith("files"):
            return FakeResp({"data": [
                {"attributes": {"kind": "folder", "name": "osfstorage"},
                 "links": {"upload": "https://u/presigned"}},
            ]})
        if "format=json" in url:
            return FakeResp({"data": [
                {"attributes": {"kind": "file", "name": "plan.md", "size": 2681, "extra": {"hashes": {}}}},
                {"attributes": {"kind": "file", "name": "LOCK.sha256", "size": 82, "extra": {"hashes": {}}}},
                {"attributes": {"kind": "file", "name": "LOCK_ACCESS_LOG.md", "size": 46, "extra": {"hashes": {}}}},
            ]})
        return FakeResp({})
    def put(self, url, **k): return FakeResp({}, 201)
    def patch(self, url, **k): return FakeResp({}, 200)

class RecordingSession(FakeSession):
    def __init__(self): self.calls = []
    def post(self, url, **k): self.calls.append(("post", url)); return FakeResp({"data": {"id": "n1"}})
    def get(self, url, **k): self.calls.append(("get", url)); return super().get(url, **k)
    def put(self, url, **k): self.calls.append(("put", url)); return FakeResp({}, 201)
    def patch(self, url, **k): self.calls.append(("patch", url)); return FakeResp({}, 200)

def test_dry_run_no_network(capsys):
    s = RecordingSession(); O.requests = s
    O.main([])
    out = capsys.readouterr().out
    assert "project_title" in out and s.calls == []

def test_missing_token_clean_error(monkeypatch, capsys):
    fake = types.ModuleType("winreg")
    fake.HKEY_CURRENT_USER = 0x80000001
    def boom(*a, **k): raise OSError("no")
    fake.OpenKey = boom
    monkeypatch.setitem(sys.modules, "winreg", fake)
    monkeypatch.delenv("OSF_TOKEN", raising=False)
    with pytest.raises(SystemExit) as e:
        O.main(["--confirm"])
    assert "missing" in capsys.readouterr().err

def test_public_refused_without_confirm(capsys):
    with pytest.raises(SystemExit) as e:
        O.main(["--public"])
    assert "--public requires --confirm" in capsys.readouterr().err

def test_token_never_in_output(monkeypatch, capsys):
    monkeypatch.setenv("OSF_TOKEN", "TEST_ONLY_FAKE_TOKEN_0123456789abcdef")
    monkeypatch.setattr(O, "new_session", lambda: RecordingSession())
    O.main(["--confirm"])
    cap = capsys.readouterr()
    assert "TEST_ONLY_FAKE_TOKEN_0123456789abcdef" not in (cap.out + cap.err)

@pytest.mark.skipif(sys.platform != "win32", reason="the token is read from the Windows registry")
def test_mismatch_blocks_public(monkeypatch, capsys):
    monkeypatch.setattr(O, "new_session", lambda: RecordingSession())
    monkeypatch.setattr(O, "list_files", lambda s, n: {"plan.md": {"size": 999, "hashes": {}}})
    with pytest.raises(SystemExit) as e:
        O.main(["--confirm", "--public"])
    assert "MISMATCH" in capsys.readouterr().err
