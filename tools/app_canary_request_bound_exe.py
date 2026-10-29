"""Build the one pinned request-bound APP EXE on Windows, without Store Identity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from package_identity_provisioner import Job, ProductConfig, SourceManager, load_json

JOB_PATH = ROOT / "docs" / "APP_CANARY_PACKAGE_JOB.json"
EXPECTED_REQUEST_ID = "app-offline-notes-canary-b83702c89489"
EXPECTED_SOURCE_SHA = "b83702c8948991cc3bd31745db5df64afaf6010f"
EXPECTED_SOURCE_BRANCH = "codex/app-canary-offline-notes-20261027"
EXPECTED_SLUG = "offline-notes-canary"


def validate_canary_job(raw: dict, config: ProductConfig) -> Job:
    job = Job.validate(raw, config)
    if (job.request_id != EXPECTED_REQUEST_ID
            or job.source_sha != EXPECTED_SOURCE_SHA
            or job.source_branch != EXPECTED_SOURCE_BRANCH
            or job.slug != EXPECTED_SLUG
            or job.dry_run
            or "BUILD_WINDOWS" not in job.requested_actions):
        raise ValueError("job differs from the immutable reviewed Offline Notes Canary request")
    return job


def verify_exe_receipt(job: Job, output: Path) -> dict:
    exe = output / (job.slug + ".exe")
    receipt_path = output / "exe-receipt.json"
    if (not output.is_dir() or output.is_symlink() or exe.is_symlink()
            or receipt_path.is_symlink() or not exe.is_file() or not receipt_path.is_file()
            or {p.name for p in output.iterdir()} != {exe.name, receipt_path.name}):
        raise ValueError("request-bound EXE evidence files are missing or unexpected")
    receipt = load_json(receipt_path, 32_768)
    expected = {
        "schema_version": 1,
        "stage": "PRE_IDENTITY_WINDOWS_EXE",
        "status": "EXE_QA_UNSIGNED",
        "source_repository": job.source_repository,
        "source_factory": job.source_factory,
        "source_branch": job.source_branch,
        "source_sha": job.source_sha,
        "request_id": job.request_id,
        "product_type": job.product_type,
        "slug": job.slug,
        "display_name": job.display_name,
        "executable": exe.name,
        "official_identity_status": "NOT_COLLECTED",
        "store_id": None,
        "msix_status": "NOT_BUILT",
    }
    for key, value in expected.items():
        if receipt.get(key, object()) != value:
            raise ValueError("EXE receipt provenance mismatch: " + key)
    if not isinstance(receipt.get("executable_bytes"), int) or isinstance(receipt["executable_bytes"], bool):
        raise ValueError("EXE receipt size is not an integer")
    if exe.stat().st_size != receipt["executable_bytes"] or not 1024 < exe.stat().st_size <= 300 * 1024 * 1024:
        raise ValueError("EXE receipt size mismatch")
    with exe.open("rb") as handle:
        if handle.read(2) != b"MZ":
            raise ValueError("EXE does not have a PE header")
        handle.seek(0)  # hash the entire PE, including its MZ header
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != receipt.get("executable_sha256"):
        raise ValueError("EXE receipt SHA-256 mismatch")
    return receipt


def verify_clean_factory_checkout(source: Path, expected_sha: str) -> None:
    """Reject dirty, untracked and ignored files before running pinned Factory code.

    Git checkout --detach at an unchanged HEAD does not necessarily discard
    pre-existing local edits. The request-bound builder must never execute them.
    """
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Factory source checkout must be a real directory")
    try:
        def git(*args: str) -> str:
            return subprocess.run(
                ["git", *args], cwd=source, capture_output=True,
                text=True, check=True, timeout=30,
            ).stdout.strip()

        root = git("rev-parse", "--show-toplevel")
        head = git("rev-parse", "HEAD")
        dirty = git("status", "--porcelain=v1", "--untracked-files=all", "--ignored")
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Factory checkout integrity could not be verified") from exc
    if Path(root).resolve() != source.resolve() or head != expected_sha:
        raise ValueError("Factory checkout does not match the pinned source root/SHA")
    if dirty:
        raise ValueError("Factory checkout contains modified, untracked or ignored files")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        parser.error("actual Windows runner required")
    config = ProductConfig.load(ROOT / "config.json")
    job = validate_canary_job(load_json(JOB_PATH), config)
    if args.output.exists() or args.output.is_symlink():
        parser.error("refusing to overwrite existing request-bound evidence")
    source = SourceManager().acquire(job, args.source_dir)
    verify_clean_factory_checkout(source, job.source_sha)
    builder = source / "tools" / "build_windows_exe.py"
    if builder.is_symlink() or not builder.is_file():
        raise ValueError("committed Factory EXE builder missing")
    subprocess.run(
        [sys.executable, str(builder), "--root", str(source), "--slug", job.slug,
         "--expected-sha", job.source_sha, "--source-branch", job.source_branch,
         "--request-id", job.request_id, "--output", str(args.output)],
        cwd=source, check=True, timeout=1800,
    )
    receipt = verify_exe_receipt(job, args.output)
    print(json.dumps({"status": "REQUEST_BOUND_EXE_VERIFIED",
                      "request_id": receipt["request_id"],
                      "source_sha": receipt["source_sha"],
                      "exe_sha256": receipt["executable_sha256"],
                      "exe_bytes": receipt["executable_bytes"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
