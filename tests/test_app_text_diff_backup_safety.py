"""Validate exact Text Diff backup-safety EXE and Partner Center handoff."""
import json
from pathlib import Path
import unittest
from tools.app_registration_contract import registration_request, RegistrationContractError

ROOT = Path(__file__).resolve().parents[1]
def load(name):
    return json.loads((ROOT / "docs" / name).read_text(encoding="utf-8"))

class TextDiffBackupSafetyContractTests(unittest.TestCase):
    def setUp(self):
        self.job = load("APP_TEXT_DIFF_BACKUP_SAFETY_PACKAGE_JOB.json")
        self.receipt = load("APP_TEXT_DIFF_BACKUP_SAFETY_EXE_RECEIPT.json")
        self.request = load("APP_TEXT_DIFF_BACKUP_SAFETY_REGISTRATION_REQUEST.json")

    def test_exact_job_receipt_and_request(self):
        actual = registration_request(self.job, self.receipt)
        for key in ("slug", "source_sha", "request_id", "product_type",
                    "packaging_family", "partner_center_registration_type",
                    "partner_center_selection", "identity_status"):
            self.assertEqual(actual[key], self.request[key])
        self.assertEqual(self.request["pre_identity_exe"]["sha256"],
                         self.receipt["executable_sha256"])
        self.assertEqual(self.request["pre_identity_exe"]["bytes"],
                         self.receipt["executable_bytes"])
        self.assertEqual(self.request["identity_return_target"]["source_sha"],
                         self.job["source_sha"])
        self.assertEqual(self.request["identity_return_target"]["request_id"],
                         self.job["request_id"])

    def test_no_fabricated_identity_or_msix(self):
        self.assertIsNone(self.request["partner_center_display_name"])
        self.assertFalse(self.request["reserved_display_name_verified"])
        self.assertFalse(self.request["identity_cas_allowed"])
        self.assertIsNone(self.receipt["store_id"])
        self.assertEqual(self.request["msix_status"], "NOT_BUILT")
        self.assertEqual(self.request["windows_gui_status"], "UNVERIFIED")
        self.assertEqual(self.request["identity_return_target"]["owner"],
                         "36_MIN_WINDOWS_E2E")

    def test_wrong_source_or_request_fails_closed(self):
        for field, replacement in (("source_sha", "f" * 40), ("request_id", "wrong-request")):
            with self.subTest(field=field):
                with self.assertRaises(RegistrationContractError):
                    registration_request(self.job, {**self.receipt, field: replacement})

    def test_cohort_original_is_immutable(self):
        original = load("APP_TEXT_DIFF_PACKAGE_JOB.json")
        self.assertNotEqual(original["source_sha"], self.job["source_sha"])
        self.assertNotEqual(original["request_id"], self.job["request_id"])
        self.assertEqual(original["slug"], self.job["slug"])
        cohort = load("APP_COHORT_ROTATION.json")
        self.assertFalse(cohort["factory_stable"])
        self.assertEqual(cohort["max_products"], 5)
        slot = next(p for p in cohort["products"] if p["slot"] == 4)
        self.assertEqual(slot["improvement_revision"]["source_sha"], self.job["source_sha"])
        self.assertEqual(slot["improvement_revision"]["request_id"], self.job["request_id"])

if __name__ == "__main__":
    unittest.main()
