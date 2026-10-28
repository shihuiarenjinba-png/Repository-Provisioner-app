from pathlib import Path
import json
import tempfile
import unittest

import identity_only_return as identity_return
from package_identity_provisioner import ConflictError, ProductConfig

SHA = "8b00bc4e90828c4282463826873aa8dfd2eb93f4"
RID = "app-focus-session-desk-8b00bc4e9082"
SLUG = "focus-session-desk"


def config():
    return ProductConfig("APP", "AI-App-Factory", "shihuiarenjinba-png/AI-App-Factory",
                         "codex/unused", "shihuiarenjinba-png", "WINDOWS", ("**/*.exe",))


def queue_job():
    return {
        "request_id": RID, "product_type": "APP", "slug": SLUG,
        "display_name": "Focus Session Desk",
        "source_repository": "shihuiarenjinba-png/AI-App-Factory",
        "source_branch": "codex/app-cohort-focus-controller-20261028",
        "source_sha": SHA, "factory_build_head": SHA,
        "status": "PRE_IDENTITY_READY", "registration_type": "MSIX_OR_PWA_APP",
        "partner_center_selection": "MSIX or PWA app",
        "expected_exe_sha256": "e" * 64, "expected_exe_bytes": 12000,
        "artifact_metadata_verified": True,
    }


def operator_job(job):
    return {**job, "identity_return_target": f"products/{SLUG}/store/approved-identity.json",
            "queue_job_digest": identity_return.canonical_digest(job)}


def receipt(job):
    return {
        "schema_version": 1, "status": "IDENTITY_CAPTURED__AUTHENTICATED_UI__GITHUB_BOUND",
        "authenticated_partner_center_pass": True,
        "capture_source": "AUTHENTICATED_PARTNER_CENTER_UI",
        "job_origin": "GITHUB_PRE_IDENTITY_QUEUE",
        "central_repository": "shihuiarenjinba-png/Windows-all-auto",
        "central_branch": "codex/e2e-belt-connection-20261027",
        "central_head_sha": "c" * 40,
        "queue_job_digest": identity_return.canonical_digest(job),
        "request_id": RID, "slug": SLUG, "product_type": "APP",
        "display_name": "Focus Session Desk",
        "source_repository": "shihuiarenjinba-png/AI-App-Factory",
        "source_branch": "codex/app-cohort-focus-controller-20261028",
        "source_sha": SHA, "source_snapshot_path": "C:/private/focus",
        "source_snapshot_head": SHA, "registration_type": "MSIX_OR_PWA_APP",
        "partner_center_selection": "MSIX or PWA app",
        "identity_return_target": f"products/{SLUG}/store/approved-identity.json",
        "store_id": "9NABCDEF1234", "reserved_display_name": "Focus Session Desk",
        "identity_name": "OkinawaDesktopTools.FocusSessionDesk",
        "publisher": "CN=Example", "publisher_display_name": "Example",
        "package_family_name": "OkinawaDesktopTools.FocusSessionDesk_123456789abcd",
        "package_sid": "S-1-15-2-1-2-3-4-5-6-7",
        "captured_at": "2026-10-29T00:45:00Z", "creation_status": "CREATED",
        "overview_exact_match_count": 1, "identity_details_observed": True,
        "package_version_gate": "HOLD", "existing_scheduler_routing_pending": True,
        "cas_applied": False, "store_submitted": False,
        "batch_id": "batch-1", "batch_index": 1, "batch_total": 4,
        "trigger_origin": "SCHEDULED_36_MIN_LOOP",
        "automation_id": "6adf4b1e7654819193b997fb4fb83c85",
    }


class FakeGitHub:
    def __init__(self, status="APPLIED"):
        self.status = status
        self.calls = 0

    def return_identity(self, job, config, official, package, apply):
        self.calls += 1
        self.official = official
        self.package = package
        return {"status": self.status, "commit_sha": "f" * 40}


class IdentityOnlyReturnTests(unittest.TestCase):
    def run_one(self, mutate=None, status="APPLIED"):
        job = queue_job()
        data = receipt(job)
        if mutate:
            mutate(data)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "identity.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            github = FakeGitHub(status)
            result = identity_return.run_identity_return(
                ledger={"rotation_cohorts": {"app_jobs": [job]}},
                operator_job=operator_job(job), receipt_path=path,
                config=config(), apply=True, github=github)
        return result, github

    def test_identity_return_does_not_require_package_version(self):
        result, github = self.run_one()
        self.assertEqual(result["status"], "APPLIED")
        self.assertIsNone(github.official["version"])
        self.assertEqual(result["package_version_gate"], "HOLD")

    def test_replay_existing_verified(self):
        result, _ = self.run_one(status="EXISTING_VERIFIED")
        self.assertEqual(result["status"], "EXISTING_VERIFIED")

    def test_cross_product_identity_rejected(self):
        with self.assertRaisesRegex(ConflictError, "another job"):
            self.run_one(lambda x: x.update(request_id="app-other-00000000"))

    def test_secret_or_unknown_field_rejected(self):
        with self.assertRaisesRegex(Exception, "unexpected"):
            self.run_one(lambda x: x.update(cookie="secret"))

    def test_wrong_return_target_rejected(self):
        with self.assertRaisesRegex(ConflictError, "another job"):
            self.run_one(lambda x: x.update(identity_return_target="products/wrong/store/approved-identity.json"))


if __name__ == "__main__":
    unittest.main()
