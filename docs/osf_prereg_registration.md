# OSF pre-registration submission (2026-10-25)

## Gate re-check 2026-10-26 (entry to the LLM A/B/C pilot)

Read-only re-verification before the pilot harness work. No token was used for the
reads below (the registration is public).

| item | value observed on 2026-10-26 | source |
|---|---|---|
| `public` | **true** | `GET https://api.osf.io/v2/registrations/8pbnu/` -> 200 |
| `pending_registration_approval` | **false** | same |
| `reviews_state` / `revision_state` | **accepted** / **approved** | same |
| `date_registered` | **2026-10-25T12:10:01.617746** (unchanged) | same |
| DOI | **10.17605/OSF.IO/8PBNU** | `GET .../8pbnu/identifiers/` -> 1 identifier, `category: doi` |
| DOI resolves | **302 -> https://osf.io/8pbnu/** | `GET https://doi.org/10.17605/OSF.IO/8PBNU` |
| Title | kuro-jikken: LLM modes A/B/C (pre-registration) | same |
| Local prereg SHA-256 | **EE039AC64277839043929BF5A3DC96D7F16353ABA79EE5672AC8986AD01B1525** (= expectation) | `Get-FileHash prereg/llm_modes_plan_v1.md` |

Note: the v2 registration object reports `attributes.doi = null`; the DOI is exposed by the
`identifiers` endpoint (and resolves). This is an OSF API shape difference, not a missing DOI.

The Freeze-1 gate (registration public + approved, before any benchmark run) is **satisfied**.

The environment gate that day was **NOT** satisfied: `ASCService` (PID 2980) and `ASCTray`
(PID 22840) were running, and the author's instruction is to stop the pilot start in that
case. No model was started.


Status: **APPROVED — PUBLIC** (approved 2026-10-25T12:55:08Z, ~45 min after submit,
by the admin approval link in the OSF notification email).
Nothing was deleted; no tag, no release, no force push.

| item | value |
|---|---|
| Registration | https://osf.io/8pbnu/ |
| Registration id | `8pbnu` |
| **DOI** | **https://doi.org/10.17605/OSF.IO/8PBNU** (resolves, `responseCode 1`) |
| Title | kuro-jikken: LLM modes A/B/C (pre-registration) |
| Registered at (UTC) | `2026-10-25T12:10:01.617746` (kept after approval) |
| Approved at (UTC) | `2026-10-25T12:55:08` (DOI mint timestamp) |
| Template | Open-Ended Registration (schema v3) |
| Source project | https://osf.io/zg6x2/ (private, left as-is) |
| Draft id | `6addee314d436bdc508a003e` |
| Repo commit at submit | `f9b74e6` |
| prereg file | `prereg/llm_modes_plan_v1.md` — 7584 bytes |
| prereg SHA-256 | `EE039AC64277839043929BF5A3DC96D7F16353ABA79EE5672AC8986AD01B1525` |
| Archived copy (read back from OSF) | https://osf.io/download/6addf19fbabe7aaf58d02469/ — name + 7584 bytes match local |
| `registration_responses.summary` | 372 chars, identical to the draft text |
| Subjects | Life Sciences (+ Research Methods in Life Sciences) |
| Visibility | `public=true`, `embargoed=false`, `withdrawn=false` (anonim `GET /v2/registrations/8pbnu/` → 200, `public=true`) |
| Moderation | `reviews_state=accepted`, `revision_state=approved`, `pending_registration_approval=false` |
| Contributor | YASİN YAĞCI (admin) |

Local re-verification (2026-10-25): `sha256sum prereg/llm_modes_plan_v1.md` ==
expected hash above; `git status --porcelain` clean; `HEAD = f9b74e6` on `main`.

## Approval (how it completed)

OSF creates a `RegistrationApproval` for **every** non-embargoed registration
(`RegistrationCreateSerializer.create` → `registration.require_approval()`), so
`pending_registration_approval = true` right after submit.

Per OSF official docs (help.osf.io/article/330, "Approving your Registration"):

- all admin contributors receive an **"Approval requested" email** and can
  accept/cancel within **48 hours**;
- if nobody acts, the registration is **auto-approved after 48 hours**
  → expected auto-approval ≈ **2026-10-27 12:10 UTC**;
- the date of record stays the submission date (`date_registered` above);
- while pending, the registration is visible to contributors only.

**Resolved:** the admin used the **approve** link in the *"Pending Registration -
Admin Notification"* email (sender `openscienceframework-noreply@osf.io`,
2026-10-25 15:10 local). API verification 2026-10-25 12:55 UTC: `public=true`,
`pending_registration_approval=false`, `reviews_state=accepted`,
`revision_state=approved`, DOI minted, anonymous `GET` → 200.

There is **no API endpoint** for this approval — attempts kept as evidence:

- `PATCH /v2/registrations/8pbnu/ {"public": true}` → 400
  `"An unapproved registration cannot be made public."`
- `POST /v2/registrations/8pbnu/actions/approve/` → 404
- `POST /v2/registrations/8pbnu/actions/` with `trigger=approve|reject|accept|register|make_public|retire`
  → 400 `"... is not a valid choice."`
- `trigger=submit` → 409 `"OSF Registries is an unmoderated provider."`
- `GET  /v2/registrations/8pbnu/actions/` → 200 with `0` items
- `GET  /v2/registration_approvals/`, `/v2/sanctions/` → 404 (no such API app)

## Closure checklist

- [x] Registration public: https://osf.io/8pbnu/
- [x] DOI resolves: https://doi.org/10.17605/OSF.IO/8PBNU
- [x] Archived file verified: `llm_modes_plan_v1.md`, 7584 bytes
- [x] `registration_responses.summary` = 372 chars, unchanged
- [x] Repo record committed + pushed (`6cda0e8` + this update)
- [ ] API token removed: `python setup_osf_token.py --remove` + delete it on
      osf.io → Settings → Personal Access Tokens (owner's action)

## Reproduce the checks

```powershell
# local
Get-FileHash .\prereg\llm_modes_plan_v1.md -Algorithm SHA256   # expect EE039A…B1525
git status --porcelain ; git rev-parse HEAD                    # expect clean, f9b74e6

# OSF (token from OSF_TOKEN env only; never echoed)
GET https://api.osf.io/v2/registrations/8pbnu/                 # public / pending_registration_approval
GET https://api.osf.io/v2/registrations/8pbnu/identifiers/     # DOI after approval
GET https://api.osf.io/v2/registrations/8pbnu/files/osfstorage/  # llm_modes_plan_v1.md, 7584
```
