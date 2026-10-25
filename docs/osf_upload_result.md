# OSF upload result (2026-10-25)

- OSF project: https://osf.io/kjye6 (public = true)
- Files uploaded and verified — name, size AND sha256 all match local files:

| file | bytes | sha256 (local == OSF) |
|---|---|---|
| plan.md | 2681 | d3f0c45d7ebb5372… |
| LOCK.sha256 | 82 | cb5d68e3b49dcbbc… |
| LOCK_ACCESS_LOG.md | 46 | 7cec057b281c41cf… |

- Honesty note: plan and lock were committed to Git BEFORE the evaluation
  (timestamps in git history); OSF upload happened AFTER `--final`, so this
  round has no external pre-registration. Rule for the next round: OSF first.
- Archive DOI: https://doi.org/10.5281/zenodo.23633859 (Zenodo, v0.1.0)
- Tool: `tools/osf_upload.py` (`--dry-run` | `--confirm` | `--public`)
- Technical note: documented v2 `?meta=` upload returned 400 ("Missing
  required parameter 'name'"); working flow = provider upload link with
  `?name=&kind=file&size=` query params (waterbutler v1), verified 3/3.
