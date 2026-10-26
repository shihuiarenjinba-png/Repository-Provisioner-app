# APP Provisioner — local package/Identity handoff (2026-10-26)

## Scope and evidence

- Repository: shihuiarenjinba-png/Repository-Provisioner-app
- Base branch: main (unchanged)
- Work branch: codex/provisioner-bootstrap-20261026 (Draft PR #1, unmerged)
- Work HEAD before this intake change: ec8d79f1d4db2457d73e4c24887d91ffa9de7092
- Intake implementation commit: b03ce19988318b8b04d68f201043533003a20112
- Intake regression tests commit: 55d24b0aba3aa3d446cff65119c62d6b7f2f1b5d
- GitHub CI: https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40330884133 — 13/13 unittest PASS, 0 failure, 0 skip, Linux only.
- Actual Windows package build: NOT RUN. Actual Partner Center lookup: NOT RUN.
- Actual GitHub Identity return: NOT RUN. Real MSIX artifact: NONE.
- Overall status: **PARTIAL / HOLD**. Unit tests are not proof of full E2E.

## Current safe intake entry point

`python package_job.py --input app-job.json --output receipt.json`

The CLI accepts **only** schema_version `"1.0"`, product_type `"APP"`, source_factory `"AI-App-Factory"`, source_repository `"shihuiarenjinba-png/AI-App-Factory"`, source_branch `"codex/factory-autoloop-20261026"`, target_owner `"shihuiarenjinba-png"`, and `dry_run: true`. It also requires a safe request_id, slug, display_name, exact non-placeholder 40-character source_sha, and the four approved requested_actions. Unknown fields, duplicate JSON keys, path traversal, cross-lane inputs and live execution requests fail closed.

A valid input produces a `DRY_RUN` receipt with a deterministic request/source key, the fixed GitHub return path `products/<slug>/store/approved-identity.json`, `expected_head_sha: null`, and explicit `NOT_BUILT`, `UNVERIFIED`, `NOT_APPLIED` statuses. It **does not** fetch source, create repositories, build MSIX, access Partner Center, or push to GitHub. The key is **not yet a durable idempotency ledger**.

The previous `provisioner.py` repository-name proposal is retained for compatibility; it is not a package implementation and `create_allowed=false`.

## Authenticated GitHub HEAD verification (read-only, optional)

A new fail-closed CLI mode is available:

`GITHUB_TOKEN=<read-only token> python package_job.py --input app-job.json --output receipt.json --verify-head`

The token must be provided through an environment variable (never committed or printed). This mode requests the **current branch HEAD** from GitHub's REST API using an authenticated read, forbids redirects and oversized responses, and rejects a stale `source_sha`. A successful check fills `expected_head_sha`, sets `source_head_verification: VERIFIED`, and **still returns DRY_RUN**. It does not build an MSIX, fetch Store Identity, or write to GitHub. If no token, invalid response, or mismatched SHA, the CLI exits HOLD without writing a receipt. The source HEAD must be rechecked immediately before any future write; this is not an authorization or durable lease.

Tests mock the GitHub API; **no authenticated live GitHub REST request was made** in this change. The previous dry-run command without `--verify-head` remains unchanged and returns `NOT_CHECKED`. Exact code/CI evidence must be taken from the latest branch HEAD rather than this historical handoff's earlier 13-test snapshot.

## Remaining implementation blockers (local code owner)

1. The Factory stacked PR #3 `handoff_request.py` still emits the **old repository-creation request**. A new compatible Factory job producer is required before actual dispatch. Do not treat the two JSON formats as interchangeable.
2. Implement authenticated read-only GitHub source/branch HEAD verification and pinned-SHA checkout. Before returning Identity, re-fetch actual branch HEAD; the job's `source_sha` is not by itself proof of current branch HEAD.
3. Implement local Windows build, package inspection, package SHA-256 and signature verification, with explicit QA_UNSIGNED status where applicable. Never execute arbitrary job-supplied commands.
4. Implement authenticated Partner Center product identity lookup/reservation only with approved permissions; Store ID is not derivable from MSIX/PFN/SID. Keep tokens, cookies and private keys out of Git.
5. Adapt the **verified** Identity evidence to Windows-all-auto `all_auto.identity_route` / `identity_commit`. Their input schema is `schema_version: 1`, not the public `"1.0"` intake schema. Apply only with the atomic `expectedHeadOid` check and never overwrite an existing identity file.
6. Add durable, atomic idempotency ledger and crash recovery, Windows QA, authenticated GitHub API mock/real-read tests, failure cases and an approved E2E run.
7. The real product source, approved Store Identity and approved PNG assets are prerequisites for Factory MSIX export. Factory→Windows-all-auto Artifact intake and local QA are separate ChatGPT-side tasks.

No OpenAI API key, paid Codex API, fabricated Store ID, main/release direct write, unauthorized PR merge or Store submission is required or permitted.
