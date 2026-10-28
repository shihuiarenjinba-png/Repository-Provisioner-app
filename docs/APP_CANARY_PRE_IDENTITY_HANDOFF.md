# APP Canary — pinned pre-Identity handoff (2026-10-28 JST)

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
