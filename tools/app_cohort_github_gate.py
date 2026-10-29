"""Download the five pinned APP Actions artifacts and run the real-byte gate.

Read-only with respect to GitHub and Partner Center. Requires an authenticated
GitHub CLI (GH_TOKEN or GITHUB_TOKEN). The downloaded ZIPs are temporary and
never used as evidence of signed attestation, Identity CAS, GUI, or MSIX.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from tools.app_artifact_binary_verify import MAX_ZIP
from tools.app_cohort_dispatch import build_dispatch, verify_binary_dispatch
from tools.app_registration_contract import RegistrationContractError

REPO = "shihuiarenjinba-png/AI-App-Factory"
URL = re.compile(
    r"https://github[.]com/shihuiarenjinba-png/AI-App-Factory/"
    r"actions/runs/([1-9][0-9]*)/artifacts/([1-9][0-9]*)\Z"
)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RegistrationContractError("Actions binary gate: " + reason)


def parse_location(row: dict) -> tuple[int, int]:
    match = URL.fullmatch(row.get("artifact_url", ""))
    require(match is not None, row.get("slug", "?") + " untrusted artifact URL")
    return int(match.group(1)), int(match.group(2))


def validate_metadata(row: dict, metadata: dict) -> tuple[int, int]:
    """Bind the authenticated Actions artifact metadata to the pinned handoff.

    The workflow HEAD may differ from the promoted product source SHA because
    promotion itself commits during the run. Do not falsely require equality.
    """
    run_id, artifact_id = parse_location(row)
    require(isinstance(metadata, dict), "metadata is not an object")
    require(type(metadata.get("id")) is int and metadata["id"] == artifact_id,
            "artifact ID mismatch")
    require(metadata.get("expired") is False, "artifact expired or expiry unknown")
    size = metadata.get("size_in_bytes")
    require(type(size) is int and 0 < size <= MAX_ZIP, "artifact size out of bounds")
    require(metadata.get("digest") == "sha256:" + row["artifact_zip_sha256"],
            "Actions artifact digest mismatch")
    api = f"https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}"
    require(metadata.get("url") == api and
            metadata.get("archive_download_url") == api + "/zip",
            "artifact API URL mismatch")
    workflow = metadata.get("workflow_run")
    require(isinstance(workflow, dict) and
            workflow.get("id") == run_id and
            workflow.get("head_branch") == row["source_branch"],
            "Actions workflow run/branch mismatch")
    return run_id, artifact_id

def validate_workflow_run(row: dict, run: dict) -> None:
    """Require a successful, completed Factory Actions run for each artifact.

    Artifact bytes and digest alone do not establish the producing run's
    outcome. The workflow HEAD can legitimately differ from promoted source.
    """
    run_id, _ = parse_location(row)
    require(isinstance(run, dict), "workflow run is not an object")
    require(type(run.get("id")) is int and run["id"] == run_id,
            "workflow run ID mismatch")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            "workflow run not successful")
    require(run.get("head_branch") == row["source_branch"],
            "workflow run source branch mismatch")
    repository = run.get("repository")
    require(isinstance(repository, dict) and repository.get("full_name") == REPO,
            "workflow run repository mismatch")
    require(run.get("html_url") == f"https://github.com/{REPO}/actions/runs/{run_id}",
            "workflow run URL mismatch")
    require(isinstance(run.get("head_sha"), str) and
            re.fullmatch(r"[0-9a-f]{40}", run["head_sha"]) is not None,
            "workflow run HEAD is invalid")


def _gh_api(path: str, destination: Path | None = None) -> dict | None:
    command = ["gh", "api", "--method", "GET", path]
    try:
        if destination is None:
            process = subprocess.run(command, capture_output=True, timeout=40,
                                     check=False)
            require(process.returncode == 0, "GitHub metadata request failed")
            try:
                result = json.loads(process.stdout)
            except (UnicodeError, ValueError) as exc:
                raise RegistrationContractError(
                    "Actions binary gate: invalid GitHub metadata JSON"
                ) from exc
            require(isinstance(result, dict), "GitHub metadata is not an object")
            return result
        with destination.open("xb") as output:
            process = subprocess.run(command, stdout=output,
                                     stderr=subprocess.DEVNULL, timeout=180,
                                     check=False)
        require(process.returncode == 0, "GitHub artifact download failed")
        require(0 < destination.stat().st_size <= MAX_ZIP,
                "downloaded artifact size out of bounds")
        return None
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RegistrationContractError(
            "Actions binary gate: GitHub CLI unavailable or timed out"
        ) from exc


def fetch_and_verify() -> dict:
    require(bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")),
            "GH_TOKEN or GITHUB_TOKEN required")
    require(shutil.which("gh") is not None, "GitHub CLI (gh) required")
    dispatch = build_dispatch()
    with tempfile.TemporaryDirectory(prefix="app-pinned-artifacts-") as temp:
        artifact_map = {}
        api_proofs = []
        for row in dispatch["products"]:
            run_id, artifact_id = parse_location(row)
            endpoint = f"/repos/{REPO}/actions/artifacts/{artifact_id}"
            metadata = _gh_api(endpoint)
            validate_metadata(row, metadata)
            run = _gh_api(f"/repos/{REPO}/actions/runs/{run_id}")
            validate_workflow_run(row, run)
            target = Path(temp) / (row["slug"] + ".zip")
            _gh_api(endpoint + "/zip", target)
            artifact_map[row["slug"]] = str(target)
            api_proofs.append({
                "slug": row["slug"], "actions_run_id": run_id,
                "actions_artifact_id": artifact_id,
                "metadata_digest_matches_pinned_zip": True,
                "workflow_branch_matches_pinned_source_branch": True,
                "producing_workflow_run_completed_successfully": True,
                "producing_workflow_head_sha": run["head_sha"],
            })
        # All five downloads must be present and verified; partial success
        # never produces a dispatch result.
        verified = verify_binary_dispatch(dispatch, artifact_map)
    require(verified["binary_verified_count"] == 5 and
            verified["downstream_binary_gate_pass"] is True,
            "incomplete five-product binary gate")
    verified["verification_scope"] = (
        "AUTHENTICATED_GITHUB_API_METADATA_AND_DOWNLOADED_ZIP_BYTES_"
        "NO_SIGNED_ATTESTATION"
    )
    verified["actions_artifact_metadata_checks"] = api_proofs
    verified["identity_cas_allowed"] = False
    return verified


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="Optional new JSON report path (never overwrite)")
    args = parser.parse_args()
    try:
        result = fetch_and_verify()
        report = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(report)
        else:
            print(report, end="")
    except (RegistrationContractError, FileExistsError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
