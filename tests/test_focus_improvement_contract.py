"""Read-only provenance regression for Focus revision 2 and frozen original."""
import unittest
from pathlib import Path

from tools.app_registration_contract import load_json, registration_request

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs"


class FocusImprovementContractTests(unittest.TestCase):
    def test_improved_job_receipt_registration_correlate(self):
        job = load_json(DOC / "APP_FOCUS_IMPROVEMENT_PACKAGE_JOB.json")
        receipt = load_json(DOC / "APP_FOCUS_IMPROVEMENT_EXE_RECEIPT.json")
        registered = load_json(DOC / "APP_FOCUS_IMPROVEMENT_REGISTRATION_REQUEST.json")
        ready = load_json(DOC / "APP_FOCUS_IMPROVEMENT_READY.json")
        derived = registration_request(job, receipt)
        for key in ("slug", "repo", "source_branch", "source_sha", "request_id",
                    "product_type", "packaging_family",
                    "partner_center_registration_type", "partner_center_selection",
                    "partner_center_display_name", "identity_status", "required_fields"):
            self.assertEqual(registered[key], derived[key], key)
        self.assertEqual(registered["pre_identity_exe"]["sha256"],
                         derived["pre_identity_exe"]["sha256"])
        self.assertEqual(registered["pre_identity_exe"]["bytes"],
                         derived["pre_identity_exe"]["bytes"])
        self.assertEqual(ready["exe_sha256"], receipt["executable_sha256"])
        self.assertEqual(ready["artifact_zip_sha256"], registered["artifact_zip_sha256"])
        self.assertEqual(ready["improved_source_sha"], job["source_sha"])
        self.assertEqual(ready["improved_request_id"], job["request_id"])
        self.assertEqual(job["request_id"], "app-focus-session-desk-" + job["source_sha"][:12])
        self.assertFalse(registered["identity_cas_allowed"])
        self.assertEqual(registered["partner_center_selection"], "MSIX or PWA app")
        self.assertIsNone(registered["partner_center_display_name"])

    def test_original_focus_request_is_immutable(self):
        old = load_json(DOC / "APP_FOCUS_PACKAGE_JOB.json")
        new = load_json(DOC / "APP_FOCUS_IMPROVEMENT_PACKAGE_JOB.json")
        self.assertEqual(old["source_sha"],
                         "8b00bc4e90828c4282463826873aa8dfd2eb93f4")
        self.assertEqual(old["request_id"], "app-focus-session-desk-8b00bc4e9082")
        self.assertNotEqual(old["source_sha"], new["source_sha"])
        self.assertNotEqual(old["request_id"], new["request_id"])

    def test_unsigned_exe_does_not_impersonate_store_identity(self):
        receipt = load_json(DOC / "APP_FOCUS_IMPROVEMENT_EXE_RECEIPT.json")
        self.assertEqual(receipt["msix_status"], "NOT_BUILT")
        self.assertIsNone(receipt["store_id"])
        self.assertEqual(receipt["official_identity_status"], "NOT_COLLECTED")
        self.assertEqual(receipt["status"], "EXE_QA_UNSIGNED")


if __name__ == "__main__":
    unittest.main()
