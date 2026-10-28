# Offline Notes Canary — revision 2 PRE_IDENTITY handoff (2026-10-29 JST)

## Consumer safety fix
- Fixed two real data-loss risks: a failed previous-version backup write no longer allows replacing the only good notes database, and TXT export cannot overwrite the open notes JSON, its .bak path, or hardlink aliases.
- Owner-controlled Factory `plan → candidate 22 tests → validate → promote` revision 2. No manual state bypass. Draft [PR #23](https://github.com/shihuiarenjinba-png/AI-App-Factory/pull/23).
- [Factory + Windows EXE run #40750841064](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40750841064) SUCCESS. Factory core 108/108 and Notes functional 22/22 on Ubuntu and Windows.
- Immutable **new** source branch `codex/app-notes-backup-export-safety-20261029`, SHA `c4431473da715e1f0cb31a04841263332e7137e5`, request `app-offline-notes-canary-c4431473da71`, slug `offline-notes-canary`. Original source `b83702c8948991cc3bd31745db5df64afaf6010f` / original request `app-offline-notes-canary-b83702c89489` remain untouched.
- Real Windows unsigned EXE: `offline-notes-canary.exe`, 11491935 bytes, SHA-256 `4febda28ba11e841eb75a8aeb6f6604fba5393f55079affc4ec6564ce5a29f7a`; [Artifact #12842579676](https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40750841064/artifacts/12842579676), ZIP SHA-256 `dfd8907a28cb7abfe7eae310ea66b738f5dd9612aa0fbe1a4fb742ea9e99a4bf`. Independently downloaded and verified ZIP entries, MZ/PE AMD64, size, EXE SHA, source SHA and request ID. Expires 2026-11-02 19:05 UTC.
- Machine-readable files: `APP_NOTES_IMPROVEMENT_{PACKAGE_JOB,EXE_RECEIPT,IDENTITY_REFERENCE,REGISTRATION_REQUEST}.json` plus `APP_COHORT_ROTATION.json` and four fail-closed tests.

## Identity / Partner Center routing
- **Partner Center selection: MSIX or PWA app**, `MSIX_OR_PWA_APP`; intermediate EXE does not change registration category.
- User-provided Store Identity reference exists (Store ID `9MZ8ZZTRTS17`); its seven values are copied into a source/request-correlated **reference only**, with `reserved_display_name=null`. No need to request the Identity again. It is not an authenticated Partner Center attestation or permission for CAS.
- `identity_attestation=NOT_VERIFIED`, `identity_cas_allowed=false`, `msix_status=NOT_BUILT`, `windows_gui_status=UNVERIFIED`, `factory_stable=false`. Commercial quality and E2E remain HOLD.
- **36_MIN_WINDOWS_E2E** owns authenticated evidence verification, Identity CAS, pinned EXE→MSIX, local Windows GUI/install and checker/E2E. Focus Session Desk remains the **first new Partner Center product creation test**; do not create another product or request an already received Identity.
- No main/release write, force push, merge, Store action or Partner Center browser operation.
