"""Tests for tools/solubility_eval_v2.py. Synthetic fixtures only.

No study data is opened: rows are generated, and loaders are replaced.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import solubility_eval_v2 as ev  # noqa: E402


def make_rows(n, seed=7, slope=1.0, with_logs=True):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        row = {
            "inchikey": f"KEY-{i:05d}",
            "logp": float(rng.normal(0.0, 1.0)),
            "mw": float(200 + rng.uniform(0, 100)),
            "rb": float(rng.integers(0, 6)),
            "ap": float(rng.uniform(0, 0.6)),
            "tpsa": float(rng.uniform(0, 90)),
        }
        if with_logs:
            row["logS"] = float(slope * row["logp"] - 0.001 * row["mw"] + 0.1 * row["rb"] + 2.0)
        rows.append(row)
    return rows


def test_ols_recovers_exact_line():
    rows = make_rows(40, seed=1)
    y = 3.0 - 2.0 * np.array([r["logp"] for r in rows])
    X = ev.design_matrix(rows)
    assert X.shape == (40, 5)          # intercept + 4 ESOL columns (C2)
    beta = ev.fit_ols(X, y)
    assert np.isclose(beta[0], 3.0, atol=1e-9)
    assert np.isclose(beta[1], -2.0, atol=1e-9)


def test_ols_rank_deficiency_raises():
    rows = make_rows(10, seed=2)
    X = ev.design_matrix(rows)
    X[:, 2] = X[:, 1]
    with pytest.raises(ValueError, match="rank deficient"):
        ev.fit_ols(X, np.zeros(10))


def test_rmse_mae_known_values():
    y = np.array([0.0, 0.0, 0.0])
    p = np.array([3.0, 0.0, -3.0])
    assert np.isclose(ev.rmse(y, p), 6 ** 0.5)
    assert np.isclose(ev.mae(y, p), 2.0)


@pytest.mark.parametrize("diff,lo,hi,label", [
    (-0.20, -0.30, -0.05, "SUCCESS"),
    (-0.20, -0.25, 0.10, "INCONCLUSIVE"),
    (0.10, 0.02, 0.20, "NO GAIN"),
])
def test_classify_three_outcomes(diff, lo, hi, label):
    assert ev.classify(diff, lo, hi) == label


def test_classify_success_needs_ci_below_zero():
    assert ev.classify(-0.30, -0.40, 0.00) == "INCONCLUSIVE"


def test_bootstrap_is_deterministic_with_fixed_seed():
    rows = make_rows(60, seed=3)
    y = np.array([r["logS"] for r in rows])
    p2 = y + np.linspace(-0.5, 0.5, len(y))
    p3 = y + np.linspace(0.5, -0.5, len(y))
    a = ev.paired_bootstrap_diff(y, p2, p3, n_boot=200, seed=ev.SEED_BOOT)
    b = ev.paired_bootstrap_diff(y, p2, p3, n_boot=200, seed=ev.SEED_BOOT)
    assert a == b
    assert a["diff"] == pytest.approx(ev.rmse(y, p2) - ev.rmse(y, p3))
    assert a["ci_low"] <= a["ci_high"]


def test_bootstrap_uses_same_indices_for_both_models():
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    r = ev.paired_bootstrap_diff(y, y.copy(), y + 0.0, n_boot=50)
    assert r["diff"] == pytest.approx(0.0)
    assert r["ci_low"] == pytest.approx(0.0)


@pytest.mark.parametrize("value,ok", [
    (float("nan"), False), (float("inf"), False), (float("-inf"), False),
    (None, False), ("abc", False), (800.0, False),      # exp(800) overflows
    (-6.0, True), (0.0, True), (12.0, True),            # ln gamma < 0 is normal
])
def test_engine_worked_definition(value, ok):
    assert ev.engine_worked(value) is ok


def test_engine_series_failure_is_none_and_run_continues():
    """Item 2: a per-molecule exception must become an engine failure (None),
    not a crash, and the temperature must be the plan's 298.15 K."""
    rows = [{"inchikey": "K-1"}, {"inchikey": "K-2"}, {"inchikey": "K-3"},
            {"inchikey": "K-4"}]

    class FakeProfiles:                      # test-only adapter stub
        def __init__(self):
            self.calls = []

        def ln_gamma_inf(self, inchikey, temperature=298.15):
            self.calls.append((inchikey, temperature))
            if inchikey == "K-2":
                raise RuntimeError("engine blew up on one molecule")
            if inchikey == "K-3":
                return {"ok": False, "error": "no sigma-DB row with formal charge 0"}
            return {"ok": True, "value": 0.25, "temperature_K": temperature}

    prof = FakeProfiles()
    ln = ev.engine_series(rows, prof)
    assert ln == [0.25, None, None, 0.25]     # raise -> None, out-of-domain -> None
    assert len(prof.calls) == 4               # every molecule was attempted
    assert all(t == ev.ENGINE_TEMPERATURE_K for _k, t in prof.calls)

    # the failures are counted, the run continues
    tune, locked = make_rows(40, seed=31), make_rows(40, seed=32)
    tune_ln = [0.01 * i for i in range(40)]           # varying -> full rank
    locked_ln = ln + [0.05 * i for i in range(36)]
    rep = ev.analyze_all(tune, locked, tune_ln, locked_ln, overlap_keys=set())
    assert rep["counts"]["engine_failures_locked"] == 2
    assert rep["counts"]["locked_engine_worked"] == 38
    assert rep["secondary"]["metrics"]["M2"]["n"] == 40   # fallback keeps all


