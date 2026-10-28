"""Exact Offline Notes revision-2 receipt, identity-reference and handoff tests."""
import json
from pathlib import Path
import unittest
from tools.app_registration_contract import registration_request, RegistrationContractError

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT / "docs" / name).read_text(encoding="utf-8"))

class OfflineNotesImprovementContractTests(unittest.TestCase):
    def setUp(self):
        self.job = load("APP_NOTES_IMPROVEMENT_PACKAGE_JOB.json")
        self.receipt = load("APP_NOTES_IMPROVEMENT_EXE_RECEIPT.json")
        self.reference = load("APP_NOTES_IMPROVEMENT_IDENTITY_REFERENCE.json")
        self.request = load("APP_NOTES_IMPROVEMENT_REGISTRATION_REQUEST.json")

    def test_reference_correlates_without_authentication_or_cas(self):
        actual = registration_request(self.job, self.receipt, self.reference)
        for key in ("slug", "source_sha", "request_id", "product", "product_type",
                    "packaging_family", "partner_center_registration_type",
                    "partner_center_selection", "identity_status", "store_id",
                    "user_id_request", "identity_attestation", "identity_cas_allowed",
                    "required_fields", "next_owner", "next_stage"):
            self.assertEqual(actual[key], self.request[key])
        self.assertEqual(actual["identity_status"], "REFERENCE_AVAILABLE")
        self.assertEqual(actual["user_id_request"], "NONE_ALREADY_RECEIVED")
        self.assertEqual(self.request["identity_binding_status"],
                         "REFERENCE_CORRELATED_NOT_ATTESTED")
        self.assertIsNone(actual["partner_center_display_name"])
        self.assertFalse(actual["identity_cas_allowed"])

    def test_artifact_source_request_and_family_match(self):
        self.assertEqual(self.request["pre_identity_exe"]["sha256"],
                         self.receipt["executable_sha256"])
        self.assertEqual(self.request["pre_identity_exe"]["bytes"],
                         self.receipt["executable_bytes"])
        self.assertEqual(self.request["identity_return_target"]["source_sha"],
                         self.job["source_sha"])
        self.assertEqual(self.request["identity_return_target"]["request_id"],
                         self.job["request_id"])
        self.assertEqual(self.request["partner_center_registration_type"], "MSIX_OR_PWA_APP")
        self.assertEqual(self.receipt["msix_status"], "NOT_BUILT")
        self.assertEqual(self.request["windows_gui_status"], "UNVERIFIED")
        self.assertEqual(self.request["artifact_zip_sha256"],
                         "dfd8907a28cb7abfe7eae310ea66b738f5dd9612aa0fbe1a4fb742ea9e99a4bf")

    def test_wrong_source_request_and_reference_fail_closed(self):
        for field, wrong in (("source_sha", "f" * 40), ("request_id", "wrong-request")):
            with self.subTest(field=field):
                with self.assertRaises(RegistrationContractError):
                    registration_request(self.job, {**self.receipt, field: wrong}, self.reference)
                with self.assertRaises(RegistrationContractError):
                    registration_request(self.job, self.receipt, {**self.reference, field: wrong})

    def test_original_immutable_and_cohort_not_stable(self):
        old = load("APP_CANARY_PACKAGE_JOB.json")
        self.assertNotEqual(old["source_sha"], self.job["source_sha"])
        self.assertNotEqual(old["request_id"], self.job["request_id"])
        self.assertEqual(old["slug"], self.job["slug"])
        cohort = load("APP_COHORT_ROTATION.json")
        self.assertFalse(cohort["factory_stable"])
        self.assertEqual(cohort["max_products"], 5)
        slot = next(p for p in cohort["products"] if p["slot"] == 1)
        self.assertEqual(slot["source_sha"], old["source_sha"])
        self.assertEqual(slot["improvement_revision"]["source_sha"], self.job["source_sha"])
        self.assertEqual(slot["improvement_revision"]["request_id"], self.job["request_id"])

if __name__ == "__main__":
    unittest.main()
