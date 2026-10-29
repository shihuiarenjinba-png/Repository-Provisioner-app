"""Regression coverage for APP cycle 9 strict handoff (offline, no Store calls)."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.app_preidentity_strict_handoff import (
    RegistrationContractError, main, strict_job, validate_strict_schema,
    verify_exe,
)
from tools.app_registration_contract import registration_request

ROOT = Path(__file__).resolve().parents[1]
JOB_PATH = ROOT / "docs/APP_NOTES_CYCLE9_STRICT_JOB.json"
REF_PATH = ROOT / "docs/APP_NOTES_CYCLE9_IDENTITY_REFERENCE.json"


def fake_pe():
    data = bytearray(2048)
    data[0:2] = b"MZ"
    data[60:64] = (128).to_bytes(4, "little")
    data[128:132] = b"PE\x00\x00"
    return bytes(data)


def receipt(job, binary):
    return {
        **{k: job[k] for k in ("source_repository", "source_branch", "source_sha",
                               "request_id", "slug", "product_type", "display_name",
                               "source_factory")},
        "schema_version": 1, "stage": "PRE_IDENTITY_WINDOWS_EXE",
        "status": "EXE_QA_UNSIGNED", "msix_status": "NOT_BUILT",
        "official_identity_status": "NOT_COLLECTED", "store_id": None,
        "executable": "offline-notes-canary.exe",
        "executable_sha256": hashlib.sha256(binary).hexdigest(),
        "executable_bytes": len(binary),
    }


class Cycle9StrictHandoffTests(unittest.TestCase):
    def setUp(self):
        self.job = json.loads(JOB_PATH.read_text(encoding="utf-8"))
        self.reference = json.loads(REF_PATH.read_text(encoding="utf-8"))
        self.binary = fake_pe()
        self.receipt = receipt(self.job, self.binary)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.exe = self.folder / "offline-notes-canary.exe"
        self.exe.write_bytes(self.binary)
        self.receipt_path = self.folder / "exe-receipt.json"
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")

    def args(self):
        return [
            "--receipt", str(self.receipt_path), "--exe", str(self.exe),
            "--identity-reference", str(REF_PATH),
            "--expected-source-sha", self.job["source_sha"],
            "--expected-request-id", self.job["request_id"],
            "--job-output", str(self.folder / "job.json"),
            "--routing-output", str(self.folder / "routing.json"),
        ]

    def test_exact_schema_no_routing_fields_in_job(self):
        validate_strict_schema(self.job)
        self.assertEqual(strict_job(self.receipt), self.job)
        self.assertEqual(self.job["source_sha"],
                         "2bc5eb249c5d23ee269e75f3b27ee2a7be359791")
        self.assertEqual(self.job["request_id"],
                         "app-offline-notes-canary-2bc5eb249c5d")
        self.assertTrue(self.job["dry_run"])

    def test_reference_is_correlated_but_never_attested(self):
        result = registration_request(self.job, self.receipt, self.reference)
        self.assertEqual(result["identity_status"], "REFERENCE_AVAILABLE")
        self.assertEqual(result["user_id_request"], "NONE_ALREADY_RECEIVED")
        self.assertFalse(result["identity_cas_allowed"])
        self.assertIsNone(result["partner_center_display_name"])
        self.assertEqual(result["partner_center_selection"], "MSIX or PWA app")
        self.assertEqual(result["packaging_family"], "MSIX")

    def test_verified_exe_emits_separate_job_and_routing(self):
        self.assertEqual(main(self.args()), 0)
        job = json.loads((self.folder / "job.json").read_text(encoding="utf-8"))
        routing = json.loads((self.folder / "routing.json").read_text(encoding="utf-8"))
        self.assertEqual(job, self.job)
        self.assertNotIn("packaging_family", job)
        self.assertEqual(routing["pre_identity_exe"]["receipt_only_not_binary_reverification"], False)
        self.assertEqual(routing["identity_return_target"]["request_id"], job["request_id"])
        self.assertEqual(routing["commercial_quality_status"], "HOLD")

    def test_modified_exe_is_rejected_without_outputs(self):
        self.exe.write_bytes(self.binary[:-1] + b"X")
        with self.assertRaisesRegex(RegistrationContractError, "SHA-256"):
            main(self.args())
        self.assertFalse((self.folder / "job.json").exists())

    def test_bad_pe_header_is_rejected(self):
        broken = b"ZZ" + self.binary[2:]
        self.exe.write_bytes(broken)
        self.receipt["executable_sha256"] = hashlib.sha256(broken).hexdigest()
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        with self.assertRaisesRegex(RegistrationContractError, "Windows PE"):
            main(self.args())

    def test_source_sha_mismatch_is_rejected(self):
        args = self.args()
        args[args.index("--expected-source-sha") + 1] = "f" * 40
        with self.assertRaisesRegex(RegistrationContractError, "unexpected source SHA"):
            main(args)

    def test_request_mismatch_is_rejected(self):
        args = self.args()
        args[args.index("--expected-request-id") + 1] = "other-request"
        with self.assertRaisesRegex(RegistrationContractError, "unexpected request ID"):
            main(args)

    def test_identity_reference_mismatch_is_rejected(self):
        bad = dict(self.reference, source_sha="f" * 40)
        path = self.folder / "bad-reference.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        args = self.args()
        args[args.index("--identity-reference") + 1] = str(path)
        with self.assertRaisesRegex(RegistrationContractError, "Identity reference mismatch"):
            main(args)

    def test_existing_output_is_not_overwritten(self):
        target = self.folder / "job.json"
        target.write_text("DO NOT OVERWRITE", encoding="utf-8")
        with self.assertRaisesRegex(RegistrationContractError, "output exists"):
            main(self.args())
        self.assertEqual(target.read_text(encoding="utf-8"), "DO NOT OVERWRITE")
        self.assertFalse((self.folder / "routing.json").exists())

    def test_duplicate_receipt_json_keys_rejected(self):
        self.receipt_path.write_text('{"source_sha":"a","source_sha":"b"}',
                                     encoding="utf-8")
        with self.assertRaisesRegex(RegistrationContractError, "duplicate JSON key"):
            main(self.args())


if __name__ == "__main__":
    unittest.main()