def test_secondary_fallback_never_leaks_placeholder():
    """A failed molecule carries no ln gamma; the placeholder used to build X2
    must never appear as a reported M2 value (M2 falls back to M1 there)."""
    rows = make_rows(20, seed=41)
    betas = {"M1": np.array([1.0, 0.5, 0.0, 0.0, 0.0]),
             "M2": np.array([1.0, 0.5, 0.0, 0.0, 0.0, 1.0]),
             "M3": np.array([1.0, 0.5, 0.0, 0.0, 0.0, 0.0])}
    ln = [None] * 5 + [0.7] * 15
    worked = [False] * 5 + [True] * 15
    pred = ev.predict_all(betas, rows, ln, worked, fallback_m2=True)
    assert np.allclose(pred["M2"][:5], pred["M1"][:5])
    assert np.isfinite(pred["M2"]).all()
    with pytest.raises(ValueError, match="without fallback"):
        ev.predict_all(betas, rows, ln, worked, fallback_m2=False)


def test_fallback_m2_uses_m1_on_failed_engine():
    rows = make_rows(30, seed=4)
    betas = {"M1": np.array([1.0, 0.5, 0.0, 0.0, 0.0]),
             "M2": np.array([1.0, 0.5, 0.0, 0.0, 0.0, 1.0]),
             "M3": np.array([1.0, 0.5, 0.0, 0.0, 0.0, 0.0])}
    worked = [True, False] * 15
    ln = [1.0] * 30
    pred = ev.predict_all(betas, rows, ln, worked, fallback_m2=True)
    assert np.allclose(pred["M2"][1::2], pred["M1"][1::2])
    assert np.allclose(pred["M2"][0::2] - pred["M1"][0::2], 1.0)


def test_analyze_all_counts_and_fallback():
    tune = make_rows(80, seed=5)
    locked = make_rows(60, seed=6)
    tune_ln = [0.01 * i for i in range(70)] + [float("nan")] * 10
    locked_ln = [0.02 * i for i in range(54)] + [float("inf")] * 6
    overlap = {r["inchikey"] for r in locked[:5]}      # first 5 are engine-worked
    rep = ev.analyze_all(tune, locked, tune_ln, locked_ln, overlap)
    c = rep["counts"]
    assert c["tune_rows"] == 80 and c["tune_engine_worked"] == 70
    assert c["locked_rows"] == 60 and c["locked_engine_worked"] == 54
    assert c["engine_failures_locked"] == 6
    assert rep["primary"]["metrics"]["M2"]["n"] == 54
    assert rep["secondary"]["metrics"]["M2"]["n"] == 60
    assert c["exploratory_rows"] == 49
    assert rep["exploratory"]["label"] == "EXPLORATORY"
    assert rep["primary"]["bootstrap"]["outcome"] in {"SUCCESS", "NO GAIN", "INCONCLUSIVE"}


