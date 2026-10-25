# OSF pre-registration submission (2026-10-25)

Status: **SUBMITTED — pending admin approval** (see "Approval" below).
Nothing was deleted; no tag, no release, no force push.

| item | value |
|---|---|
| Registration | https://osf.io/8pbnu/ |
| Registration id | `8pbnu` |
| Title | kuro-jikken: LLM modes A/B/C (pre-registration) |
| Registered at (UTC) | `2026-10-25T12:10:01.617746` |
| Template | Open-Ended Registration (schema v3) |
| Source project | https://osf.io/zg6x2/ (private, left as-is) |
| Draft id | `6addee314d436bdc508a003e` |
| Repo commit at submit | `f9b74e6` |
| prereg file | `prereg/llm_modes_plan_v1.md` — 7584 bytes |
| prereg SHA-256 | `EE039AC64277839043929BF5A3DC96D7F16353ABA79EE5672AC8986AD01B1525` |
| Archived copy (read back from OSF) | https://osf.io/download/6addf19fbabe7aaf58d02469/ — name + 7584 bytes match local |
| `registration_responses.summary` | 372 chars, identical to the draft text |
| Subjects | Life Sciences (+ Research Methods in Life Sciences) |
| Visibility now | `public=false`, `embargoed=false`, `withdrawn=false` |
| DOI | not minted yet (`identifiers=[]`; OSF mints the DOI only when public) |

Local re-verification (2026-10-25): `sha256sum prereg/llm_modes_plan_v1.md` ==
expected hash above; `git status --porcelain` clean; `HEAD = f9b74e6` on `main`.

## Approval (why it is not public yet)

OSF creates a `RegistrationApproval` for **every** non-embargoed registration
(`api/registrations/serializers.py` → `RegistrationCreateSerializer.create` →
`registration.require_approval(auth.user)`), therefore
`pending_registration_approval = true` immediately after submit.

Per OSF official docs (help.osf.io/article/330, "Approving your Registration"):

- all admin contributors receive an **"Approval requested" email** and can
  accept/cancel within **48 hours**;
- if nobody acts, the registration is **auto-approved after 48 hours**
  → expected auto-approval ≈ **2026-10-27 12:10 UTC**;
- the date of record stays the submission date (`date_registered` above);
- while pending, the registration is visible to contributors only.

There is **no API endpoint** for this approval:

- `PATCH /v2/registrations/8pbnu/ {"public": true}` → 400
  `"An unapproved registration cannot be made public."`
- `POST /v2/registrations/8pbnu/actions/approve/` → 404
- `POST /v2/registrations/8pbnu/actions/` with `trigger=approve|reject|accept|register|make_public|retire`
  → 400 `"... is not a valid choice."`
- `trigger=submit` → 409 `"OSF Registries is an unmoderated provider."`
- `GET  /v2/registrations/8pbnu/actions/` → 200 with `0` items
- `GET  /v2/registration_approvals/`, `/v2/sanctions/` → 404 (no such API app)

## What happens next

1. Admin clicks **Accept** in the OSF approval email (fastest), **or**
   wait for the 48-hour auto-approval.
2. Then confirm: `public=true` and a DOI appears in
   `GET /v2/registrations/8pbnu/identifiers/`.
3. `python setup_osf_token.py --remove` + revoke the token on osf.io
   (deferred until step 2 is verified).

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
