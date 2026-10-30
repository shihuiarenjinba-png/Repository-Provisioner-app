"""Cross-boundary APP Factory -> Provisioner real-byte intake tests."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.app_artifact_intake import verify_artifact

SHA = "dd94bd2cd52a84653623f6ccdf727a6cf7903b98"


def fixture(root: Path):
    job = {
        "schema_version": "1.0",
        "request_id": "app-focus-strict-dd94bd2cd52a",
        "product_type": "APP",
        "source_factory": "AI-App-Factory",
        "source_repository": "shihuiarenjinba-png/AI-App-Factory",
        "source_branch": "codex/app-preidentity-strict-job-20261030",
        "source_sha": SHA,
        "slug": "focus-session-desk",
        "display_name": "Focus Session Desk — Offline Timer and Task Checklist",
        "target_owner": "shihuiarenjinba-png",
        "dry_run": True,
        "requested_actions": ["BUILD_WINDOWS"],
    }
    # Synthetic valid-header PE, never presented as a real application.
    data = bytearray(2048)
    data[:2] = b"MZ"
    data[0x3C:0x40] = (0x80).to_bytes(4, "little")
    data[0x80:0x84] = b"PE\0\0"
    exe = root / "focus-session-desk.exe"
    exe.write_bytes(data)
    receipt = {
        "schema_version": 1,
        "stage": "PRE_IDENTITY_WINDOWS_EXE",
        "status": "EXE_QA_UNSIGNED",
        "source_factory": job["source_factory"],
        "source_repository": job["source_repository"],
        "source_branch": job["source_branch"],
        "source_sha": job["source_sha"],
        "request_id": job["request_id"],
        "product_type": "APP",
        "slug": job["slug"],
        "display_name": job["display_name"],
        "executable": exe.name,
        "executable_sha256": hashlib.sha256(data).hexdigest(),
        "executable_bytes": len(data),
        "official_identity_status": "NOT_COLLECTED",
        "store_id": None,
        "msix_status": "NOT_BUILT",
    }
    return job, receipt, exe


class ArtifactIntakeTests(unittest.TestCase):
    def test_real_bytes_verified_but_head_not_assumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, receipt, exe = fixture(Path(tmp))
            proof = verify_artifact(job, receipt, exe)
            self.assertEqual(proof["status"], "ARTIFACT_VERIFIED_HEAD_UNCHECKED")
            self.assertTrue(proof["artifact_bytes_verified"])
            self.assertEqual(proof["exe_sha256"], receipt["executable_sha256"])
            self.assertEqual(proof["source_sha"], SHA)
            self.assertEqual(proof["source_head_verification"], "NOT_CHECKED")
            self.assertEqual(proof["partner_center_registration_type"], "MSIX_OR_PWA_APP")
            self.assertFalse(proof["identity_cas_allowed"])
            self.assertEqual(proof["commercial_quality_status"], "HOLD")

    def test_authenticated_head_gate_is_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, receipt, exe = fixture(Path(tmp))
            with patch("tools.app_artifact_intake.verify_github_head", return_value=SHA) as head:
                proof = verify_artifact(job, receipt, exe, verify_head=True)
            head.assert_called_once_with(job)
            self.assertEqual(proof["status"], "PRE_IDENTITY_READY")
            self.assertEqual(proof["source_head_sha"], SHA)
            self.assertFalse(proof["identity_cas_allowed"])

    def test_modified_exe_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, receipt, exe = fixture(Path(tmp))
            with exe.open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaises(ValueError):
                verify_artifact(job, receipt, exe)

    def test_job_receipt_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, receipt, exe = fixture(Path(tmp))
            for field, wrong in [
                ("source_sha", "a" * 40),
                ("request_id", "app-other-123456"),
                ("source_branch", "codex/another-branch"),
                ("display_name", "Different Product"),
            ]:
                with self.subTest(field=field):
                    changed = copy.deepcopy(job)
                    changed[field] = wrong
                    with self.assertRaises(ValueError):
                        verify_artifact(changed, receipt, exe)

    def test_unsafe_job_and_wrong_filename_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, receipt, exe = fixture(Path(tmp))
            job["dry_run"] = False
            with self.assertRaises(ValueError):
                verify_artifact(job, receipt, exe)
            job["dry_run"] = True
            job["extra_field"] = "untrusted"
            with self.assertRaises(ValueError):
                verify_artifact(job, receipt, exe)
            del job["extra_field"]
            renamed = exe.with_name("other.exe")
            renamed.write_bytes(exe.read_bytes())
            with self.assertRaises(ValueError):
                verify_artifact(job, receipt, renamed)

    def test_user_reference_is_not_identity_attestation(self):
        with tempfile.TemporaryDirectory() as tmp:
            job, receipt, exe = fixture(Path(tmp))
            reference = {
                "source_sha": SHA,
                "request_id": job["request_id"],
                "slug": job["slug"],
                "reference_source": "USER_PROVIDED",
                "store_id": "9P6452C61N7B",
                "identity_name": "Example.FocusSessionDesk",
                "publisher": "CN=00000000-0000-0000-0000-000000000000",
                "publisher_display_name": "Example Publisher",
                "pfn": "Example.FocusSessionDesk_abcdefghijklm",
                "package_sid": "S-1-15-2-1-2-3-4-5-6-7",
                "reserved_display_name": "Focus Session Desk",
            }
            proof = verify_artifact(job, receipt, exe, identity_reference=reference)
            self.assertEqual(proof["identity_status"], "REFERENCE_AVAILABLE")
            self.assertEqual(proof["identity_attestation"], "NOT_VERIFIED")
            self.assertFalse(proof["identity_cas_allowed"])
            reference["source_sha"] = "a" * 40
            with self.assertRaises(ValueError):
                verify_artifact(job, receipt, exe, identity_reference=reference)

    def test_cli_creates_proof_once_no_clobber(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job, receipt, exe = fixture(root)
            (root / "job.json").write_text(json.dumps(job), encoding="utf-8")
            (root / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            args = [
                sys.executable, "-m", "tools.app_artifact_intake",
                "--job", str(root / "job.json"),
                "--receipt", str(root / "receipt.json"),
                "--exe", str(exe), "--output", str(root / "proof.json"),
            ]
            first = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads((root / "proof.json").read_text())["status"],
                             "ARTIFACT_VERIFIED_HEAD_UNCHECKED")
            second = subprocess.run(args, capture_output=True, text=True, timeout=15)
            self.assertEqual(second.returncode, 2)
            self.assertIn("APP_ARTIFACT_INTAKE_HOLD", second.stderr)


if __name__ == "__main__":
    unittest.main()