def _sandbox(tmp_path, *, script_hash=None, plan="p", locked="l", pool="o"):
    files = {}
    for name, text in (("plan", plan), ("locked", locked), ("pool", pool)):
        f = tmp_path / f"{name}.txt"
        f.write_text(text, encoding="utf-8")
        files[name] = f
    self_py = tmp_path / "self.py"
    self_py.write_text("x = 1\n", encoding="utf-8")
    sha_file = tmp_path / "self.sha256"
    sha_file.write_text((script_hash or ev.sha256_file(self_py)) + "\n", encoding="utf-8")
    files.update(self_py=self_py, sha_file=sha_file)
    files["expected"] = {"plan": ev.sha256_file(files["plan"]),
                         "locked": ev.sha256_file(files["locked"]),
                         "pool": ev.sha256_file(files["pool"])}
    return files


def _guard(files, confirm=ev.CONFIRM_WORD, repo=None):
    return ev.check_guard(confirm, self_path=files["self_py"], plan=files["plan"],
                          locked=files["locked"], pool=files["pool"],
                          sha_file=files["sha_file"], repo=repo or Path("."),
                          expected=files["expected"])


def test_guard_needs_confirm_word(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "git_clean", lambda repo=None: True)
    files = _sandbox(tmp_path)
    with pytest.raises(RuntimeError, match="CALISTIR"):
        _guard(files, confirm=None)
    with pytest.raises(RuntimeError, match="CALISTIR"):
        _guard(files, confirm="calistir")
    _guard(files)                                    # correct word passes


def test_guard_refuses_dirty_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "git_clean", lambda repo=None: False)
    with pytest.raises(RuntimeError, match="not clean"):
        _guard(_sandbox(tmp_path))


def test_guard_refuses_wrong_script_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "git_clean", lambda repo=None: True)
    with pytest.raises(RuntimeError, match="script SHA-256 mismatch"):
        _guard(_sandbox(tmp_path, script_hash="0" * 64))


def test_guard_refuses_missing_hash_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "git_clean", lambda repo=None: True)
    files = _sandbox(tmp_path)
    files["sha_file"].unlink()
    with pytest.raises(RuntimeError, match="missing self.sha256|missing"):
        _guard(files)


@pytest.mark.parametrize("key", ["plan", "locked", "pool"])
def test_guard_refuses_wrong_data_hash(tmp_path, monkeypatch, key):
    monkeypatch.setattr(ev, "git_clean", lambda repo=None: True)
    files = _sandbox(tmp_path)
    files[key].write_text("changed", encoding="utf-8")
    with pytest.raises(RuntimeError, match=f"{key} SHA-256 mismatch"):
        _guard(files)


def test_assert_writable_refuses_second_run(tmp_path):
    out = tmp_path / "res.json"
    ev.assert_writable(out)                  # first time ok (file absent)
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="one evaluation only"):
        ev.assert_writable(out)


def test_main_refuses_before_reading_study_data(monkeypatch):
    def boom(_path):
        raise AssertionError("study data was read before the guard passed")

    monkeypatch.setattr(ev, "load_split", boom)
    monkeypatch.setattr(ev, "git_clean", lambda repo=None: True)
    with pytest.raises(RuntimeError, match="CALISTIR"):
        ev.main([])                          # no --confirm


