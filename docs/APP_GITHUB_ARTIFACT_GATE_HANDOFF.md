# APP cohort — authenticated GitHub artifact gate

Owner: APP 00-minute lane (Provisioner). Integration owner: 36-minute Windows/E2E lane.

## Execute on a runner with GitHub CLI and read-only Actions artifact permission

```bash
export GH_TOKEN="<ephemeral GitHub token with actions:read>"
python -m tools.app_cohort_github_gate --output app-cohort-github-gate.json
```

The script **does not need Windows GUI, a local install, Partner Center login, or Store Identity**. On GitHub Actions, pass `GH_TOKEN: ${{ github.token }}` in the step environment and grant `actions: read` permission. Run it against the exact checked-out Provisioner Draft PR SHA. It does not use or modify main/release.

The script derives five artifact URLs from the current improvement revisions, not the historical top-level source fields. It fetches GitHub API metadata for each exact artifact ID, requires a non-expired artifact, matches its SHA-256 digest, Actions run ID and source branch, then verifies that the producing run is completed/successful **and** comes from the pinned product-specific workflow ID/path with a `push` event. The artifact metadata's workflow HEAD must equal the producing run's HEAD. Only then does it download the archive and call `verify_binary_dispatch` to inspect ZIP/EXE bytes and provenance. It refuses partial results and does not accept a user-supplied URL. It writes a JSON report only after all five pass, and never overwrites an existing report.

**Important:** An Actions workflow HEAD SHA can differ from the promoted product `source_sha` because the Factory promotion commits during the run. The ZIP receipt and handoff prove product source correlation; the API metadata independently ties the archive to its Actions run and branch. The report is not a cryptographic signed build attestation.

The workflow identity allowlist in `tools/app_cohort_github_gate.py` is intentionally frozen for these five current improvement artifacts. A new legitimate Factory build must update the source/request/artifact receipts **and** its reviewed workflow identity together, then rerun the gate. Never silently accept a different successful workflow on the same branch. The JSON evidence now records the producing workflow ID/path and artifact-to-run HEAD match.

Current pinned artifacts are short-lived and expire on 2026-11-02 UTC unless regenerated. If any artifact expires, fail closed; do not silently substitute an older revision or alter the pinned SHA. Rebuild through the authorized Factory lifecycle, pin a new immutable revision and retest before dispatch.

## Downstream handoff boundary

The 36-minute Windows/E2E owner may consume `app-cohort-github-gate.json` as **authenticated GitHub API metadata + downloaded bytes** evidence. It must separately verify any signed attestation, Identity CAS authorization, MSIX packaging, Windows GUI/install, and Store readiness. In particular, `identity_cas_allowed=false`, `msix_status=NOT_BUILT`, and `windows_gui_status=UNVERIFIED` remain unchanged.

Partner Center selection: **MSIX or PWA app** (`MSIX_OR_PWA_APP`), never EXE/MSI merely because the intermediate artifact is EXE. Offline Notes Canary's user-provided Store Identity remains `REFERENCE_AVAILABLE` and must not be re-requested. Focus Session Desk remains the next *new* Partner Center registration test when authorized.

No external product API, SaaS, login, telemetry, certificate-store change, security-policy change, merge, or Store submission is performed.
