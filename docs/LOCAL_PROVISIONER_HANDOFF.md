# LOCAL_PROVISIONER_HANDOFF — APP（現行統合記録）

更新日: 2026-10-27 (Asia/Tokyo)

## APP Identity-only batch return（2026-10-29追記）

`identity_only_return.py`は、1件のGitHub PRE_IDENTITY APP jobと、ローカル
Windowsの認証済みUI receiptを受け取る。書込みは既存
`GitHubReturnClient`へ委譲し、別のCAS実装は持たない。

Store IdentityとPackage Versionは分離する。Identity取得段階ではVersionを
生成せず、`package_version_gate=HOLD`とする。初回CASは`APPLIED`、同じ内容の
再開は`EXISTING_VERIFIED`。既存ファイル差異、source/queue digest drift、誤った
return target、別製品receiptは`CONFLICT`で停止する。

この入口はpackage upload、Store submission、certification、publish、pricingを
実行しない。

## 現行判定

**HOLD — オフライン実装完了／ライブ作成未確認。** APPのactive productは監督台帳上`null`。製品を新規生成せず、実MSIX、認証済みPartner Center Identity、Factory CAS書戻し、Windows-all-auto受領はいずれも未実施。Store提出は0件。

## 現行Git/GitHub基準

- Repository: https://github.com/shihuiarenjinba-png/Repository-Provisioner-app
- 統合元: `codex/app-exe-request-provenance-20261027-1300` / `cdf355e928e86ad8032cec40e3ca9567f68b8cae`
- ローカル作業ブランチ: `codex/e2e-belt-connection-20261027`
- 現行Draft PR: https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/pull/10
- 作業HEAD: 本資料を含む最新`git rev-parse HEAD`を正とする（最終報告とDraft PRに記録）
- 変更概要: Factory jobの動的で安全な`codex/*` branch、7項目相関、SHA固定取得、実EXE/MSIX検査、PFN/Package SID/署名/SHA-256、既存Identity完全照合、GraphQL CAS、秘密情報伏字、PowerShell 7優先。
- main/release変更、Identity上書き、Store提出: なし。

## 現行テスト・契約

- 自動テスト: **78件 / PASS 77 / FAIL 0 / SKIP 1**（Windows symlink権限制約）
- DRY_RUN: mockで副作用0を確認。実APP jobはactiveでないため実行していない。
- 共通Schema正規化SHA-256: job `0fbdaf38d25563bf60f756fbf2dd03468517584fb7b05b1bf5f942bf27c1d599` / result `1264f0285283c77aceb2956d687ff3898657578b82ba37ff475a8565f8709310`
- 起動: `python provisioner.py --input job.json --output result.json`。公式証拠を明示する場合のみ`--official-identity <secure-local-path>`、レビュー後のCAS返却のみ`--apply`。
- 必要権限: Factory metadata/read・contents/read、指定作業ブランチcontents/write、対象製品を閲覧できるPartner Center認証。token/PFX/cookieはGitに置かない。
- 返却先: 入力で検証済みのFactory作業ブランチ上`products/<slug>/store/approved-identity.json`。`main`/`release`は拒否。

## 次の一手

APP active productが正式に指定された後、そのrequest_id・Factory branch・source SHAを再照合し、DRY_RUN→Windows実ビルド→認証済みIdentity照合→CAS返却の順で再開する。active product不在の間はHOLDを維持する。

---

## 既存リモート実装の履歴（以下は履歴。上記の現行統合記録が優先）

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
---

## 現行Package + Identity実装の引継ぎ

# LOCAL_PROVISIONER_HANDOFF — APP

更新日: 2026-10-27 (Asia/Tokyo)

## 判定

**HOLD: オフライン実装、モック検証、DRY_RUNは完了。実製品MSIX生成、Partner Center公式ID取得、Factoryへの実返却は未確認。** テストPASSだけを完成とは扱わない。

## GitHub情報

