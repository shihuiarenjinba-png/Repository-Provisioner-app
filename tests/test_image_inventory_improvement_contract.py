"""Exact-source image inventory revision 2 provenance and registration safety."""
import unittest
from pathlib import Path

from tools.app_registration_contract import load_json, registration_request, RegistrationContractError

DOC = Path(__file__).resolve().parents[1] / "docs"


class ImageInventoryImprovementContractTests(unittest.TestCase):
    def setUp(self):
        self.job = load_json(DOC / "APP_IMAGE_INVENTORY_IMPROVEMENT_PACKAGE_JOB.json")
        self.receipt = load_json(DOC / "APP_IMAGE_INVENTORY_IMPROVEMENT_EXE_RECEIPT.json")
        self.request = load_json(DOC / "APP_IMAGE_INVENTORY_IMPROVEMENT_REGISTRATION_REQUEST.json")

    def test_request_bound_receipt_and_registration(self):
        derived = registration_request(self.job, self.receipt)
        for key in ("slug", "repo", "source_branch", "source_sha", "request_id",
                    "product_type", "packaging_family",
                    "partner_center_registration_type", "partner_center_selection",
                    "partner_center_display_name", "identity_status", "required_fields"):
            self.assertEqual(self.request[key], derived[key], key)
        self.assertEqual(self.request["pre_identity_exe"]["sha256"],
                         self.receipt["executable_sha256"])
        self.assertEqual(self.request["pre_identity_exe"]["bytes"],
                         self.receipt["executable_bytes"])
        self.assertEqual(self.request["identity_return_target"]["source_sha"],
                         self.job["source_sha"])
        self.assertEqual(self.request["identity_return_target"]["request_id"],
                         self.job["request_id"])
        self.assertEqual(self.job["request_id"],
                         "app-offline-image-inventory-desk-" + self.job["source_sha"][:12])

    def test_old_request_stays_frozen(self):
        old = load_json(DOC / "APP_IMAGE_INVENTORY_PACKAGE_JOB.json")
        self.assertEqual(old["source_sha"],
                         "16b6a772952ca0988f2ae2f8b5f4db2e59ec5877")
        self.assertEqual(old["request_id"],
                         "app-offline-image-inventory-desk-16b6a772952c")
        self.assertNotEqual(old["source_sha"], self.job["source_sha"])
        self.assertNotEqual(old["request_id"], self.job["request_id"])

    def test_unsigned_exe_and_identity_fail_closed(self):
        self.assertEqual(self.receipt["status"], "EXE_QA_UNSIGNED")
        self.assertEqual(self.receipt["msix_status"], "NOT_BUILT")
        self.assertIsNone(self.receipt["store_id"])
        self.assertIsNone(self.request["partner_center_display_name"])
        self.assertFalse(self.request["identity_cas_allowed"])
        self.assertFalse(self.request["reserved_display_name_verified"])
        self.assertEqual(self.request["partner_center_selection"], "MSIX or PWA app")
        self.assertEqual(self.request["identity_return_target"]["owner"], "36_MIN_WINDOWS_E2E")
        with self.assertRaises(RegistrationContractError):
            registration_request(self.job, {**self.receipt, "source_sha": "f" * 40})
        with self.assertRaises(RegistrationContractError):
            registration_request(self.job, {**self.receipt, "store_id": "9MZ8ZZTRTS17"})


if __name__ == "__main__":
    unittest.main()
