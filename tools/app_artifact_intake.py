"""Verify real Factory EXE bytes together with its strict Provisioner job.

Read-only intake, except an optional new evidence JSON file. Never installs,
builds, signs, binds Identity, authenticates Partner Center, or submits Store.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from package_job import validate_job, verify_github_head
from tools.app_preidentity_strict_handoff import verify_exe
from tools.app_registration_contract import (
    RegistrationContractError, load_json, registration_request,
    validate_job_receipt,
)


def verify_artifact(job: dict, receipt: dict, exe: Path, *,
                    identity_reference: dict | None = None,
                    verify_head: bool = False) -> dict:
    """Fail closed unless the actual PE, receipt and 12-field job agree."""
    intake = validate_job(job)
    validate_job_receipt(job, receipt)
    if exe.name != receipt["executable"]:
        raise RegistrationContractError("EXE filename differs from receipt")
    verify_exe(exe, receipt)
    routing = registration_request(job, receipt, identity_reference)
    # A valid EXE is not proof that the mutable GitHub branch still points
    # at the pinned source. The optional check is authenticated/read-only.
    head = verify_github_head(job) if verify_head else None
    return {
        "schema_version": 1,
        "status": "PRE_IDENTITY_READY" if head else "ARTIFACT_VERIFIED_HEAD_UNCHECKED",
        "source_repository": job["source_repository"],
        "source_branch": job["source_branch"],
        "source_sha": job["source_sha"],
        "request_id": job["request_id"],
        "slug": job["slug"],
        "exe_sha256": receipt["executable_sha256"],
        "exe_bytes": receipt["executable_bytes"],
        "artifact_bytes_verified": True,
        "job_idempotency_key": intake["idempotency_key"],
        "source_head_verification": "VERIFIED_AT_CHECK_TIME" if head else "NOT_CHECKED",
        "source_head_sha": head,
        "product_type": "APP",
        "packaging_family": "MSIX",
        "partner_center_registration_type": "MSIX_OR_PWA_APP",
        "partner_center_selection": "MSIX or PWA app",
        "partner_center_display_name": routing["partner_center_display_name"],
        "identity_status": routing["identity_status"],
        "identity_attestation": "NOT_VERIFIED",
        "identity_cas_allowed": False,
        "msix_status": "NOT_BUILT",
        "commercial_quality_status": "HOLD",
        "next_owner": "36_MIN_WINDOWS_E2E",
        "next_stage": "AUTHENTICATED_IDENTITY_EVIDENCE_AND_CAS"
                      if identity_reference else "AWAIT_USER_IDENTITY",
        "note": ("Read-only artifact proof. HEAD may change after verification. "
                 "Recheck immediately before any mutation; no Store or Identity write."),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--identity-reference", type=Path)
    parser.add_argument("--verify-head", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_artifact(
            load_json(args.job), load_json(args.receipt), args.exe,
            identity_reference=(load_json(args.identity_reference)
                                if args.identity_reference else None),
            verify_head=args.verify_head,
        )
        if args.output.exists() or args.output.is_symlink():
            raise RegistrationContractError("refusing to overwrite evidence")
        if not args.output.parent.is_dir() or args.output.parent.is_symlink():
            raise RegistrationContractError("output parent missing or linked")
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("APP_ARTIFACT_INTAKE_HOLD: " + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
