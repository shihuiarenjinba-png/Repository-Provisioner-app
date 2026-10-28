"""Fail-closed, read-only APP registration routing for the pre-Identity cohort.

No Partner Center authentication, Identity CAS, Store submission or MSIX
generation. The *final* packaging family, never the intermediate EXE,
determines the Partner Center registration category.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from typing import Any

SOURCE_REPO = "shihuiarenjinba-png/AI-App-Factory"
REQUIRED_IDENTITY_FIELDS = ("store_id", "reserved_display_name", "identity_name", "publisher",
                            "publisher_display_name", "pfn", "package_sid")
SOURCE_KEYS = ("source_repository", "source_branch", "source_sha", "request_id",
               "slug", "product_type", "display_name")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
BRANCH = re.compile(r"codex/[A-Za-z0-9._/-]+\Z")
SLUG = re.compile(r"[a-z][a-z0-9-]{3,39}\Z")
REQUEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{3,127}\Z")
STORE_ID = re.compile(r"[A-Za-z0-9]{8,32}\Z")
IDENTITY_NAME = re.compile(r"[A-Za-z][A-Za-z0-9._-]{2,49}\Z")
PFN = re.compile(r"[A-Za-z0-9._-]+_[a-z0-9]{13}\Z")
PACKAGE_SID = re.compile(r"S-1-15-2(?:-\d+){7}\Z")


class RegistrationContractError(ValueError):
    """Unsafe or mismatched inputs; no side effects performed."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise RegistrationContractError(reason)


def _matches(pattern: re.Pattern[str], value: Any) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    _require(path.is_file() and not path.is_symlink(), "missing or linked JSON input")
    _require(path.stat().st_size <= 65536, "oversized JSON input")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RegistrationContractError("invalid JSON input") from exc
    _require(isinstance(value, dict), "JSON input must be an object")
    return value


def validate_job_receipt(job: dict[str, Any], receipt: dict[str, Any]) -> None:
    _require(job.get("schema_version") == "1.0", "unsupported job schema")
    _require(receipt.get("schema_version") == 1, "unsupported EXE receipt schema")
    _require(job.get("product_type") == "APP", "APP registration requires APP job")
    _require(job.get("source_factory") == "AI-App-Factory", "wrong Factory")
    _require(job.get("source_repository") == SOURCE_REPO, "wrong source repository")
    _require(_matches(BRANCH, job.get("source_branch")), "invalid source branch")
    branch = job["source_branch"]
    _require(".." not in branch and "//" not in branch and not branch.endswith(("/", ".")), "unsafe branch")
    _require(_matches(SHA40, job.get("source_sha")) and job["source_sha"] != "0" * 40, "invalid source SHA")
    _require(_matches(REQUEST, job.get("request_id")), "invalid request ID")
    _require(_matches(SLUG, job.get("slug")), "invalid slug")
    _require(isinstance(job.get("display_name"), str) and 1 <= len(job["display_name"].strip()) <= 100,
             "invalid display name")
    _require(job.get("requested_actions") and isinstance(job["requested_actions"], list), "missing job actions")
    for key in SOURCE_KEYS:
        _require(receipt.get(key) == job[key], "EXE receipt mismatch: " + key)
    _require(receipt.get("source_factory") == job["source_factory"], "EXE receipt Factory mismatch")
    _require(receipt.get("stage") == "PRE_IDENTITY_WINDOWS_EXE", "wrong EXE stage")
    _require(receipt.get("status") == "EXE_QA_UNSIGNED", "EXE QA status not verified")
    _require(receipt.get("msix_status") == "NOT_BUILT", "EXE receipt unexpectedly claims MSIX")
    _require(receipt.get("store_id") is None, "pre-Identity EXE must not carry Store ID")
    _require(receipt.get("official_identity_status") == "NOT_COLLECTED", "EXE receipt Identity state invalid")
    _require(receipt.get("executable") == job["slug"] + ".exe", "EXE name mismatch")
    _require(_matches(SHA256, receipt.get("executable_sha256")), "EXE SHA-256 missing")
    _require(type(receipt.get("executable_bytes")) is int and 1024 < receipt["executable_bytes"] <= 314572800,
             "EXE size invalid")


