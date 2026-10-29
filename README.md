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

返却先リポジトリは製品系統ごとに固定し、返却ブランチは入力されたFactory作業ブランチを検証して使用します。`codex/*` 以外、`main`、`release`、不正なブランチ名は拒否します。

- repository: `shihuiarenjinba-png/AI-App-Factory`
- branch: 入力 `source_branch` と同じ安全な `codex/*` 作業ブランチ
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

`config.json` keeps the lane's default branch for examples, while each job's
safe `codex/*` `source_branch` is preserved through checkout, HEAD validation,
and atomic Identity return. A live branch must contain a real committed product
and the reviewed builder before the pipeline can run.
