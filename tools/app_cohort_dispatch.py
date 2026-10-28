"""Read-only, fail-closed selector for the five *current* APP handoffs.

The historical top-level source_sha in APP_COHORT_ROTATION.json is intentionally
immutable. Dispatch must use its improvement_revision, never silently fall
back to the older EXE or request. This module does not build, CAS, or register.
"""
from __future__ import annotations

import json
from pathlib import Path

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
                and target.get("owner") == "36_MIN_WINDOWS_E2E",
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
        "factory_stable": False,
        "next_partner_center_new_product": "focus-session-desk",
        "next_owner": "36_MIN_WINDOWS_E2E",
        "no_partner_center_mutation": True,
        "products": result,
    }


def main() -> None:
    print(json.dumps(build_dispatch(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
