# APP Canary — pinned pre-Identity handoff (2026-10-28 JST)

## 2026-10-28 — cloud-first APP cohort registration handoff

- **Partner Center selection: MSIX or PWA app** (machine code `MSIX_OR_PWA_APP`). The unsigned intermediate Windows EXE is NOT an `EXE_OR_MSI_APP` Store registration.
- **Canary cloud PRE_IDENTITY_READY:** native Factory promotion, 18 functional tests, immutable `b83702c8948991cc3bd31745db5df64afaf6010f` and `app-offline-notes-canary-b83702c89489`, verified request-bound EXE SHA-256 `373b069b5a5f5ebdfea8785edc1c165030b6988b688739105585f34ed4501ab0`. Windows GUI/install still **UNVERIFIED**; local Windows is temporarily unavailable, so this is nonblocking for additional cloud cohort products, NOT a Windows QA PASS.
- New APP-owned `tools/app_registration_contract.py` validates pinned job/EXE receipt and optionally binds the **user-provided** Identity reference to source/request/slug. It **never** attests Partner Center authentication, performs CAS, or modifies Identity. `docs/APP_COHORT_REGISTRATION_REQUEST.json` records `REFERENCE_AVAILABLE` and `identity_cas_allowed=false`; `docs/APP_COHORT_ROTATION.json` tracks the bounded five-product cohort (1/5 currently cloud-ready, NOT stable).
- The user has already supplied Store ID `9MZ8ZZTRTS17` and the other reference values. **Do not ask again.** Reserved Partner Center display name was not independently verified; leave it null, not guessed.
- **36-minute owner next:** authenticated Identity evidence review, source/request attestation, CAS only after verification, MSIX from pinned EXE, checker/E2E. **00-minute owner next:** distinct second product on `codex/app-cohort-rotation-20261028` via authorized native Factory lifecycle; frozen canary source branch unchanged. Never edit `factory/state.json` directly.
- Provisioner CI run [40639596924](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40639596924) PASS on Windows and Ubuntu including ten new registration contract tests.

---


## 2026-10-28 14:08 JST — clean-source guard + fresh request-bound EXE verified

- **CODE FIX (APP-owned Provisioner only):** [commit 49f2ab33](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/commit/49f2ab339062350e25b55de126d9ea04f5f02133) adds `verify_clean_factory_checkout` before executing the Factory builder. An existing Git checkout can have the correct HEAD while retaining modified, untracked or ignored files; these now fail closed instead of running altered local source. The [test refinement c551d4ea](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/commit/c551d4eaabe6f2792450a2e31558daf493536f81) verifies ignored payloads are truly ignored by Git. Three new regression tests cover clean checkout, dirty/ignored checkout and SHA mismatch.
- **CI PASS:** [Provisioner Windows+Ubuntu CI 40636040523](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40636040523) SUCCESS at `c551d4ea`.
- **NEW Windows EXE PASS:** [run 40636033797](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40636033797) SUCCESS, [Artifact 12793163698](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40636033797/artifacts/12793163698). Artifact ZIP independently downloaded and verified: ZIP SHA-256 `d63f8d80262b7191f1dce332a2108c777335ddabd932adc191374ccf3ba0b779`, EXE **11,491,423 bytes**, SHA-256 `373b069b5a5f5ebdfea8785edc1c165030b6988b688739105585f34ed4501ab0`. Windows PE `MZ`, `PE\\0\\0`, AMD64, PE32+ checked. Exact two files: `offline-notes-canary.exe`, `exe-receipt.json`. Receipt source SHA/request_id/slug match the immutable canary. ZIP digest matches GitHub artifact digest. Expires **2026-11-02 05:07:41 UTC**.
- **Source unchanged:** Factory PR #14 `b83702c8948991cc3bd31745db5df64afaf6010f`; request_id `app-offline-notes-canary-b83702c89489`; slug `offline-notes-canary`. No new APP, no Store Identity applied. Artifact EXE bytes may differ across PyInstaller builds; use exact hash/receipt of the chosen artifact, not a prior EXE hash.
- **36-minute owner next:** prefer this latest request-bound EXE for Windows GUI QA at 1024x768, save/restart/recovery, then authenticated Identity attestation, CAS, MSIX, Windows-checker and E2E. **Windows GUI and commercial quality remain unverified**. Identity reference already available in Windows-all-auto PR #19; do not re-request. The 00-minute lane did not touch central E2E, Identity scheduler or Partner Center.

