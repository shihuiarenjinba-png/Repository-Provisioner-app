"""APP registration routing tests: no Partner Center network or Identity CAS."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.app_registration_contract import RegistrationContractError, load_json, registration_request

JOB = {
    "schema_version": "1.0", "product_type": "APP", "source_factory": "AI-App-Factory",
    "source_repository": "shihuiarenjinba-png/AI-App-Factory",
    "source_branch": "codex/app-canary-offline-notes-20261027",
    "source_sha": "b83702c8948991cc3bd31745db5df64afaf6010f",
    "request_id": "app-offline-notes-canary-b83702c89489",
    "slug": "offline-notes-canary", "display_name": "Offline Notes Canary — Searchable Scratchpad",
    "requested_actions": ["BUILD_WINDOWS"],
}
RECEIPT = {
    **{k: JOB[k] for k in ("source_repository", "source_branch", "source_sha", "request_id",
                          "slug", "product_type", "display_name", "source_factory")},
    "schema_version": 1, "stage": "PRE_IDENTITY_WINDOWS_EXE", "status": "EXE_QA_UNSIGNED",
    "msix_status": "NOT_BUILT", "official_identity_status": "NOT_COLLECTED",
    "store_id": None, "executable": "offline-notes-canary.exe",
    "executable_sha256": "373b069b5a5f5ebdfea8785edc1c165030b6988b688739105585f34ed4501ab0",
    "executable_bytes": 11491423,
}
REFERENCE = {
    "source_sha": JOB["source_sha"], "request_id": JOB["request_id"], "slug": JOB["slug"],
    "reference_source": "USER_PROVIDED", "store_id": "9MZ8ZZTRTS17",
    "reserved_display_name": None,
    "identity_name": "OkinawaDesktopTools.OfflineNotesCanary",
    "publisher": "CN=46263F21-A700-41DB-8C9B-114C22FB82FC",
    "publisher_display_name": "Okinawa Desktop Tools",
    "pfn": "OkinawaDesktopTools.OfflineNotesCanary_j8yefg9jgfh58",
    "package_sid": "S-1-15-2-2642756671-247194623-3930721938-1552475434-2475515228-2865765061-1607947205",
}


class RegistrationContractTests(unittest.TestCase):
    def test_offline_notes_reference_binds_to_pinned_request_without_cas(self):
        result = registration_request(JOB, RECEIPT, REFERENCE)
        self.assertEqual(result["partner_center_registration_type"], "MSIX_OR_PWA_APP")
        self.assertEqual(result["partner_center_selection"], "MSIX or PWA app")
        self.assertEqual(result["identity_status"], "REFERENCE_AVAILABLE")
        self.assertEqual(result["user_id_request"], "NONE_ALREADY_RECEIVED")
        self.assertFalse(result["identity_cas_allowed"])
        self.assertIsNone(result["partner_center_display_name"])
        self.assertEqual(result["required_fields"], [])

    def test_jointly_forged_job_and_receipt_request_rejected(self):
        bad = "app-offline-notes-canary-000000000000"
        with self.assertRaisesRegex(RegistrationContractError, "request ID does not bind"):
            registration_request({**JOB, "request_id": bad},
                                 {**RECEIPT, "request_id": bad})

    def test_jointly_wrong_product_request_rejected(self):
        bad = "app-other-product-" + JOB["source_sha"][:12]
        with self.assertRaisesRegex(RegistrationContractError, "request ID does not bind"):
            registration_request({**JOB, "request_id": bad},
                                 {**RECEIPT, "request_id": bad})

    def test_jointly_changed_source_with_old_request_rejected(self):
        bad_sha = "f" * 40
        with self.assertRaisesRegex(RegistrationContractError, "request ID does not bind"):
            registration_request({**JOB, "source_sha": bad_sha},
                                 {**RECEIPT, "source_sha": bad_sha})

    def test_exe_intermediate_does_not_change_msix_registration(self):
        result = registration_request(JOB, RECEIPT)
        self.assertEqual(result["packaging_family"], "MSIX")
        self.assertEqual(result["partner_center_registration_type"], "MSIX_OR_PWA_APP")
        self.assertEqual(result["identity_status"], "WAITING_USER_IDENTITY")
        self.assertEqual(len(result["required_fields"]), 7)

    def test_mismatched_source_sha_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "source_sha"):
            registration_request(JOB, {**RECEIPT, "source_sha": "f" * 40}, REFERENCE)

    def test_mismatched_request_id_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "request_id"):
            registration_request(JOB, RECEIPT, {**REFERENCE, "request_id": "another-request-0001"})

    def test_forged_identity_attestation_fields_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "unexpected"):
            registration_request(JOB, RECEIPT, {**REFERENCE, "authenticated_account": "operator"})

    def test_wrong_pfn_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "PFN"):
            registration_request(JOB, RECEIPT, {**REFERENCE, "pfn": "Wrong.Product_j8yefg9jgfh58"})

    def test_receipt_with_store_identity_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "Store ID"):
            registration_request(JOB, {**RECEIPT, "store_id": REFERENCE["store_id"]}, REFERENCE)

    def test_receipt_with_msix_claim_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "MSIX"):
            registration_request(JOB, {**RECEIPT, "msix_status": "BUILT"})

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "input.json"
            p.write_text('{"request_id":"good","request_id":"bad"}', encoding="utf-8")
            with self.assertRaisesRegex(RegistrationContractError, "duplicate JSON key"):
                load_json(p)

    def test_untrusted_product_type_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "APP job"):
            registration_request({**JOB, "product_type": "GAME"}, RECEIPT)


    def test_unknown_job_action_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "unsupported APP job action"):
            registration_request({**JOB, "requested_actions": ["BUILD_WINDOWS", "DELETE_FILES"]}, RECEIPT)

    def test_duplicate_job_action_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "duplicate APP job action"):
            registration_request({**JOB, "requested_actions": ["BUILD_WINDOWS", "BUILD_WINDOWS"]}, RECEIPT)

    def test_non_string_job_action_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "unsupported APP job action"):
            registration_request({**JOB, "requested_actions": ["BUILD_WINDOWS", {"action": "LOOKUP_OFFICIAL_IDENTITY"}]}, RECEIPT)

    def test_missing_build_action_rejected(self):
        with self.assertRaisesRegex(RegistrationContractError, "must request BUILD_WINDOWS"):
            registration_request({**JOB, "requested_actions": ["LOOKUP_OFFICIAL_IDENTITY"]}, RECEIPT)

    def test_approved_multi_action_job_remains_compatible(self):
        approved = ["BUILD_WINDOWS", "INSPECT_PACKAGE", "LOOKUP_OFFICIAL_IDENTITY",
                    "PROPOSE_GITHUB_RETURN"]
        result = registration_request({**JOB, "requested_actions": approved}, RECEIPT, REFERENCE)
        self.assertEqual(result["identity_status"], "REFERENCE_AVAILABLE")
        self.assertFalse(result["identity_cas_allowed"])


if __name__ == "__main__":
    unittest.main()
