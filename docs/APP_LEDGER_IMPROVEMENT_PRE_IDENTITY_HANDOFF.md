# File Integrity Ledger improvement — verified APP pre-Identity handoff (2026-10-28)

This is **a new immutable improvement revision**, not a silent replacement for the original slot 3 source/receipt.

- Product: File Integrity Ledger — Offline Checksum Snapshot
- slug: `file-integrity-ledger`
- Factory source repo: `shihuiarenjinba-png/AI-App-Factory`
- source_branch: `codex/app-ledger-snapshot-size-20261028`
- source_sha: `d1108d12f7d1697af30400f97c7db39cba5e6791`
- request_id: `app-file-integrity-ledger-d1108d12f7d1`
- Factory lifecycle: genuine owner-controller improve plan → candidate tests → validate → promote; revision 2
- Regression: Ubuntu core 109/109 and product 20/20 PASS; Windows core 109/109 and product 20/20 PASS
- Windows EXE: 11,393,466 bytes, unsigned QA-only
- EXE SHA-256: `9100bbcfba20ed2768e5d2dffcb39c987466377d26a34af1e03cc166071e02ca`
- ZIP SHA-256: `c4c1f299318cf182d3d04773284990e55e270c25de28f4b8eb3baf7895548b88`
- Artifact: https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40711443897/artifacts/12826068537
- Artifact expiry: 2026-11-02 15:04:16 UTC

Verification: downloaded the Actions ZIP, independently computed its SHA-256, extracted the EXE, checked MZ header, exact byte count, EXE SHA-256, receipt source_sha/request_id and handoff registration type. This is **not** an MSIX or GUI/install QA pass.

**Partner Center selection: MSIX or PWA app** (`MSIX_OR_PWA_APP`). Proposed display name: `File Integrity Ledger`. Reserved display name has not been verified; `partner_center_display_name=null`. Identity status: `WAITING_USER_IDENTITY`. Required when its turn arrives: Store ID, reserved display name, Package Identity Name, Publisher, Publisher Display Name, PFN and Package SID. `identity_return_target=36_MIN_WINDOWS_E2E`; authenticated evidence and CAS remain with that owner.

Machine-readable records: `APP_LEDGER_IMPROVEMENT_PACKAGE_JOB.json`, `APP_LEDGER_IMPROVEMENT_EXE_RECEIPT.json`, `APP_LEDGER_IMPROVEMENT_REGISTRATION_REQUEST.json`, `APP_LEDGER_IMPROVEMENT_READY.json`. The prior immutable `deaa9f32...` source and `app-file-integrity-ledger-deaa9f324326` request remain unchanged; downstream must explicitly select the revision.

Focus Session Desk remains the first local Partner Center new-registration test. Windows GUI, MSIX, POST_IDENTITY, E2E, commercial quality and Store submission remain HOLD. No Partner Center action or Identity CAS occurred in the APP lane.
