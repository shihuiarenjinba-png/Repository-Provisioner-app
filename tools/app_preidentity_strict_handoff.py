"""Fail-closed APP EXE -> strict Provisioner job and separate Store routing.

Runs offline. No Partner Center login, Identity attestation/CAS, MSIX build,
Store mutation, or auto-submit. The EXE must match its exact source receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.app_registration_contract import (
    RegistrationContractError, load_json, registration_request,
    validate_job_receipt,
)

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/job-v1.0.schema.json"
JOB_FIELDS = (
    "schema_version", "request_id", "product_type", "source_factory",
    "source_repository", "source_branch", "source_sha", "slug",
    "display_name", "target_owner", "dry_run", "requested_actions",
)
SOURCE_FIELDS = (
    "request_id", "product_type", "source_factory", "source_repository",
    "source_branch", "source_sha", "slug", "display_name",
)


def strict_job(receipt: dict, *, dry_run: bool = True) -> dict:
    """Build only schema-permitted fields; never mix routing metadata into job."""
    job = {key: receipt.get(key) for key in SOURCE_FIELDS}
    job.update(schema_version="1.0", target_owner="shihuiarenjinba-png",
               dry_run=dry_run, requested_actions=["BUILD_WINDOWS"])
    validate_job_receipt(job, receipt)
    validate_strict_schema(job)
    return job


def validate_strict_schema(job: dict) -> None:
    """Check the authoritative repository schema without extra dependencies."""
    schema = load_json(SCHEMA)
    required = set(schema["required"])
    if set(job) != required or set(JOB_FIELDS) != required:
        raise RegistrationContractError("strict Provisioner job keys mismatch")
    for key, value in job.items():
        rule = schema["properties"][key]
        kind = rule.get("type")
        if kind == "boolean" and type(value) is not bool:
            raise RegistrationContractError("wrong boolean: " + key)
        if kind == "string" and not isinstance(value, str):
            raise RegistrationContractError("wrong string: " + key)
        if kind == "array":
            if not isinstance(value, list) or len(value) < rule.get("minItems", 0):
                raise RegistrationContractError("invalid array: " + key)
            if rule.get("uniqueItems") and len(value) != len(set(map(str, value))):
                raise RegistrationContractError("duplicate action: " + key)
            if any(item not in rule["items"]["enum"] for item in value):
                raise RegistrationContractError("unsupported action: " + key)
        if "const" in rule and value != rule["const"]:
            raise RegistrationContractError("wrong constant: " + key)
        if "enum" in rule and value not in rule["enum"]:
            raise RegistrationContractError("wrong enum: " + key)
        if "pattern" in rule and (not isinstance(value, str)
                                  or re.fullmatch(rule["pattern"], value) is None):
            raise RegistrationContractError("invalid pattern: " + key)
        if isinstance(value, str) and (len(value) < rule.get("minLength", 0)
                                      or len(value) > rule.get("maxLength", 10**9)):
            raise RegistrationContractError("invalid length: " + key)


def verify_exe(exe: Path, receipt: dict) -> None:
    if not exe.is_file() or exe.is_symlink():
        raise RegistrationContractError("missing or linked EXE")
    size = exe.stat().st_size
    if size != receipt.get("executable_bytes") or not 1024 < size <= 314572800:
        raise RegistrationContractError("EXE byte count mismatch")
    digest = hashlib.sha256()
    with exe.open("rb") as stream:
        header = stream.read(4096)
        stream.seek(0)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if header[:2] != b"MZ" or len(header) < 64:
        raise RegistrationContractError("not a Windows PE executable")
    pe_offset = int.from_bytes(header[60:64], "little")
    if pe_offset + 4 > len(header) or header[pe_offset:pe_offset + 4] != b"PE\x00\x00":
        raise RegistrationContractError("invalid Windows PE header")
    if digest.hexdigest() != receipt.get("executable_sha256"):
        raise RegistrationContractError("EXE SHA-256 mismatch")


def write_outputs(job_path: Path, job: dict, routing_path: Path, routing: dict) -> None:
    if job_path.resolve() == routing_path.resolve():
        raise RegistrationContractError("job and routing outputs must differ")
    for path in (job_path, routing_path):
        if path.exists() or path.is_symlink() or not path.parent.is_dir():
            raise RegistrationContractError("output exists or directory missing")
    created = []
    try:
        for path, value in ((job_path, job), (routing_path, routing)):
            with path.open("x", encoding="utf-8") as out:
                created.append(path)
                json.dump(value, out, ensure_ascii=False, indent=2)
                out.write("\n")
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--identity-reference", type=Path)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-request-id", required=True)
    parser.add_argument("--job-output", type=Path, required=True)
    parser.add_argument("--routing-output", type=Path, required=True)
    parser.add_argument("--execute-build", action="store_true",
                        help="Prepare non-dry-run BUILD_WINDOWS job only; no action executed")
    args = parser.parse_args(argv)
    receipt = load_json(args.receipt)
    if receipt.get("source_sha") != args.expected_source_sha:
        raise RegistrationContractError("unexpected source SHA")
    if receipt.get("request_id") != args.expected_request_id:
        raise RegistrationContractError("unexpected request ID")
    verify_exe(args.exe, receipt)
    job = strict_job(receipt, dry_run=not args.execute_build)
    reference = load_json(args.identity_reference) if args.identity_reference else None
    routing = registration_request(job, receipt, reference)
    routing["pre_identity_exe"]["receipt_only_not_binary_reverification"] = False
    routing["identity_return_target"] = {
        "owner": "36_MIN_WINDOWS_E2E", "source_sha": job["source_sha"],
        "request_id": job["request_id"], "stage": routing["next_stage"],
    }
    routing["commercial_quality_status"] = "HOLD"
    routing["reserved_display_name_verified"] = False
    write_outputs(args.job_output, job, args.routing_output, routing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
