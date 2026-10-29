# Offline Notes Canary — commercial restore PRE_IDENTITY handoff (2026-10-29)

- Factory owner/controller `plan → candidate tests (29/29) → validate → promote → commit` succeeded. Windows headless regressions also passed.
- Source branch `codex/app-notes-commercial-restore-20261029`, SHA `0b3a6698ca117e678f257dad3e68bfbf212190fa`, request `app-offline-notes-canary-0b3a6698ca11`, slug `offline-notes-canary`.
- New consumer feature: bilingual Restore backup UI action, recover valid `.bak` to a NEW unused JSON file; refuse existing targets, corrupt backups and symlinks. Previous save/backup/TXT export protections retained.
- [Windows Actions run #40862129632](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40862129632) SUCCESS. Unsigned EXE 11,492,431 bytes, SHA-256 `6ae7d8ec3180e8f88cde963e8ae742cbf8a617cf6196d95fdba3e2408e7962af`.
- [Artifact #12891174971](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40862129632/artifacts/12891174971) ZIP SHA-256 `2a0228c713ea76bca0a3d1ccbc8598a8b64755cc25e51c3e01d7c23a554a455f`; expires 2026-11-03 11:02:51 UTC. Producing workflow ID `400504889`, path `.github/workflows/notes-commercial-restore.yml`, push HEAD `26c691ae263b303375a4bf0e2a58c6bfedeb1408`.
- ZIP bytes, EXE PE header/hash/length, receipt source/request and registration handoff were independently cross-checked. This is not a signed attestation or GUI QA.
- Partner Center selection **MSIX or PWA app** (`MSIX_OR_PWA_APP`), not EXE/MSI. Store ID `9MZ8ZZTRTS17` and other user-provided Identity fields remain `REFERENCE_AVAILABLE`; reserved display name unverified. No re-request or CAS.
- `identity_attestation=NOT_VERIFIED`, `identity_cas_allowed=false`, `msix_status=NOT_BUILT`, `windows_gui_status=UNVERIFIED`, commercial quality HOLD, POST_IDENTITY and E2E HOLD.
- All five APPs are intended Store products, not disposable canaries. Consumer-valuable features, 1024x768 bilingual Windows GUI review, error/restart QA, MSIX and Checker are required before submission. No sixth APP.
- 36_MIN_WINDOWS_E2E owns authenticated Identity evidence/CAS, signed MSIX, install/GUI and Checker. Draft only; no merge, Partner Center operation or Store submission.