---

## Latest: request-bound Windows EXE VERIFIED (2026-10-28 13:05 JST)

- **NEW PASS**: [Provisioner Windows workflow run 40630198770](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40630198770) on PR #10 work branch at Provisioner commit `7d4a9da745bf6ae399b0b7d5a738b20a5f94fcff`; [Artifact 12791411541](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40630198770/artifacts/12791411541).
- The runner checked the **current Factory branch HEAD** against pinned `b83702c8948991cc3bd31745db5df64afaf6010f`, checked out that exact commit, ran the committed Windows PyInstaller builder with `--source-branch` and `--request-id`, and verified the resulting receipt and EXE.
- `request_id=app-offline-notes-canary-b83702c89489`, `source_branch=codex/app-canary-offline-notes-20261027`, `source_sha=b83702c8948991cc3bd31745db5df64afaf6010f`, `slug=offline-notes-canary`.
- **Independently downloaded artifact ZIP and rechecked its bytes**: ZIP SHA-256 `1c0f0718f1eb39e372c22f0f1c7934e6ea676ac95cd53f641f3c3f2ab33a7ec7`; EXE SHA-256 `a3bcec9bc181d7fa5f755ec3fb61bcbe140f23671430595dc87fbde9479df0e5`, 11,490,228 bytes, PE `MZ` header, exactly two files (`offline-notes-canary.exe`, `exe-receipt.json`). Receipt has exact non-null request_id and source SHA; `status=EXE_QA_UNSIGNED`, `store_id=null`, `msix_status=NOT_BUILT`.
- Full Provisioner CI [40630203771](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40630203771): Windows and Ubuntu SUCCESS, including nine new fail-closed request-bound EXE tests. The initial run exposed a SHA-256 verification bug (omitted `MZ` bytes); fixed in `7d4a9da7` before successful rerun.
- **Use the NEW request-bound artifact for downstream handoff**, never the earlier Factory EXE-only QA receipt with `request_id=null`. Artifact expires **2026-11-02 04:04:52 UTC**; copy/queue under the 36-minute owner's approved evidence flow before expiry.
- **36-minute Windows/E2E owner next**: real Windows GUI launch/save/reopen/recovery at 1024×768, validate authenticated Partner Center evidence against the user-provided Identity reference already in Windows-all-auto PR #19, then Identity CAS, MSIX, Windows-checker and central E2E. The 00-minute APP lane did not apply Identity, authenticate to Partner Center, modify central E2E records or submit to Store.
- **Gates**: Factory lifecycle PASS; Factory CI PASS; Provisioner CI PASS; **request-bound Windows EXE PASS**; Linux UI evidence partial, Windows GUI HOLD; PRE_IDENTITY_READY partial (Windows GUI unverified); POST_IDENTITY_READY HOLD; E2E HOLD; commercial quality not tested.

---

## Exact source and controller evidence

