"""Pin the third APP cohort's actual Windows EXE receipt to Provisioner schema."""
import json
from pathlib import Path
import unittest

from tools.app_registration_contract import registration_request, RegistrationContractError

ROOT = Path(__file__).resolve().parents[1]
JOB = json.loads((ROOT / "docs/APP_LEDGER_PACKAGE_JOB.json").read_text(encoding="utf-8"))
RECEIPT = json.loads((ROOT / "docs/APP_LEDGER_EXE_RECEIPT.json").read_text(encoding="utf-8"))
REQUEST = json.loads((ROOT / "docs/APP_COHORT_LEDGER_REGISTRATION_REQUEST.json").read_text(encoding="utf-8"))


class LedgerCohortContractTests(unittest.TestCase):
    def test_real_receipt_matches_exact_job(self):
        result = registration_request(JOB, RECEIPT)
        for key in ("slug", "source_sha", "request_id", "partner_center_registration_type"):
            self.assertEqual(result[key], REQUEST[key])
        self.assertEqual(result["partner_center_selection"], "MSIX or PWA app")
        self.assertEqual(result["identity_status"], "WAITING_USER_IDENTITY")
        self.assertIsNone(result["partner_center_display_name"])
        self.assertFalse(result["identity_cas_allowed"])

    def test_modified_receipt_source_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "source_sha"):
            registration_request(JOB, {**RECEIPT, "source_sha": "f" * 40})

    def test_unapproved_identity_in_exe_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "Store ID"):
            registration_request(JOB, {**RECEIPT, "store_id": "9MZ8ZZTRTS17"})

    def test_exe_sha_and_handoff_are_exact(self):
        self.assertEqual(RECEIPT["executable_sha256"], REQUEST["pre_identity_exe"]["sha256"])
        self.assertEqual(RECEIPT["executable_bytes"], REQUEST["pre_identity_exe"]["bytes"])
        self.assertEqual(RECEIPT["request_id"], REQUEST["identity_return_target"]["request_id"])
        self.assertEqual(RECEIPT["source_sha"], REQUEST["identity_return_target"]["source_sha"])
        self.assertEqual(REQUEST["packaging_family"], "MSIX")
        self.assertEqual(REQUEST["msix_status"], "NOT_BUILT")


if __name__ == "__main__":
    unittest.main()