def test_guard_checks_section15_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "git_clean", lambda repo=None: True)
    files = _sandbox(tmp_path)
    adapter = tmp_path / "adapter.py"
    adapter.write_text("a = 1\n", encoding="utf-8")
    good = ev.sha256_file(adapter)
    files["plan"].write_text(
        "| item | value |\n|---|---|\n"
        f"| adapter `adapter.py` | `{good}` |\n", encoding="utf-8")
    files["expected"]["plan"] = ev.sha256_file(files["plan"])
    _guard(files, repo=tmp_path)                      # matching -> passes
    adapter.write_text("b = 2\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="section 15 SHA-256 mismatch"):
        _guard(files, repo=tmp_path)


def test_section15_parse_finds_adapter_and_split_script():
    rows = ev.section15_hashes(ev.PLAN)
    assert "mcp/cosmosac_pubchemqc.py" in rows
    assert "data/solubility/make_split_v2.py" in rows
    assert all(len(v) == 64 for v in rows.values())


def _e2e_env(monkeypatch, tune, locked, tune_ln, locked_ln):
    """TEST-ONLY injection: fake profile factory, injected guard and loaders.
    The real path still needs --confirm CALISTIR and every hash."""
    import sys as _sys

    factory_calls = []

    def fake_profiles(cache_dir=None):           # stand-in for make_profiles()
        factory_calls.append(cache_dir)
        return object()

    monkeypatch.setattr(ev, "make_profiles", fake_profiles)
    monkeypatch.setattr(ev, "check_guard", lambda *a, **k: None)
    monkeypatch.setattr(ev, "load_split", lambda p: tune if p == ev.TUNE else locked)
    monkeypatch.setattr(ev, "integrity_check", lambda *a, **k: None)
    monkeypatch.setattr(ev, "engine_series",
                        lambda rows, prof: tune_ln if rows is tune else locked_ln)
    monkeypatch.setattr(ev, "overlap_keys", lambda: {locked[1]["inchikey"]})
    # no sys.modules faking here: if the adapter is already imported, it must be
    # the real repo module (mcp/tests/test_cosmosac_adapter.py imports it).
    real = _sys.modules.get("cosmosac_pubchemqc")
    if real is not None:
        assert Path(real.__file__).resolve().parent == ev.REPO / "mcp"
    return factory_calls


def test_end_to_end_synthetic(tmp_path, monkeypatch):
    tune, locked = make_rows(60, seed=11), make_rows(80, seed=12)
    tune_ln = list(np.linspace(-2, 2, 60))
    locked_ln = list(np.linspace(-2, 2, 80))
    locked_ln[3] = float("nan")
    locked_ln[4] = 800.0                       # exp overflows -> engine failure
    locked_ln[5] = float("inf")
    out = tmp_path / "res.json"
    factory = _e2e_env(monkeypatch, tune, locked, tune_ln, locked_ln)

    seen = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: seen.append(out.exists()))
    assert ev.main(["--confirm", "CALISTIR", "--out", str(out)]) == 0
    assert seen and seen[0] is True            # nothing printed before the file
    assert factory == [None]                   # main() built profiles via make_profiles()

    rep = json.loads(out.read_text(encoding="utf-8"))
    for m in ("M0", "M1", "M2", "M3"):
        assert {"rmse", "mae", "n"} <= set(rep["primary"]["metrics"][m])
        assert {"rmse", "mae", "n"} <= set(rep["secondary"]["metrics"][m])
    assert {"diff", "ci_low", "ci_high", "outcome"} <= set(rep["primary"]["bootstrap"])
    assert rep["counts"]["engine_failures_locked"] == 3
    assert rep["primary"]["metrics"]["M1"]["n"] == 77     # failures excluded
    assert rep["secondary"]["metrics"]["M1"]["n"] == 80   # all molecules
    assert rep["exploratory"]["label"] == "EXPLORATORY"
    assert "provenance" in rep

    with pytest.raises(RuntimeError, match="one evaluation only"):
        ev.main(["--confirm", "CALISTIR", "--out", str(out)])


def test_end_to_end_crash_leaves_no_result_file(tmp_path, monkeypatch):
    tune, locked = make_rows(30, seed=21), make_rows(30, seed=22)
    out = tmp_path / "res.json"
    factory = _e2e_env(monkeypatch, tune, locked, [0.1 * i for i in range(30)],
                        [0.1 * i for i in range(30)])

    def boom(*_a, **_k):
        raise RuntimeError("analysis exploded")

    monkeypatch.setattr(ev, "analyze_all", boom)
    with pytest.raises(RuntimeError, match="analysis exploded"):
        ev.main(["--confirm", "CALISTIR", "--out", str(out)])
    assert not out.exists()
    assert factory == [None]                   # profiles were built before the crash


