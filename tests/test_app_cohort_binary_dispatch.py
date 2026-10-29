"""Cohort binary gate integration: five explicit ZIPs, no false readiness."""
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.app_artifact_binary_verify import ArtifactVerificationError
from tools.app_cohort_dispatch import build_dispatch, verify_binary_dispatch
from tools.app_registration_contract import RegistrationContractError


class CohortBinaryDispatchTests(unittest.TestCase):
    def setUp(self):
        self.dispatch = build_dispatch()
        self.paths = {row["slug"]: "/not/a/real/" + row["slug"] + ".zip"
                      for row in self.dispatch["products"]}

    def test_contract_only_does_not_claim_binary_verified(self):
        self.assertEqual(self.dispatch["product_count"], 5)
        self.assertEqual(self.dispatch["binary_verified_count"], 0)
        self.assertFalse(self.dispatch["downstream_binary_gate_pass"])
        self.assertEqual(self.dispatch["verification_scope"],
                         "CONTRACT_ONLY_NO_LOCAL_BINARY_CHECK")

    def test_missing_product_zip_fails_closed(self):
        incomplete = dict(self.paths)
        incomplete.pop("focus-session-desk")
        with self.assertRaisesRegex(RegistrationContractError,
                                    "exactly five explicitly mapped"):
            verify_binary_dispatch(self.dispatch, incomplete)

    def test_unexpected_product_zip_fails_closed(self):
        extra = dict(self.paths, unknown_product="/tmp/unknown.zip")
        with self.assertRaisesRegex(RegistrationContractError,
                                    "exactly five explicitly mapped"):
            verify_binary_dispatch(self.dispatch, extra)

    def test_real_missing_zip_fails_closed(self):
        with self.assertRaisesRegex(RegistrationContractError,
                                    "binary gate failed"):
            verify_binary_dispatch(self.dispatch, self.paths)

    def test_corrupt_zip_fails_closed_even_if_pinned_path_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            corrupt = Path(directory) / "corrupt.zip"
            corrupt.write_bytes(b"this is not a ZIP")
            paths = {slug: str(corrupt) for slug in self.paths}
            with self.assertRaisesRegex(RegistrationContractError,
                                        "binary gate failed"):
                verify_binary_dispatch(self.dispatch, paths)

    def test_all_five_matching_proofs_pass_without_claiming_msix(self):
        original = copy.deepcopy(self.dispatch)
        by_slug = {row["slug"]: row for row in original["products"]}
        def checked_verify(path, job, zip_sha):
            row = by_slug[job["slug"]]
            self.assertEqual(zip_sha, row["artifact_zip_sha256"])
            self.assertEqual(path, Path(self.paths[job["slug"]]))
            return {
                "status": "BINARY_VERIFIED", "slug": job["slug"],
                "source_sha": row["source_sha"], "request_id": row["request_id"],
                "zip_sha256": zip_sha,
                "exe_sha256": row["pre_identity_exe"]["sha256"],
                "exe_bytes": row["pre_identity_exe"]["bytes"],
                "identity_cas_allowed": False, "msix_status": "NOT_BUILT",
                "windows_gui_status": "UNVERIFIED",
            }
        with patch("tools.app_artifact_binary_verify.verify",
                   side_effect=checked_verify) as mock:
            result = verify_binary_dispatch(original, self.paths)
        self.assertEqual(mock.call_count, 5)
        self.assertTrue(result["downstream_binary_gate_pass"])
        self.assertEqual(result["binary_verified_count"], 5)
        self.assertFalse(result["factory_stable"])
        for row in result["products"]:
            self.assertFalse(row["post_identity_ready"])
            self.assertFalse(row["msix_built"])
            self.assertFalse(row["windows_gui_pass"])
            self.assertEqual(row["binary_verification"]["status"], "BINARY_VERIFIED")

    def test_mismatched_exe_proof_fails_even_if_verifier_claims_success(self):
        first = self.dispatch["products"][0]
        fake = {
            "status": "BINARY_VERIFIED", "slug": first["slug"],
            "source_sha": first["source_sha"], "request_id": first["request_id"],
            "zip_sha256": first["artifact_zip_sha256"],
            "exe_sha256": "0" * 64,
            "exe_bytes": first["pre_identity_exe"]["bytes"],
            "identity_cas_allowed": False, "msix_status": "NOT_BUILT",
            "windows_gui_status": "UNVERIFIED",
        }
        with patch("tools.app_artifact_binary_verify.verify", return_value=fake):
            with self.assertRaisesRegex(RegistrationContractError,
                                        "binary proof inconsistent"):
                verify_binary_dispatch(self.dispatch, self.paths)


if __name__ == "__main__":
    unittest.main()