- Repository: https://github.com/shihuiarenjinba-png/Repository-Provisioner-app
- 基準: `main` / `9ba2a574740d94247dcd3149429c1b933187e867`
- 作業ブランチ: `codex/provisioner-bootstrap-20261026`
- 作業開始時HEAD: `ec8d79f1d4db2457d73e4c24887d91ffa9de7092`
- 資料生成時の実装HEAD: `91ecdf4`（リモート先行9コミットを保持してrebase後）
- コミット: `830f643 docs(app): document authenticated HEAD check...`、`91ecdf4 feat: implement package identity round-trip provisioner`
- Draft PR: https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/pull/1
- CI検証済みHEAD: `573bef37bf2e476c7bd43493bd90cc449b467dfb`
- GitHub Actions: SUCCESS — https://github.com/shihuiarenjinba-png/Repository-Provisioner-app/actions/runs/40382366650
- Provisioner作業ブランチpush: 成功（非force）。
- 差分: Package+Identity CLI、共通Schema、SHA固定取得、Windows build adapter、MSIX/署名/PFN/SID解析、型別台帳・排他、公式Identity照合、GitHub CAS返却、CI、テスト。資料更新commit自体のSHAはDraft PRの最新HEADを正とする。

## テスト情報

- 自動テスト: 58件 / PASS 57 / FAIL 0 / SKIP 1（Windows sandboxでsymlink作成不可の1件）
- Python compile: PASS
- DRY_RUN: PASS。build、Partner Center、GitHub writeは0回。
- 実Factory Identity書込: 未実施。Factory側commit SHAなし。
- 実Windows build/MSIX: 未実施。モックMSIX解析のみPASS。
- Partner Center公式ID: 未取得。Store ID推測機能はない。
- 作成・削除したテストリポジトリ: なし。

## 起動と契約

```powershell
python provisioner.py --input job.json --output result.json
python provisioner.py --input job.json --output result.json `
  --official-identity C:\secure\partner-center-evidence.json --apply
```

- 入力: `schemas/job-v1.0.schema.json`
- 出力: `schemas/result-v1.0.schema.json`
- Factory入口: `APP` / `AI-App-Factory`
- 返却先: `shihuiarenjinba-png/AI-App-Factory`、`codex/factory-autoloop-20261026`、`products/<slug>/store/approved-identity.json`
- Windows-all-auto: `type=app`、`expected_head_sha`付きのIdentity返却契約。
- 成功条件: 実MSIXと公式Identityの完全一致、およびGraphQL CASが返す実commit SHA。

## 必要な権限

- GitHub: Factory metadata/read、contents/read、作業ブランチへのcontents/write。main/release権限は不要。
- Partner Center: 対象製品を閲覧できる認証済み担当者。MFA/CAPTCHA回避や未承認の名前予約は禁止。
- 証明書/token/PFXは環境Secret、credential store、証明書ストアで管理し、Gitへ保存しない。

## 重複・復旧

- `.provisioner-state/app/` でrequest fingerprintを記録。同一完了案件は再ビルドせず結果を再掲。
- 同request_idで別入力/SHA、同時起動、既存Identity相違、HEAD不一致は`CONFLICT`。
- HOLD/RETRYABLE_FAILUREは同一入力で再開可能。429/5xx/timeoutは書込済みか再照会してから再試行。
- 既存approved-identity.jsonは一致時のみ`EXISTING_VERIFIED`。自動上書きしない。

## HOLD項目

1. Git credentialによるProvisioner pushは成功したが、`gh auth status`のtokenは失効中。Factory Identity API書込権限は未確認。
2. 承認済み実Factory job、実Windows build、実MSIXが未提供。
3. 認証済みPartner Centerでの公式Identity確認が未実施。
4. Factory→Provisioner→Windows-all-autoのE2EはChatGPT側の別工程。

CIはWindows/Ubuntuでテストとcompileのみ実行し、権限は`contents: read`。Store提出は行わない。
