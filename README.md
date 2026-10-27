# Repository-Provisioner-app

`AI-App-Factory` で確定したAPPを、SHA固定でWindowsビルド／MSIX検査し、認証済みPartner Centerの公式Identityと一致した場合だけFactory作業ブランチへ返す中間工程です。新規GitHubリポジトリ作成、Store ID推測、Store提出、main/releaseへの書込みは行いません。

## 実行

Python 3.12以降とGit/GitHub CLIを使用します。DRY_RUNは外部読取・ビルド・GitHub書込みを行いません。

```powershell
python provisioner.py --input examples/job.dry-run.json --output test-results/dry-run.json
```

実処理ではFactory作業ブランチの現在HEADと同じ `source_sha`、認証済みPartner Centerセッションから人間が照合した証跡JSON、Windowsビルド環境が必要です。GitHub返却は明示的な `--apply` のときだけ行います。

```powershell
python provisioner.py --input job.json --output result.json `
  --official-identity C:\secure\partner-center-evidence.json --apply
```

返却先は設定で固定されています。

- repository: `shihuiarenjinba-png/AI-App-Factory`
- branch: `codex/factory-autoloop-20261026`
- path: `products/<slug>/store/approved-identity.json`

入力・出力契約は `schemas/`、運用とHOLD項目は `docs/LOCAL_PROVISIONER_HANDOFF.md` を参照してください。ローカル状態と生成物は `.provisioner-state/` と `.provisioner-work/` に製品タイプ別で保存され、Gitには追加されません。

## APP pre-Identity Windows EXE stage (Draft)

When the exact pinned Factory checkout contains the committed
`tools/build_windows_exe.py`, Provisioner now passes the Factory job's
`slug` and `source_sha` to that builder on the local Windows machine.
It collects a real EXE, a SHA-256 receipt, and a fresh artifact path.

An EXE-only result is **HOLD**, not a verified MSIX or Store candidate.
The response retains `package.kind=exe`, `package.sha256` and
`package.path`, with `next_stage=OBTAIN_OFFICIAL_IDENTITY_AND_BUILD_MSIX`.
It does **not** call Partner Center, write approved-identity.json, or
invent a Store ID from an EXE. MSIX generation and official Identity
round-trip still require the authenticated local operator.

Companion Factory implementation: 
https://github.com/shihuiarenjinba-png/AI-App-Factory/pull/11

The current `config.json` still pins `codex/factory-autoloop-20261026`.
That branch must contain a real committed product and the reviewed builder
before the live pipeline can run. This Draft branch does not change that
allowlisted source branch.


## APP: verified Identity return after a pre-Identity EXE

The APP Factory's SHA-pinned Windows EXE is a real build artifact, but has **no
MSIX Identity**. The Provisioner now supports the next separate step: after
an operator supplies the authenticated Partner Center evidence JSON via
`--official-identity`, it can write `products/<slug>/store/approved-identity.json`
to the allowlisted Factory work branch with `--apply`, using GitHub's
`expectedHeadOid=source_sha` compare-and-swap guard.

The returned JSON retains `request_id`, `product_type`, `source_factory`,
`source_repository`, `source_branch`, `source_sha`, `expected_head_sha`,
`slug`, `display_name`, official Store ID/Name/Publisher/Version, and
the inspected EXE `package_sha256`, `package_kind=exe`, and byte count.
**The EXE SHA is not an MSIX SHA**; the later Windows MSIX packaging step must
independently hash the finished MSIX and verify that it contains exactly the
pinned EXE bytes. Neither EXE inspection nor the returned JSON creates or
guesses an official Store ID.

Even when the Identity write succeeds, the overall result is **HOLD** with
`next_stage=GITHUB_PACKAGE_PINNED_EXE_AS_MSIX`, not E2E PASS or Store-ready.
No `windows_all_auto_record` is issued for an EXE-only build. Without
operator evidence, the result remains HOLD at
`OBTAIN_OFFICIAL_IDENTITY_AND_BUILD_MSIX`; without `--apply`, no GitHub
write is attempted. The Factory source branch must match `config.json`
exactly and must still be at the job's `source_sha` when applying the
Identity return. Parallel branch changes produce CONFLICT, not silent retry.

Do not run a second PyInstaller build during the subsequent MSIX stage:
reuse and hash-check the already inspected EXE. MSIX generation, actual
Factory handoff Artifact, Windows-all-auto intake, and local Windows QA
remain separate unverified stages.
