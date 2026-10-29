# APP Offline Notes cycle 9 — strict Provisioner handoff (review-only)

- Product: Offline Notes Canary — Searchable Scratchpad
- Slug: `offline-notes-canary`; product_type: `APP`
- Factory repository: `shihuiarenjinba-png/AI-App-Factory`
- Source branch: `codex/app-notes-new-save-no-clobber-20261030`
- Immutable source SHA: `2bc5eb249c5d23ee269e75f3b27ee2a7be359791`
- Request: `app-offline-notes-canary-2bc5eb249c5d`
- Previous reported unsigned EXE: 11,496,095 bytes, SHA-256 `f2e99c6c65f688cedc1da0bbe7486bb7f8e9c1268987bea65dcea906309c2475`
- Factory Windows run: https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40936743336
- EXE artifact ID: `12925116983`. The SHA and size above are **prior run evidence**, not independently downloaded or reverified by this change.
- Final Store packaging family: `MSIX`; Partner Center selection: **MSIX or PWA app** (`MSIX_OR_PWA_APP`). The intermediate EXE does not change the registration category.
- Identity: Store ID `9MZ8ZZTRTS17` and remaining identity fields are user-provided references only. Reserved Partner Center display name is **not verified**; no authenticated UI evidence, Identity CAS or Store action is claimed.

## Files and boundary

`APP_NOTES_CYCLE9_STRICT_JOB.json` has **exactly** the required keys from `schemas/job-v1.0.schema.json`: `target_owner` and `dry_run` are present, and routing/Identity metadata is absent. Its default is `dry_run=true` for safe contract testing.

`APP_NOTES_CYCLE9_IDENTITY_REFERENCE.json` correlates the previously received user Identity to this source/request but does **not** attest it. Never ask the user for the same Identity again.

`tools/app_preidentity_strict_handoff.py` validates the actual downloaded Windows PE bytes against the exact EXE receipt, validates source SHA/request ID, and then emits **two separate JSON files**: strict Provisioner job and rich APP registration/36-minute handoff. It refuses to overwrite either output. It does not execute a build or contact Partner Center.

Run after extracting the trusted Windows Actions artifact (paths are examples):

```powershell
python -m tools.app_preidentity_strict_handoff `
  --receipt dist/preidentity/exe-receipt.json `
  --exe dist/preidentity/offline-notes-canary.exe `
  --identity-reference docs/APP_NOTES_CYCLE9_IDENTITY_REFERENCE.json `
  --expected-source-sha 2bc5eb249c5d23ee269e75f3b27ee2a7be359791 `
  --expected-request-id app-offline-notes-canary-2bc5eb249c5d `
  --job-output dist/strict-provisioner-job.json `
  --routing-output dist/app-registration-handoff.json
```

The job is dry-run unless `--execute-build` is explicitly provided. That flag changes only the generated job; it does not perform the build.

## Gates and next owner

- Factory lifecycle / functional tests / EXE / Windows GUI: previous Factory PR #30 report indicated PASS, **not rerun by this Provisioner change**.
- Strict schema generation and test suite: pending this PR's CI.
- PRE_IDENTITY_READY: **conditional** on downloading and independently verifying exact EXE/receipt with the generator.
- POST_IDENTITY: HOLD pending 36-minute Windows owner authenticated evidence and safe CAS.
- Official MSIX, Checker/install QA, E2E, consumer-quality signoff and Store submission: HOLD.
- Handoff owner: `36_MIN_WINDOWS_E2E`; Identity return target must retain this immutable source SHA and request ID. Do not overwrite old request/receipt or blindly replace another branch's files.
- No new sixth APP, main/release write, merge, Store submission, Partner Center browser operation, or guessed Identity.
