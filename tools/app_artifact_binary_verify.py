"""Offline, read-only verifier for a SHA-pinned APP pre-Identity Actions ZIP.

Checks actual ZIP and PE bytes, not just agreement between JSON records.
Does not execute the EXE, contact Partner Center, attest Identity, or build MSIX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

MAX_ZIP = 100 * 1024 * 1024
MAX_EXE = 300 * 1024 * 1024
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ArtifactVerificationError(ValueError):
    pass


def check(ok: bool, reason: str) -> None:
    if not ok:
        raise ArtifactVerificationError(reason)


def unique_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            check(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    check(len(raw) <= 65536, "oversized metadata")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ArtifactVerificationError("invalid metadata JSON") from exc
    check(isinstance(result, dict), "metadata must be object")
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(zip_path: Path, job: dict, expected_zip_sha256: str) -> dict:
    check(zip_path.is_file() and not zip_path.is_symlink(), "ZIP must be regular file")
    check(0 < zip_path.stat().st_size <= MAX_ZIP, "ZIP size out of bounds")
    check(isinstance(expected_zip_sha256, str) and SHA256.fullmatch(expected_zip_sha256)
          and expected_zip_sha256 != "0" * 64, "invalid pinned ZIP SHA-256")
    check(sha256_file(zip_path) == expected_zip_sha256, "ZIP SHA-256 mismatch")
    slug = job.get("slug")
    source = job.get("source_sha")
    request = job.get("request_id")
    check(isinstance(slug, str) and re.fullmatch(r"[a-z][a-z0-9-]{3,39}", slug), "invalid slug")
    check(isinstance(source, str) and re.fullmatch(r"[0-9a-f]{40}", source), "invalid source SHA")
    check(request == "app-" + slug + "-" + source[:12], "request/source mismatch")
    exe_name = slug + ".exe"
    expected_names = {"exe-receipt.json", "registration-handoff.json", exe_name}
    try:
        with zipfile.ZipFile(zip_path) as archive:
            entries = archive.infolist()
            check(len(entries) == 3 and {e.filename for e in entries} == expected_names,
                  "unexpected, missing or duplicate ZIP members")
            for entry in entries:
                check(not entry.is_dir() and not (entry.flag_bits & 1), "directory or encrypted ZIP member")
                check((entry.external_attr >> 16) & 0o170000 != 0o120000,
                      "ZIP symlink not allowed")
                check(entry.file_size <= (MAX_EXE if entry.filename == exe_name else 65536),
                      "ZIP member exceeds size limit")
                check(entry.compress_size > 0 and entry.file_size <= 250 * entry.compress_size,
                      "suspicious ZIP compression ratio")
            receipt = unique_json(archive.read("exe-receipt.json"))
            handoff = unique_json(archive.read("registration-handoff.json"))
            for key in ("slug", "source_branch", "source_sha", "request_id"):
                check(receipt.get(key) == job.get(key) and handoff.get(key) == job.get(key),
                      "ZIP provenance mismatch: " + key)
            check(receipt.get("source_repository") == job.get("source_repository"),
                  "ZIP source repository mismatch")
            check(receipt.get("status") == "EXE_QA_UNSIGNED" and
                  receipt.get("stage") == "PRE_IDENTITY_WINDOWS_EXE" and
                  receipt.get("msix_status") == "NOT_BUILT" and
                  receipt.get("official_identity_status") == "NOT_COLLECTED", "unsafe receipt state")
            check(handoff.get("product_type") == "APP" and
                  handoff.get("packaging_family") == "MSIX" and
                  handoff.get("partner_center_registration_type") == "MSIX_OR_PWA_APP" and
                  handoff.get("partner_center_selection") == "MSIX or PWA app" and
                  handoff.get("identity_cas_allowed") is False and
                  handoff.get("msix_status") == "NOT_BUILT" and
                  handoff.get("windows_gui_status") == "UNVERIFIED", "unsafe handoff state")
            target = handoff.get("identity_return_target")
            check(isinstance(target, dict) and target.get("owner") == "36_MIN_WINDOWS_E2E" and
                  target.get("stage") == "AUTHENTICATED_IDENTITY_EVIDENCE_AND_CAS",
                  "unsafe Identity return target")
            for key in ("source_sha", "request_id"):
                check(target.get(key, job[key]) == job[key], "Identity return provenance mismatch")
            check(receipt.get("executable") == exe_name, "wrong EXE filename")
            check(isinstance(receipt.get("executable_sha256"), str) and
                  SHA256.fullmatch(receipt["executable_sha256"]), "invalid EXE digest")
            check(type(receipt.get("executable_bytes")) is int and
                  1024 < receipt["executable_bytes"] <= MAX_EXE, "invalid EXE byte count")
            with archive.open(exe_name) as stream:
                header = stream.read(4096)
                check(header[:2] == b"MZ" and len(header) >= 128, "not an MZ executable")
                pe_offset = struct.unpack_from("<I", header, 0x3c)[0]
                check(0x40 <= pe_offset <= len(header) - 6 and
                      header[pe_offset:pe_offset + 4] == b"PE\0\0" and
                      struct.unpack_from("<H", header, pe_offset + 4)[0] == 0x8664,
                      "not an AMD64 PE executable")
                digest = hashlib.sha256(header)
                total = len(header)
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    total += len(block)
                    check(total <= MAX_EXE, "EXE stream exceeds size limit")
                    digest.update(block)
            check(total == receipt["executable_bytes"], "EXE byte count mismatch")
            check(digest.hexdigest() == receipt["executable_sha256"], "EXE SHA-256 mismatch")
    except (zipfile.BadZipFile, EOFError, RuntimeError, OSError) as exc:
        raise ArtifactVerificationError("invalid or corrupt ZIP") from exc
    return {"status": "BINARY_VERIFIED", "slug": slug, "source_sha": source,
            "request_id": request, "zip_sha256": expected_zip_sha256,
            "exe_sha256": digest.hexdigest(), "exe_bytes": total,
            "exe_format": "PE_AMD64", "identity_cas_allowed": False,
            "msix_status": "NOT_BUILT", "windows_gui_status": "UNVERIFIED",
            "provenance_note": "local bytes matched supplied pinned digest; not a live Actions attestation"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--zip-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.zip, unique_json(args.job.read_bytes()), args.zip_sha256), indent=2))


if __name__ == "__main__":
    main()