def validate_identity_reference(reference: dict[str, Any], job: dict[str, Any]) -> None:
    """Bind a user-provided reference to an immutable product, NOT attest it."""
    allowed = set(REQUIRED_IDENTITY_FIELDS) | {"source_sha", "request_id", "slug", "reference_source"}
    _require(set(reference) <= allowed, "unexpected Identity reference keys")
    for key in ("source_sha", "request_id", "slug"):
        _require(reference.get(key) == job[key], "Identity reference mismatch: " + key)
    _require(reference.get("reference_source") == "USER_PROVIDED", "Identity reference provenance missing")
    _require(_matches(STORE_ID, reference.get("store_id")), "invalid Store ID")
    _require(_matches(IDENTITY_NAME, reference.get("identity_name")), "invalid Identity Name")
    _require(isinstance(reference.get("publisher"), str) and reference["publisher"].startswith("CN=")
             and len(reference["publisher"]) <= 250, "invalid Publisher")
    _require(isinstance(reference.get("publisher_display_name"), str)
             and 1 <= len(reference["publisher_display_name"].strip()) <= 100, "invalid Publisher Display Name")
    _require(_matches(PFN, reference.get("pfn")), "invalid PFN")
    _require(reference["pfn"].startswith(reference["identity_name"] + "_"), "PFN and Identity Name mismatch")
    _require(_matches(PACKAGE_SID, reference.get("package_sid")), "invalid Package SID")
    # Reserved display name cannot be inferred from the app's UI title.
    reserved = reference.get("reserved_display_name")
    _require(reserved is None or (isinstance(reserved, str) and 1 <= len(reserved.strip()) <= 100),
             "invalid reserved display name")


def registration_request(job: dict[str, Any], receipt: dict[str, Any],
                         identity_reference: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_job_receipt(job, receipt)
    if identity_reference is not None:
        validate_identity_reference(identity_reference, job)
    received = identity_reference is not None
    return {
        "schema_version": 1,
        "product": job["display_name"],
        "slug": job["slug"],
        "repo": job["source_repository"],
        "source_branch": job["source_branch"],
        "source_sha": job["source_sha"],
        "request_id": job["request_id"],
        "product_type": "APP",
        "packaging_family": "MSIX",
        "partner_center_registration_type": "MSIX_OR_PWA_APP",
        "partner_center_selection": "MSIX or PWA app",
        "partner_center_display_name": (identity_reference or {}).get("reserved_display_name"),
        "identity_status": "REFERENCE_AVAILABLE" if received else "WAITING_USER_IDENTITY",
        "identity_attestation": "NOT_VERIFIED",
        "identity_cas_allowed": False,
        "store_id": (identity_reference or {}).get("store_id"),
        "required_fields": [] if received else list(REQUIRED_IDENTITY_FIELDS),
        "user_id_request": "NONE_ALREADY_RECEIVED" if received else "REQUEST_OFFICIAL_IDENTITY",
        "pre_identity_exe": {
            "status": receipt["status"],
            "sha256": receipt["executable_sha256"],
            "bytes": receipt["executable_bytes"],
            "receipt_only_not_binary_reverification": True,
        },
        "next_owner": "36_MIN_WINDOWS_E2E",
        "next_stage": "AUTHENTICATED_IDENTITY_EVIDENCE_AND_CAS" if received else "AWAIT_USER_IDENTITY",
        "msix_status": "NOT_BUILT",
        "windows_gui_status": "UNVERIFIED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--identity-reference", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = registration_request(load_json(args.job), load_json(args.receipt),
                                  load_json(args.identity_reference) if args.identity_reference else None)
    _require(not args.output.exists() and not args.output.is_symlink(), "output already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
