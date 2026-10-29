# APP slot 5 — Image Inventory revision 2 append safety (2026-10-29)

## Consumer defect and fix
Previously the Add action rescanned every already-inventoried image. If an old image moved or disappeared, that inventory row vanished silently during an unrelated Add action. The audited Factory improvement introduces `append_images` to preserve existing snapshot rows while inspecting only newly selected files. Duplicate/invalid new files are reported without dropping existing rows.

## Factory evidence
[Draft PR #21](https://github.com/shihuiarenjinba-png/AI-App-Factory/pull/21); real owner-controller improve plan → 26 candidate tests → validate → promote revision 2; source `28fd060c2400bd9382cd1a5a14cd70b63b724de3`, request `app-offline-image-inventory-desk-28fd060c2400`, branch `codex/app-image-inventory-append-safety-20261029`. The original `16b6a772952ca0988f2ae2f8b5f4db2e59ec5877` source/request remain immutable.

## EXE evidence
[Actions #40731750753](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40731750753) SUCCESS, [artifact #12834803795](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40731750753/artifacts/12834803795), expiry 2026-11-02 17:03 UTC. Independently downloaded ZIP SHA-256 `a87e9f0f19acd675617ec2e59eb7a15483fa1921bf510add3ecb37e4db0f4b0d`; unsigned EXE 11392480 bytes SHA-256 `6cbdc5334f1e24c79c2549274ed905bd185cbb15461536564ca6b3c35e646e61`. MZ and PE signatures, exact source/request/slug and handoff metadata independently checked.

## Registration and owner boundary
**Partner Center selection: MSIX or PWA app**; `MSIX_OR_PWA_APP` is the final MSIX route, never EXE_OR_MSI_APP. Suggested display name `Offline Image Inventory Desk`; reserved exact display name **unverified** and `partner_center_display_name=null`. Identity `WAITING_USER_IDENTITY`, 7 official fields pending, no fabricated values or CAS. Identity return owner `36_MIN_WINDOWS_E2E` at `AUTHENTICATED_IDENTITY_EVIDENCE_AND_CAS`.

Use `docs/APP_IMAGE_INVENTORY_IMPROVEMENT_PACKAGE_JOB.json`, `docs/APP_IMAGE_INVENTORY_IMPROVEMENT_EXE_RECEIPT.json`, `docs/APP_IMAGE_INVENTORY_IMPROVEMENT_REGISTRATION_REQUEST.json`. Focus Session Desk remains the next Partner Center registration test. Windows GUI/install, MSIX, E2E, commercial quality remain HOLD. Do not generate sixth APP or mutate main/release, force push, merge, submit Store.
