"""Build data/manifest.json from the files themselves (sizes and hashes are computed)."""
import hashlib
import json
import pathlib
import sys

SIGMA = pathlib.Path(r"C:\KuroshinHQ\_hub\data\formulation_sigma")
TDB = pathlib.Path(r"C:\KuroshinHQ\_hub\data\alloy_tdb_mgf")

R = []
R.append(dict(id="aqsoldb_20261025", title="AqSolDB aqueous solubility snapshot",
    path="data/solubility/raw/aqsoldb_20261025.tab", in_repo=True, licence="CC0-1.0",
    domain={"quantity": "aqueous logS", "temperature_K": 298.15, "rows": 9982},
    used_by=["mcp/esol.py"], not_for=["non-aqueous", "salts/metals", "mixtures"]))
R.append(dict(id="pubchemqc_sigma_profiles", title="PubChemQC sigma profiles",
    path=str(SIGMA / "sigma_profiles_main.parquet"), in_repo=False, licence="external-research",
    domain={"quantity": "COSMO-SAC sigma profiles", "rows": 361583, "columns": 164},
    used_by=["mcp/cosmosac_pubchemqc.py", "tools/gamma_validation.py"],
    not_for=["molecules missing from the index", "charged species", "performance claims"]))
R.append(dict(id="pubchemqc_sigma_index", title="PubChemQC sigma index (InChIKey)",
    path=str(SIGMA / "sigma_profile_index.parquet"), in_repo=False, licence="external-research",
    domain={"rows": 361583, "columns": 11}, used_by=["mcp/cosmosac_pubchemqc.py"],
    not_for=["named lookup outside PubChemQC"]))
R.append(dict(id="sigma_refit_params", title="COSMO-SAC refit constants",
    path=str(SIGMA / "sequential_final_params.json"), in_repo=False, licence="MIT",
    domain={"quantity": "refit interaction constants"},
    used_by=["mcp/cosmosac_pubchemqc.py"], not_for=["use with other sigma tables"]))
for name, eid in (("mc_al_v2.032.pycalphad.tdb", "matcalc_mc_al"),
                  ("mc_fe_v2.059.pycalphad.tdb", "matcalc_mc_fe"),
                  ("mc_ni_v2.034.pycalphad.tdb", "matcalc_mc_ni")):
    R.append(dict(id=eid, title=f"MatCalc open TDB {name}", path=str(TDB / name),
        in_repo=False, licence="ODbL-1.0", domain={"quantity": "CALPHAD Gibbs energy"},
        used_by=["mcp/tools_server.py"], not_for=["creep", "oxidation", "corrosion"]))
R.append(dict(id="hsp_chemicals", title="Hansen solubility table in chemicals 1.5.2",
    path=None, in_repo=False, licence="MIT",
    domain={"quantity": "Hansen dD/dP/dH", "key": "CASRN"},
    used_by=["mcp/tools_server.py", "tools/build_pool.py"], not_for=["mixtures (petrolatum, mineral oil)", "polymers"]))
# chemicals 1.5.2 thermal tables were in the committed manifest but missing from
# this builder; kept here so a regeneration never drops a row (SABIT #1).
R.append(dict(id="chemicals_thermal", title="Tm/Hfus tables in chemicals 1.5.2 (OPEN_NTBKM and other compilations)",
    path=None, in_repo=False, licence="MIT",
    domain={"quantity": "melting temperature and enthalpy of fusion", "key": "CASRN"},
    used_by=["tools/wax_melting.py", "tools/build_pool.py"],
    not_for=["mixtures (petrolatum and paraffin wax have no Hfus)", "wax content",
             "rheology", "performance claims"]))

R.append(dict(id="gamma_inf_literature", title="Measured gamma-infinity in water (Straver & de Loos 2005)",
    path="tools/gamma_validation.py", in_repo=True, licence="citation-only",
    domain={"quantity": "gamma-infinity", "temperature_K": 298.15, "solutes": 9},
    used_by=["tools/gamma_validation.py"], not_for=["redistribution", "other solvents"]))

# S4: the two cosmetics sources. Raw files stay outside the repository; only the
# derived pool (data/cosmetics) is committed, with these hashes pinning the input.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cosmetics_sources as CS  # noqa: E402

obf = CS.RAW_DIR / CS.OBF_NAME
_cos = sorted(CS.RAW_DIR.glob("cosing_inci_*.json"))
obf_stats = CS.count_tokens(CS.iter_products(obf))[2] if obf.is_file() else {}
R.append(dict(id="obf_products_20261028", title="Open Beauty Facts product dump (2026-10-28)",
    path=str(obf), in_repo=False, licence="ODbL-1.0 + DbCL-1.0",
    domain={"quantity": "cosmetic products with label data",
            "products": obf_stats.get("products"),
            "with_inci": obf_stats.get("with_inci")},
    used_by=["tools/build_cosmetics.py"],
    not_for=["market share", "concentration", "safety or efficacy claims"]))
if _cos:
    _doc = json.loads(_cos[-1].read_text(encoding="utf-8"))
    R.append(dict(id="cosing_labels_20261028", title="CosIng records for label names (2026-10-28)",
        path=str(_cos[-1]), in_repo=False, licence="CC-BY-4.0",
        domain={"quantity": "INCI identity, function, restrictions",
                "records": _doc.get("count"), "names_queried": _doc.get("names_queried")},
        used_by=["tools/build_cosmetics.py"],
        not_for=["formulation design", "safety assessment", "market claims"]))

out = []
for row in R:
    row = dict(row)
    if row["path"]:
        p = pathlib.Path(row["path"]) if pathlib.Path(row["path"]).is_absolute() else pathlib.Path(__file__).resolve().parents[1] / row["path"]
        row["bytes"] = p.stat().st_size
        row["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    out.append(row)
doc = {"version": 1, "generated": "2026-10-26",
       "note": "A dataset missing here must not be used by any engine.",
       "allowed_licences": ["CC0-1.0", "ODbL-1.0", "ODbL-1.0 + DbCL-1.0", "MIT",
                            "citation-only", "external-research", "CC-BY-4.0"],
       "datasets": out}
dst = pathlib.Path(__file__).resolve().parents[1] / "data" / "manifest.json"
dst.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print("wrote", dst, len(out), "datasets")
