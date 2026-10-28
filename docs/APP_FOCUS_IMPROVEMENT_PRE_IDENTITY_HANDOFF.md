# Focus Session Desk revision 2 — verified APP pre-Identity handoff (2026-10-29 JST)

This is a **separately pinned quality improvement**, not a replacement of the immutable original slot 2 package job.

## Product / source
- Product: Focus Session Desk — Offline Timer and Task Checklist
- slug: `focus-session-desk`
- Factory source repo: `shihuiarenjinba-png/AI-App-Factory`
- source_branch: `codex/app-focus-save-rollback-20261029`
- source_sha: `fda3f2fce807d667594313592bb5e1e7f7839511`
- request_id: `app-focus-session-desk-fda3f2fce807`
- Factory Draft PR: https://github.com/shihuiarenjinba-png/AI-App-Factory/pull/20
- Factory lifecycle: real owner-controller `improve plan → candidate tests → validate → promote`, revision 2
- Consumer fix: when a disk write fails, unsaved task, timer and language mutations are rolled back; no misleading in-memory state
- Core regression tests: Ubuntu 110/110 PASS, Windows 110/110 PASS
- Product headless tests: Ubuntu 20/20 PASS, Windows 20/20 PASS
- Windows GUI at 1024×768: **UNVERIFIED**; no install/consumer-quality claim

## Verified unsigned Windows EXE
- Size: 11,474,457 bytes
- SHA-256: `031ffc7e62dd265ff989581b67c165b451eab7127f061cf15ee537e5115e000b`
- Downloaded ZIP SHA-256: `ab970e5a6a5fb05d78af15aa09f2e8d915868cd0a6d8af191fc99f5a3e51cf4a`
- Artifact: https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40722852829/artifacts/12830748482
- Expires: 2026-11-02 16:09:11 UTC
- Independently checked downloaded ZIP members, MZ/PE header, exact EXE size/hash, source_sha, request_id and registration type
- This is **EXE_QA_UNSIGNED**, not an MSIX and not Store submission-ready

## Partner Center registration / ownership
- **Partner Center selection: MSIX or PWA app** (`MSIX_OR_PWA_APP`)
- Proposed display name: `Focus Session Desk`; reserved display name **not verified** (`partner_center_display_name=null`)
- Identity status: `WAITING_USER_IDENTITY`; Store ID and Identity values must never be guessed
- Required fields: Store ID, reserved display name, Package Identity Name, Publisher, Publisher Display Name, PFN, Package SID
- `identity_return_target=36_MIN_WINDOWS_E2E` for authenticated evidence and CAS
- Focus remains the first new Partner Center registration test; do not attempt the browser or Partner Center operation from the APP lane

## Machine-readable records
- `APP_FOCUS_IMPROVEMENT_PACKAGE_JOB.json`
- `APP_FOCUS_IMPROVEMENT_EXE_RECEIPT.json`
- `APP_FOCUS_IMPROVEMENT_REGISTRATION_REQUEST.json`
- `APP_FOCUS_IMPROVEMENT_READY.json`

Original immutable source `8b00bc4e90828c4282463826873aa8dfd2eb93f4` and request `app-focus-session-desk-8b00bc4e9082` remain intact. Downstream must explicitly select revision 2. No main/release changes, force push, merge, Partner Center action, Identity CAS, MSIX build or Store submission occurred in the APP lane.
