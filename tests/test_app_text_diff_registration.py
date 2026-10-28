"""Fourth APP cohort registration and immutable receipt checks."""
import json
from pathlib import Path
import unittest
from tools.app_registration_contract import registration_request, RegistrationContractError

ROOT=Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/"docs"/name).read_text(encoding="utf-8"))

class TextDiffRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.job=read("APP_TEXT_DIFF_PACKAGE_JOB.json")
        self.receipt=read("APP_TEXT_DIFF_EXE_RECEIPT.json")
        self.registration=read("APP_COHORT_TEXT_DIFF_REGISTRATION_REQUEST.json")

    def test_request_and_receipt_bind_without_identity(self):
        actual=registration_request(self.job,self.receipt)
        self.assertEqual(actual["identity_status"],"WAITING_USER_IDENTITY")
        self.assertEqual(actual["partner_center_registration_type"],"MSIX_OR_PWA_APP")
        self.assertFalse(actual["identity_cas_allowed"])
        self.assertEqual(self.job["source_sha"],self.receipt["source_sha"])
        self.assertEqual(self.job["request_id"],self.receipt["request_id"])
        self.assertEqual(self.registration["pre_identity_exe"]["sha256"],self.receipt["executable_sha256"])

    def test_registration_is_msix_and_unattested(self):
        self.assertEqual(self.registration["partner_center_selection"],"MSIX or PWA app")
        self.assertIsNone(self.registration["partner_center_display_name"])
        self.assertFalse(self.registration["reserved_display_name_verified"])
        self.assertEqual(self.registration["identity_return_target"]["owner"],"36_MIN_WINDOWS_E2E")
        self.assertEqual(len(self.registration["required_fields"]),7)

    def test_wrong_source_sha_rejected(self):
        with self.assertRaises(RegistrationContractError):
            registration_request(self.job,{**self.receipt,"source_sha":"f"*40})

if __name__=="__main__":
    unittest.main()
