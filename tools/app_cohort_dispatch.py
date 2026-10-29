"""Read-only, fail-closed selector for the five *current* APP handoffs.

The historical top-level source_sha in APP_COHORT_ROTATION.json is intentionally
immutable. Dispatch must use its improvement_revision, never silently fall
back to the older EXE or request. This module does not build, CAS, or register.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from tools.app_registration_contract import (
    RegistrationContractError, load_json, registration_request,
)

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ("offline-notes-canary", "NOTES_IMPROVEMENT", True),
    ("focus-session-desk", "FOCUS_IMPROVEMENT", False),
    ("file-integrity-ledger", "LEDGER_IMPROVEMENT", False),
    ("offline-text-diff-desk", "TEXT_DIFF_BACKUP_SAFETY", False),
    ("offline-image-inventory-desk", "IMAGE_INVENTORY_IMPROVEMENT", False),
)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RegistrationContractError("cohort dispatch: " + reason)


def build_dispatch(root: Path = ROOT) -> dict:
    docs = root / "docs"
    rotation = load_json(docs / "APP_COHORT_ROTATION.json")
    require(rotation.get("max_products") == 5, "five-product cap changed")
    require(rotation.get("new_product_generation_allowed") is False,
            "new product generation is not authorized")
    require(rotation.get("factory_stable") is False,
            "cloud contract cannot certify Factory stable")
    rows = rotation.get("products")
    require(isinstance(rows, list) and len(rows) == len(FILES),
            "missing or extra cohort product")

    result = []
    for index, (slug, prefix, received) in enumerate(FILES, start=1):
        row = rows[index - 1]
        require(row.get("slot") == index and row.get("slug") == slug,
                "cohort order or slug changed")
        current = row.get("improvement_revision")
        require(isinstance(current, dict), slug + " missing current revision")
        job = load_json(docs / ("APP_" + prefix + "_PACKAGE_JOB.json"))
        receipt = load_json(docs / ("APP_" + prefix + "_EXE_RECEIPT.json"))
        request = load_json(docs / ("APP_" + prefix + "_REGISTRATION_REQUEST.json"))
        reference = (load_json(docs / "APP_NOTES_IMPROVEMENT_IDENTITY_REFERENCE.json")
                     if received else None)
        generated = registration_request(job, receipt, reference)

        require(job["slug"] == slug, slug + " job slug mismatch")
        for key in ("source_branch", "source_sha", "request_id"):
            require(job[key] == current.get(key), slug + " stale rotation " + key)
            require(request.get(key) == job[key], slug + " stale registration " + key)
        require(job["request_id"].endswith(job["source_sha"][:12]),
                slug + " request/source correlation mismatch")
        # The current improvement revision is the source of truth. Matching
        # source SHA alone does not prove the EXE, ZIP or Actions run is current.
        require(current.get("artifact_sha256") == receipt["executable_sha256"],
                slug + " stale improvement EXE SHA-256")
        require(current.get("artifact_bytes") == receipt["executable_bytes"],
                slug + " stale improvement EXE byte count")
        # Two matching absent or malformed digests are not evidence of an artifact.
        zip_digest = current.get("artifact_zip_sha256")
        require(isinstance(zip_digest, str) and
                re.fullmatch(r"[0-9a-f]{64}", zip_digest) is not None and
                zip_digest != "0" * 64,
                slug + " invalid improvement artifact ZIP SHA-256")
        require(zip_digest == request.get("artifact_zip_sha256"),
                slug + " stale improvement artifact ZIP SHA-256")
        require(current.get("artifact_url") == request.get("artifact_url"),
                slug + " stale improvement artifact URL")
        require(isinstance(request.get("artifact_url"), str) and
                re.fullmatch(
                    r"https://github[.]com/shihuiarenjinba-png/AI-App-Factory/"
                    r"actions/runs/[1-9][0-9]*/artifacts/[1-9][0-9]*",
                    request["artifact_url"]) is not None,
                slug + " malformed Actions artifact URL")
        require(request.get("product") == job["display_name"],
                slug + " registration display name mismatch")
        require(request.get("identity_status") == current.get("identity_status"),
                slug + " stale improvement Identity status")
        require(request.get("store_id") ==
                (reference.get("store_id") if reference else None),
                slug + " untrusted Store ID")

        for key in ("slug", "repo", "source_branch", "source_sha", "request_id",
                    "product_type", "packaging_family", "partner_center_registration_type",
                    "partner_center_selection", "identity_status", "identity_attestation",
                    "identity_cas_allowed", "store_id", "required_fields",
                    "user_id_request", "next_owner", "next_stage", "msix_status",
                    "windows_gui_status"):
            require(request.get(key) == generated.get(key),
                    slug + " registration contract mismatch: " + key)
        target = request.get("identity_return_target")
        require(isinstance(target, dict)
                and target.get("source_sha") == job["source_sha"]
                and target.get("request_id") == job["request_id"]
                and target.get("owner") == "36_MIN_WINDOWS_E2E"
                and target.get("stage") == "AUTHENTICATED_IDENTITY_EVIDENCE_AND_CAS",
                slug + " invalid Identity return target")
        exe = request.get("pre_identity_exe")
        require(isinstance(exe, dict)
                and exe.get("status") == "EXE_QA_UNSIGNED"
                and exe.get("sha256") == receipt["executable_sha256"]
                and exe.get("bytes") == receipt["executable_bytes"]
                and exe.get("receipt_only_not_binary_reverification") is False,
                slug + " missing independent EXE verification")
        require(request.get("partner_center_display_name") is None,
                slug + " unverified reserved name must remain null")
        require(request.get("artifact_url", "").startswith(
            "https://github.com/shihuiarenjinba-png/AI-App-Factory/actions/runs/"),
            slug + " untrusted artifact URL")
        require(request.get("identity_status") ==
                ("REFERENCE_AVAILABLE" if received else "WAITING_USER_IDENTITY"),
                slug + " Identity status mismatch")
        require(request.get("identity_cas_allowed") is False,
                slug + " Identity CAS is not authorized")
        require(request.get("msix_status") == "NOT_BUILT"
                and request.get("windows_gui_status") == "UNVERIFIED",
                slug + " unsupported downstream PASS")
        result.append({
            "slot": index,
            "product": request["product"],
            "slug": slug,
            "repo": request["repo"],
            "source_branch": job["source_branch"],
            "source_sha": job["source_sha"],
            "request_id": job["request_id"],
            "product_type": "APP",
            "packaging_family": "MSIX",
            "partner_center_registration_type": "MSIX_OR_PWA_APP",
            "partner_center_selection": "MSIX or PWA app",
            "partner_center_display_name": None,
            "identity_status": request["identity_status"],
            "required_fields": request["required_fields"],
            "identity_return_target": target,
            "pre_identity_exe": exe,
            "artifact_url": request["artifact_url"],
            "artifact_zip_sha256": request["artifact_zip_sha256"],
            "registration_request_path": "docs/APP_" + prefix + "_REGISTRATION_REQUEST.json",
            "post_identity_ready": False,
            "windows_gui_pass": False,
            "msix_built": False,
        })
    return {
        "schema_version": 1,
        "lane": "APP",
        "source": "FIVE_PRODUCT_CURRENT_IMPROVEMENT_REVISIONS",
        "product_count": len(result),
        "pre_identity_cloud_ready_count": len(result),
        "binary_verified_count": 0,
        "downstream_binary_gate_pass": False,
        "verification_scope": "CONTRACT_ONLY_NO_LOCAL_BINARY_CHECK",
        "factory_stable": False,
        "next_partner_center_new_product": "focus-session-desk",
        "next_owner": "36_MIN_WINDOWS_E2E",
        "no_partner_center_mutation": True,
        "products": result,
    }



def verify_binary_dispatch(dispatch: dict, artifact_paths: dict, root: Path = ROOT) -> dict:
    """Require all five pinned ZIPs before claiming a binary-verified handoff.

    An explicit slug-to-local-ZIP map avoids guessing artifact names. These
    checks establish local byte integrity, NOT a fresh GitHub attestation,
    Windows GUI success, MSIX completion or official Identity authorization.
    """
    from tools.app_artifact_binary_verify import ArtifactVerificationError, verify

    expected = {row["slug"] for row in dispatch["products"]}
    require(isinstance(artifact_paths, dict) and set(artifact_paths) == expected,
            "binary gate requires exactly five explicitly mapped product ZIPs")
    results = []
    for row in dispatch["products"]:
        slug = row["slug"]
        prefix = next(prefix for name, prefix, _ in FILES if name == slug)
        job = load_json(root / "docs" / ("APP_" + prefix + "_PACKAGE_JOB.json"))
        location = artifact_paths[slug]
        require(isinstance(location, str) and bool(location.strip()),
                slug + " missing ZIP path")
        try:
            proof = verify(Path(location), job, row["artifact_zip_sha256"])
        except (ArtifactVerificationError, OSError, ValueError) as exc:
            raise RegistrationContractError(
                "cohort dispatch: " + slug + " binary gate failed: " + str(exc)
            ) from exc
        exe = row["pre_identity_exe"]
        require(proof.get("status") == "BINARY_VERIFIED"
                and proof.get("slug") == slug
                and proof.get("source_sha") == row["source_sha"]
                and proof.get("request_id") == row["request_id"]
                and proof.get("zip_sha256") == row["artifact_zip_sha256"]
                and proof.get("exe_sha256") == exe["sha256"]
                and proof.get("exe_bytes") == exe["bytes"]
                and proof.get("identity_cas_allowed") is False
                and proof.get("msix_status") == "NOT_BUILT"
                and proof.get("windows_gui_status") == "UNVERIFIED",
                slug + " binary proof inconsistent with current handoff")
        results.append(proof)
    dispatch["binary_verified_count"] = len(results)
    dispatch["downstream_binary_gate_pass"] = True
    dispatch["verification_scope"] = "LOCAL_PINNED_ZIP_BYTES_NOT_LIVE_ACTIONS_ATTESTATION"
    for row, proof in zip(dispatch["products"], results):
        row["binary_verification"] = proof
    return dispatch


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-map", type=Path,
                        help="JSON object mapping each of the five slugs to a local ZIP path")
    parser.add_argument("--require-binary", action="store_true",
                        help="Fail unless all five real ZIP files are byte-verified")
    args = parser.parse_args()
    dispatch = build_dispatch()
    if args.require_binary and args.artifact_map is None:
        parser.error("--require-binary requires --artifact-map")
    if args.artifact_map is not None:
        try:
            artifact_paths = load_json(args.artifact_map)
            dispatch = verify_binary_dispatch(dispatch, artifact_paths)
        except (RegistrationContractError, OSError, ValueError) as exc:
            parser.error(str(exc))
    print(json.dumps(dispatch, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
