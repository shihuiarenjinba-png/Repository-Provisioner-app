# Offline Notes Canary — commercial search-highlight PRE_IDENTITY handoff (2026-10-29)

- Factory owner/controller `plan → candidate tests (39/39) → validate → promote → guarded commit` succeeded. Factory core 108 tests and product 39 tests passed on Windows; owner Ubuntu tests passed.
- Source branch `codex/app-notes-search-highlight-promote-20261029`, SHA `e854b60bd0b701e6939bf1776e079d0e5bcb7354`, request `app-offline-notes-canary-e854b60bd0b7`, slug `offline-notes-canary`.
- Consumer features now headlessly verified: safe backup restore, tags, favorites, recent-first navigation, bounded search highlighting inside the active note body. Search never modifies stored notes. Existing schema 1 files remain compatible.
- [Windows Actions run #40878375984](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40878375984) SUCCESS. Unsigned EXE 11,496,201 bytes, SHA-256 `360eb9083915d90dedd7bca49da2b1c8065a680de0f4b1540259062a3c81c266`.
- [Artifact #12899451487](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40878375984/artifacts/12899451487) ZIP SHA-256 `06ef21748fec75eaaf8217e7eeef2eeb8e093a0c785000b81a1bc034f43b33fc`; expires 2026-11-03 13:04:15 UTC. Producing workflow ID `400618017`, path `.github/workflows/notes-search-highlight-promote.yml`, push HEAD `d8dc8754aa70a25bc434ba18fcb024c59ed5a856`.
- The ZIP was independently downloaded, and its SHA-256, PE `MZ` header, EXE SHA-256/length, receipt source/request and registration handoff were compared with GitHub metadata and Actions logs. This is not signed attestation or GUI QA.
- Partner Center selection **MSIX or PWA app** (`MSIX_OR_PWA_APP`), not EXE/MSI. User-provided Store ID `9MZ8ZZTRTS17` and Identity remain `REFERENCE_AVAILABLE`; reserved display name unverified. Do not re-request or CAS.
- `identity_attestation=NOT_VERIFIED`, `identity_cas_allowed=false`, `msix_status=NOT_BUILT`, `windows_gui_status=UNVERIFIED`, commercial quality HOLD, POST_IDENTITY and E2E HOLD.
- All five APPs are intended Store products, not disposable canaries. Consumer-valued features, 1024x768 bilingual Windows GUI review, error/restart QA, MSIX and Checker are required before submission. No sixth APP.
- 36_MIN_WINDOWS_E2E owns authenticated Identity evidence/CAS, signed MSIX, install/GUI and Checker. Draft only; no merge, Partner Center operation or Store submission.
