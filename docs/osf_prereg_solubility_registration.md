# OSF pre-registration - solubility sigma feature (2026-10-25)

Status: **PUBLIC - APPROVED** (registered 2026-10-25T16:45:45Z UTC).
Nothing deleted; no tag, no release, no force push. Project and registration are
**not** zg6x2 / 8pbnu: those belong to the earlier LLM A/B/C pre-registration and
were not touched.

| item | value |
|---|---|
| Registration | https://osf.io/uce8d/ |
| Registration id | `uce8d` |
| Title | kuro-jikken: solubility sigma feature (pre-registration) |
| Registered at (UTC) | `2026-10-25T16:45:45.274708` (`date_created` 16:45:45.287436) |
| Template | Open-Ended Registration (schema `5df83f7dd28338001ac0ab0d`) |
| Source project | https://osf.io/5tyvs/ (private, as intended) |
| Draft id | `6ade2f7bf8840c7f6e259c76` |
| Repo commit at submit | `dc402c1989a8db1fd124d6fabd00e2e242b15b80` (`HEAD` = `origin/main`) |
| Plan file | `prereg/solubility_sigma_feature_plan_v1.md` - **10,589 bytes** (223 lines) |
| Plan SHA-256 | `56ef478994e987931869ae5e7f9b19576779c67629bc06edb2e012c21717f5c2` |
| Archived copy (registration storage) | `Archive of OSF Storage/solubility_sigma_feature_plan_v1.md` - **10,589 bytes**, sha256 identical |
| `registration_responses.summary` | **409 chars**, identical to the draft text |
| Subjects | `Physical Chemistry` (`584240da54be81056cecaac2`); OSF automatically listed its parents `Chemistry` and `Physical Sciences and Mathematics` |
| Visibility | `public=true`, `pending_registration_approval=false`, `reviews_state=accepted`, `revision_state=approved`; embargoed=false, withdrawn=false |
| Moderation | `pending_registration_approval=true`, `reviews_state=initial`, `revision_state=unapproved` |
| DOI | **`10.17605/OSF.IO/UCE8D`** |
| Anonymous read | `GET /v2/registrations/uce8d/` -> **200** |

## What was uploaded and verified

Only the plan file. The label-bearing data files (`pool_v2.csv`, `split_tune_v2.csv`,
`split_locked_v2.csv`) were **not** uploaded: the plan already fixes their hashes in
section 15, and files cannot be added to a registration after submit.

Verification chain (all three agree):

1. `PUT` upload -> HTTP **201**
2. listing on OSF -> `10589` bytes, `sha256 56ef4789...f5c2`
3. real download of the bytes -> `10589` bytes, `sha256 56ef4789...f5c2`

Project description (verbatim):

```
Repo commit: dc402c1989a8db1fd124d6fabd00e2e242b15b80 (github.com/KuroShinHQ/kuro-jikken, main).
Plan file: prereg/solubility_sigma_feature_plan_v1.md
Plan SHA-256: 56ef478994e987931869ae5e7f9b19576779c67629bc06edb2e012c21717f5c2
No study engine run, no error or feature value used in design decisions; label-free sanity run disclosed in section 16.
```

Summary (verbatim, 409 chars):

```
Does one engine feature (ln gamma-infinity, solute in water at 298.15 K; NIST COSMOSAC + PubChemQC sigma DB) cut logS error versus an equally cheap RDKit TPSA feature on held-out molecules? M0 published ESOL; M1 ESOL OLS; M2 = M1 + engine; M3 = M1 + TPSA; primary M2 vs M3. 50/50 split seed 20261027, 800 gate; margin 0.10; bootstrap 10,000 seed 20261028; SUCCESS / NO GAIN / INCONCLUSIVE. Hashes: section 15.
```

## Subject note

The subject was attached as the single leaf `Physical Chemistry`
(`584240da54be81056cecaac2`) via
`PUT /v2/draft_registrations/{id}/relationships/subjects/`. OSF itself expanded the
taxonomy and returned three rows (leaf + its two ancestors). No parent subject was
chosen or added by hand.

## Approval (same mechanism as 8pbnu)

OSF requires admin approval for every non-embargoed registration, so
`pending_registration_approval=true` right after submit, with
`reviews_state=initial`. Completion needs the **approve** link in the
"Pending Registration - Admin Notification" email; 48 hours without action means
automatic approval and `date_registered` stays the submission date. There is no
API endpoint for this approval (evidence: `docs/osf_prereg_registration.md`).

Until then: registration not readable anonymously (401), no DOI.

**Resolved 2026-10-26:** approval arrived, so this paragraph is historical. The
record is now `public=true` with DOI `10.17605/OSF.IO/UCE8D` and an anonymous
`GET` returns 200; `date_registered` is unchanged. A dated OSF *Update* on this
record (`uce8d`) was accepted on 2026-10-26. Separate record, separate state: the
Freeze 2 *Update* for `8pbnu` is no longer a draft. The author approval line is
present (Freeze 2 approved 2026-10-26) and OSF accepted that Update on
2026-10-26 (`docs/osf_freeze2_update_draft.md`).

## Token hygiene

Token read from `OSF_TOKEN` (env or HKCU fallback); never printed, never written to
disk. Cleanup is deliberately **not** run yet: `setup_osf_token.py --remove` plus
deleting the token at osf.io -> Settings -> Personal Access Tokens is the owner's
action, after this registration is closed out.

## Reproduce the checks

```powershell
# local
Get-FileHash .\prereg\solubility_sigma_feature_plan_v1.md -Algorithm SHA256   # 56ef4789...f5c2
git status --porcelain ; git rev-parse HEAD                                    # clean, dc402c1

# OSF (token from OSF_TOKEN only; never echoed)
GET https://api.osf.io/v2/registrations/uce8d/                     # public, pending_registration_approval
GET https://api.osf.io/v2/registrations/uce8d/files/osfstorage/    # -> Archive of OSF Storage/...
GET https://api.osf.io/v2/registrations/uce8d/identifiers/         # DOI after approval
```

Helper used for every step (outside the repo, so the tree stays clean):
`C:\KuroshinHQ\_hub\scripts\osf_sigma_registration.py`
(`check`, `project`, `schemas`, `subjects`, `draft`, `setsummary`, `setsubject`,
`submit`, `regstatus`, `regfiles`).