- Product: `offline-notes-canary` only. No new APP generation.
- Factory: [Draft PR #14](https://github.com/shihuiarenjinba-png/AI-App-Factory/pull/14), branch `codex/app-canary-offline-notes-20261027`.
- **Immutable product source SHA:** `b83702c8948991cc3bd31745db5df64afaf6010f`. Keep this Factory branch HEAD frozen until the request-bound Windows build consumes it; Provisioner verifies HEAD equality.
- Product paths: `products/offline-notes-canary/{main.py,manifest.json,README.md,tests/test_smoke.py}`.
- State after native `python factory.py plan` -> exact candidate **18/18 PASS** -> `python factory.py validate` -> `python factory.py promote`: `stage=improve`, `revision=1`, `slug=offline-notes-canary`. Controller `factory.py` and state were **not manually edited** to bypass validation.
- [Factory core CI](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40623993334): SUCCESS at source SHA.

## Historical Factory EXE-only QA artifact (not request-bound)

- [Windows EXE workflow](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40623989309): SUCCESS.
- [Artifact 12789160163](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40623989309/artifacts/12789160163), name `factory-preidentity-exe-offline-notes-canary-b83702c8948991cc3bd31745db5df64afaf6010f`; expires **2026-11-02 02:59:32 UTC**.
- `offline-notes-canary.exe`: **11,491,304 bytes**, starts with `MZ`, SHA-256 `8056bc40df17c8a57714e599e788a6146dec0c59fd02c7283dc854cfffca2429`.
- Downloaded ZIP SHA-256 `1ea86fecf4987f92a6ae189abfddddb3f4386da0cbff6d05d666ef6af568f8d3`. Embedded receipt matched the EXE hash and pinned source SHA.
- **Important:** EXE receipt has `request_id: null`, `status: EXE_QA_UNSIGNED`, `store_id: null`. This proves a real unsigned Windows EXE was generated, **not** a request-bound EXE ready for the immutable MSIX path. Do not modify the receipt to fake correlation.

## Provisioner request to execute on local Windows

- Canonical staged job: [`docs/APP_CANARY_PACKAGE_JOB.json`](./APP_CANARY_PACKAGE_JOB.json).
- **request_id:** `app-offline-notes-canary-b83702c89489`.
- `source_branch`: `codex/app-canary-offline-notes-20261027`; `source_sha`: `b83702c8948991cc3bd31745db5df64afaf6010f`.
- Use current `provisioner.py` / `package_identity_provisioner.Job.validate` (accepts validated `codex/*` branches), **not** the older `package_job.py` / Factory `package_handoff_request.py`, which still hard-code `codex/factory-autoloop-20261026`.
- Stage only: `dry_run=false` describes the intended live job, **not permission to apply Identity**. A read-only dry run can be performed with a separate temporary copy and must not reuse the same request_id with different payload in a persistent ledger.
- The pinned job has now produced a **new request-bound EXE receipt** in Provisioner Actions (see latest section). A local Windows rerun is optional and must preserve exact source/request correlation; do not use the historical Factory EXE-only receipt.
- [Provisioner Draft PR #10](https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/pull/10) owns this job and [APP progress](./APP_LOOP_PROGRESS.json).

## UI, Identity and downstream gates

- Linux Xvfb at 1024x768: 13 post-promotion GUI checks PASS for first-run, toolbar visibility, new note, unsaved search, save, English switch, restart/reopen, malformed JSON error and data preservation. Evidence is local, **not Windows GUI PASS**.
- Store Identity: **REFERENCE_AVAILABLE** from user-provided Partner Center values. Store ID `9MZ8ZZTRTS17`; full values are already in **Windows-all-auto stacked PR #19** `user_provided_store_identities.json`. Do **not** ask user to resend, guess values, authenticate to Partner Center, or CAS from this reference alone.
- 36-minute Windows/E2E owner: verify authenticated Identity evidence and 7-field correlation only after the request-bound EXE is verified, then MSIX build, Windows GUI/install QA, Windows-checker and central E2E backlog. Identity scheduler and central E2E ledger remain 36-minute owned; this APP handoff does not edit them.
- **Gates (updated):** Factory lifecycle PASS; Factory and Provisioner CI PASS; request-bound EXE PASS; Windows UI HOLD; PRE_IDENTITY_READY partial; POST_IDENTITY_READY HOLD; E2E HOLD; commercial quality untested. No main/release writes, merges, Store submission or Identity CAS.
