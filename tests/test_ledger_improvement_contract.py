"""Read-only provenance regression for improved Ledger revision and frozen prior request."""
import unittest
from pathlib import Path

from tools.app_registration_contract import load_json, registration_request

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs"


class LedgerImprovementContractTests(unittest.TestCase):
    def test_improved_job_receipt_registration_correlate(self):
        job = load_json(DOC / "APP_LEDGER_IMPROVEMENT_PACKAGE_JOB.json")
        receipt = load_json(DOC / "APP_LEDGER_IMPROVEMENT_EXE_RECEIPT.json")
        registered = load_json(DOC / "APP_LEDGER_IMPROVEMENT_REGISTRATION_REQUEST.json")
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
        self.assertFalse(registered["identity_cas_allowed"])
        self.assertEqual(registered["partner_center_selection"], "MSIX or PWA app")
        self.assertIsNone(registered["partner_center_display_name"])
        self.assertEqual(job["request_id"], "app-file-integrity-ledger-" + job["source_sha"][:12])

    def test_prior_frozen_ledger_job_is_not_rewritten(self):
        old = load_json(DOC / "APP_LEDGER_PACKAGE_JOB.json")
        new = load_json(DOC / "APP_LEDGER_IMPROVEMENT_PACKAGE_JOB.json")
        self.assertEqual(old["source_sha"],
                         "deaa9f324326a1ee276596c325f7a360adf27877")
        self.assertEqual(old["request_id"],
                         "app-file-integrity-ledger-deaa9f324326")
        self.assertNotEqual(old["source_sha"], new["source_sha"])
        self.assertNotEqual(old["request_id"], new["request_id"])

    def test_new_receipt_is_not_msix_or_identity_attestation(self):
        receipt = load_json(DOC / "APP_LEDGER_IMPROVEMENT_EXE_RECEIPT.json")
        self.assertEqual(receipt["msix_status"], "NOT_BUILT")
        self.assertIsNone(receipt["store_id"])
        self.assertEqual(receipt["official_identity_status"], "NOT_COLLECTED")
        self.assertEqual(receipt["status"], "EXE_QA_UNSIGNED")


if __name__ == "__main__":
    unittest.main()
