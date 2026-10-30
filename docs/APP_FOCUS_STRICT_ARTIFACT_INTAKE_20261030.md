# APP Factory → Provisioner: actual EXE artifact verification (2026-10-30 JST)

## Scope and provenance

- Factory PR: https://github.com/shihuiarenjinba-png/AI-App-Factory/pull/35
- Windows Actions: https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/40977569390
- GitHub Actions artifact ID: `12943596081`, ZIP SHA-256: `f66ac87c8b5fa7130758a3aa9c8bf3f49e508650afe9959377ea13a0e6512c43`
- The actual artifact ZIP was downloaded and independently inspected. This is a **Factory contract-QA source**, **not** a replacement for the formally promoted Focus product source in PR #34.

## Exact source/request/EXE

| Field | Value |
|---|---|
| product | Focus Session Desk |
| slug | `focus-session-desk` |
| source_repository | `shihuiarenjinba-png/AI-App-Factory` |
| source_branch | `codex/app-preidentity-strict-job-20261030` |
| source_sha | `dd94bd2cd52a84653623f6ccdf727a6cf7903b98` |
| request_id | `app-focus-strict-dd94bd2cd52a` |
| EXE SHA-256 | `f23e646305677739eccea25cd279b86bcb52e997d82c117d4eaea5f1004cd14b` |
| EXE bytes | `11479328` |
| registration_type | `MSIX_OR_PWA_APP` |
| Partner Center selection | `MSIX or PWA app` |

Independent ZIP checks: ZIP CRC PASS, exact 3 entries PASS, strict 12-field dry-run job PASS, job↔receipt correlation PASS, MZ/PE signature PASS, EXE size PASS, EXE SHA-256 PASS. Factory PR #35 branch HEAD matched the recorded source SHA when checked; **this check is time-sensitive and must be repeated before mutation**.

## New Provisioner CLI (PR #16)

Run on the actual extracted artifact, with the Provisioner PR #16 code:

```sh
python -m tools.app_artifact_intake \
  --job preidentity-provisioner-job.json \
  --receipt preidentity/exe-receipt.json \
  --exe preidentity/focus-session-desk.exe \
  --output artifact-intake-proof.json
```

Default evidence status: `ARTIFACT_VERIFIED_HEAD_UNCHECKED`. Use `--verify-head` with an authenticated `GITHUB_TOKEN` for a **read-only** exact current branch HEAD check and `PRE_IDENTITY_READY` at check time. The new CLI was covered by synthetic-PE regression tests on Windows/Ubuntu CI; the real ZIP was independently verified, not executed through the new CLI in this run.

If the seven user-provided Identity fields are already stored in a verified source/request-specific reference file, pass `--identity-reference`. Without it, output is `IDENTITY_REFERENCE_NOT_ATTACHED`, **not** a new user request. Focus Store ID `9P6452C61N7B` and Offline Notes Store ID `9MZ8ZZTRTS17` were already received; do not re-request them. Never infer reserved display names from Factory UI titles.

## Gate boundary

This proves the real Factory artifact can be independently correlated with its strict Provisioner job, but **does not yet prove an end-to-end invocation of the new Provisioner CLI on that ZIP**. No Identity CAS, signed MSIX, install QA, human commercial review, or Store submission occurred. The 36-minute Windows/E2E owner must independently receive the job and perform live HEAD recheck before binding.