def _write_pool(path, keys, header="inchikey,cid,logS"):
    path.write_text("\n".join([header] + [f"{k},1,0.0" for k in keys]) + "\n",
                    encoding="utf-8")


def _split_fixtures(tune_n=10, locked_n=10):
    """Disjoint synthetic tune/locked sets (make_rows reuses KEY- ids)."""
    tune = make_rows(tune_n, seed=55)
    locked = make_rows(locked_n, seed=56)
    for r in locked:
        r["inchikey"] = "L-" + r["inchikey"]
    return tune, locked


def test_integrity_check_accepts_disjoint_split(tmp_path):
    tune, locked = _split_fixtures()
    pool = tmp_path / "pool.csv"
    _write_pool(pool, [r["inchikey"] for r in tune + locked])
    ev.integrity_check(tune, locked, pool_path=pool)          # no raise


def test_integrity_check_rejects_overlap(tmp_path):
    tune, locked = _split_fixtures()
    locked[0]["inchikey"] = tune[0]["inchikey"]               # plant the overlap
    pool = tmp_path / "pool.csv"
    _write_pool(pool, sorted({r["inchikey"] for r in tune + locked}))
    with pytest.raises(ValueError, match="tune/locked overlap"):
        ev.integrity_check(tune, locked, pool_path=pool)


def test_integrity_check_rejects_pool_mismatch(tmp_path):
    tune, locked = _split_fixtures()
    keys = [r["inchikey"] for r in tune + locked]
    pool = tmp_path / "pool.csv"

    _write_pool(pool, keys[:-1])                              # split molecule not in pool
    with pytest.raises(ValueError, match="not in the pool"):
        ev.integrity_check(tune, locked, pool_path=pool)

    _write_pool(pool, keys + ["GHOST-UHFFFAOYSA-N"])          # pool molecule not in split
    with pytest.raises(ValueError, match="missing from the split"):
        ev.integrity_check(tune, locked, pool_path=pool)


def test_integrity_check_never_opens_a_label_column(tmp_path, monkeypatch):
    """The pool is read through csv.reader + one header index."""
    calls = []
    tune, locked = _split_fixtures()
    pool = tmp_path / "pool.csv"
    _write_pool(pool, [r["inchikey"] for r in tune + locked])
    original = ev.column_values

    def spy(path, column, delimiter=","):
        calls.append((column, delimiter))
        return original(path, column, delimiter)

    monkeypatch.setattr(ev, "column_values", spy)
    ev.integrity_check(tune, locked, pool_path=pool)
    assert calls == [("inchikey", ",")]


def test_overlap_keys_reads_only_id_and_inchikey(tmp_path):
    raw = tmp_path / "aqsoldb.tab"
    raw.write_text(
        "ID\tSolubility\tInChIKey\tExtra\n"
        "X1\tX2\tAAAA-UHFFFAOYSA-N\tzz\n"     # Solubility holds an ID-like token
        "X2\t3.14\tBBBB-UHFFFAOYSA-N\tyy\n",
        encoding="utf-8")
    ids = tmp_path / "locked_ids.txt"
    ids.write_text("X2\n", encoding="utf-8")
    assert ev.overlap_keys(locked_ids=ids, raw=raw) == {"BBBB-UHFFFAOYSA-N"}


def test_make_profiles_import_path_in_fresh_interpreter(tmp_path):
    """main()'s exact import path must work in a clean interpreter, with no
    sys.modules faking and no conftest state (the venv also ships the official
    `mcp` package, which used to shadow the repo's mcp/ directory)."""
    import subprocess

    tools_dir = str(ev.REPO / "tools")
    code = (
        f"import sys; sys.path.insert(0, {tools_dir!r}); "
        "import solubility_eval_v2 as ev; "
        f"p = ev.make_profiles(cache_dir={str(tmp_path)!r}); "
        "print(type(p).__name__); print(p.sigma_parquet.name); "
        "print(p.params_json.name)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, timeout=300)
    assert out.returncode == 0, out.stderr
    assert "PubChemQCProfiles" in out.stdout
    assert "sigma_profiles_main.parquet" in out.stdout
    assert "sequential_final_params.json" in out.stdout













