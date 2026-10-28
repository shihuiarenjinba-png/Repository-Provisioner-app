"""Return an APP Store Identity through the existing single-writer CAS client.

This entrypoint accepts the GitHub PRE_IDENTITY job and a private authenticated
UI receipt.  It intentionally does not select a package version or build an
MSIX; the Factory performs that later after Identity return.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from package_identity_provisioner import (
    ConflictError,
    GitHubReturnClient,
    HoldError,
    Job,
    ProductConfig,
    load_json,
    write_json,
)

IDENTITY_FIELDS = {
    "store_id", "reserved_display_name", "identity_name", "publisher",
    "publisher_display_name", "package_family_name", "package_sid",
}
RECEIPT_FIELDS = {
    "schema_version", "status", "authenticated_partner_center_pass",
    "capture_source", "job_origin", "central_repository", "central_branch",
    "central_head_sha", "queue_job_digest", "request_id", "slug",
    "product_type", "display_name", "source_repository", "source_branch",
    "source_sha", "source_snapshot_path", "source_snapshot_head",
    "registration_type", "partner_center_selection", "identity_return_target",
    "captured_at", "creation_status", "overview_exact_match_count",
    "identity_details_observed", "package_version_gate",
    "existing_scheduler_routing_pending", "cas_applied", "store_submitted",
    "batch_id", "batch_index", "batch_total", "trigger_origin", "automation_id",
} | IDENTITY_FIELDS


def canonical_digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _official(receipt: dict, job: Job, queue_job: dict) -> dict:
    if set(receipt) != RECEIPT_FIELDS:
        raise HoldError("APP Identity receipt has missing or unexpected fields")
    exact = {
        "request_id": job.request_id, "slug": job.slug, "product_type": "APP",
        "display_name": job.display_name, "source_repository": job.source_repository,
        "source_branch": job.source_branch, "source_sha": job.source_sha,
        "source_snapshot_head": job.source_sha,
        "registration_type": "MSIX_OR_PWA_APP",
        "partner_center_selection": "MSIX or PWA app",
        "identity_return_target": f"products/{job.slug}/store/approved-identity.json",
        "job_origin": "GITHUB_PRE_IDENTITY_QUEUE",
        "central_repository": "shihuiarenjinba-png/Windows-all-auto",
        "central_branch": "codex/e2e-belt-connection-20261027",
        "queue_job_digest": canonical_digest(queue_job),
        "trigger_origin": "SCHEDULED_36_MIN_LOOP",
        "automation_id": "6adf4b1e7654819193b997fb4fb83c85",
        "batch_total": 4,
    }
    if any(receipt.get(key) != value for key, value in exact.items()):
        raise ConflictError("APP Identity receipt belongs to another job/product/source")
    if (receipt.get("status") != "IDENTITY_CAPTURED__AUTHENTICATED_UI__GITHUB_BOUND"
            or receipt.get("authenticated_partner_center_pass") is not True
            or receipt.get("capture_source") != "AUTHENTICATED_PARTNER_CENTER_UI"
            or receipt.get("creation_status") not in {"CREATED", "REUSED_EXISTING"}
            or receipt.get("overview_exact_match_count") != 1
            or receipt.get("identity_details_observed") is not True
            or receipt.get("package_version_gate") != "HOLD"
            or receipt.get("cas_applied") is not False
            or receipt.get("store_submitted") is not False):
        raise HoldError("APP Identity receipt evidence is incomplete")
    if (not re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("central_head_sha", "")))
            or not isinstance(receipt.get("batch_index"), int)
            or not 1 <= receipt["batch_index"] <= 4):
        raise HoldError("APP scheduled batch provenance is invalid")
    for key in IDENTITY_FIELDS:
        value = receipt.get(key)
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise HoldError("APP Identity field is invalid")
    if (not re.fullmatch(r"[A-Za-z0-9]{8,32}", receipt["store_id"])
            or not receipt["publisher"].startswith("CN=")
            or not re.fullmatch(r"S-1-15-2(?:-\d+){7}", receipt["package_sid"])):
        raise HoldError("APP Identity schema is invalid")
    return {
        **receipt,
        "name": receipt["identity_name"],
        "version": None,
        "authenticated_account": "LOCAL_WINDOWS_PARTNER_CENTER_OPERATOR",
        "official_evidence_url": (
            f"https://partner.microsoft.com/en-us/dashboard/products/{receipt['store_id']}/identity"
        ),
    }


def run_identity_return(*, ledger: dict, operator_job: dict, receipt_path: Path,
                        config: ProductConfig, apply: bool,
                        github: GitHubReturnClient | None = None) -> dict:
    jobs = (ledger.get("rotation_cohorts") or {}).get("app_jobs", [])
    matches = [item for item in jobs if isinstance(item, dict)
               and item.get("slug") == operator_job.get("slug")]
    if len(matches) != 1 or matches[0].get("status") != "PRE_IDENTITY_READY":
        raise HoldError("APP PRE_IDENTITY GitHub job is not unique and ready")
    queue_job = matches[0]
    if canonical_digest(queue_job) != operator_job.get("queue_job_digest"):
        raise ConflictError("APP PRE_IDENTITY queue job digest changed")
    required = {
        "request_id": operator_job.get("request_id"), "product_type": "APP",
        "source_repository": operator_job.get("source_repository"),
        "source_branch": operator_job.get("source_branch"),
        "source_sha": operator_job.get("source_sha"), "slug": operator_job.get("slug"),
        "display_name": operator_job.get("display_name"),
        "registration_type": "MSIX_OR_PWA_APP",
        "partner_center_selection": "MSIX or PWA app",
    }
    if any(queue_job.get(key) != value for key, value in required.items()):
        raise ConflictError("APP PRE_IDENTITY job and local operator binding differ")
    if (queue_job.get("artifact_metadata_verified") is not True
            or queue_job.get("factory_build_head") != required["source_sha"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(queue_job.get("expected_exe_sha256", "")))
            or type(queue_job.get("expected_exe_bytes")) is not int
            or queue_job["expected_exe_bytes"] <= 1024):
        raise HoldError("APP PRE_IDENTITY Factory EXE evidence is incomplete")
    raw_job = {
        "schema_version": "1.0", "request_id": required["request_id"],
        "product_type": "APP", "source_factory": config.source_factory,
        "source_repository": required["source_repository"],
        "source_branch": required["source_branch"], "source_sha": required["source_sha"],
        "slug": required["slug"], "display_name": required["display_name"],
        "target_owner": config.target_owner, "dry_run": False,
        "requested_actions": ["LOOKUP_OFFICIAL_IDENTITY", "PROPOSE_GITHUB_RETURN"],
    }
    job = Job.validate(raw_job, config)
    official = _official(load_json(receipt_path, 64_000), job, queue_job)
    package = {
        "kind": "exe", "sha256": queue_job["expected_exe_sha256"],
        "size_bytes": queue_job["expected_exe_bytes"],
        "signature_status": "PRE_IDENTITY_EXE_NOT_MSIX",
    }
    returned = (github or GitHubReturnClient()).return_identity(
        job, config, official, package, apply=apply,
    )
    return {
        "schema_version": 1, "status": returned["status"],
        "request_id": job.request_id, "slug": job.slug, "source_sha": job.source_sha,
        "identity_return_target": f"products/{job.slug}/store/approved-identity.json",
        "github_return": returned, "package_version_gate": "HOLD",
        "store_submission": "NOT_PERFORMED",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--operator-job", type=Path, required=True)
    parser.add_argument("--official-identity", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_identity_return(
            ledger=load_json(args.ledger, 1_000_000),
            operator_job=load_json(args.operator_job, 64_000),
            receipt_path=args.official_identity,
            config=ProductConfig.load(args.config), apply=args.apply,
        )
    except (HoldError, ConflictError) as exc:
        result = {"status": exc.status, "errors": [str(exc)],
                  "store_submission": "NOT_PERFORMED"}
    write_json(args.output, result)
    print(json.dumps({"status": result["status"], "output": str(args.output)},
                     ensure_ascii=False))
    return 0 if result["status"] in {"APPLIED", "EXISTING_VERIFIED", "NOT_APPLIED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
