"""Regression for actual APP ZIP/PE byte verification; no network required."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from tools.app_artifact_binary_verify import ArtifactVerificationError, verify


class ArtifactBinaryVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "artifact.zip"
        self.job = {"slug": "test-desk", "source_sha": "a" * 40,
                    "source_branch": "codex/test", "request_id": "app-test-desk-" + "a" * 12,
                    "source_repository": "shihuiarenjinba-png/AI-App-Factory"}
        self.exe = bytearray((i * 47 + 13) % 256 for i in range(4096))
        self.exe[:2] = b"MZ"
        struct.pack_into("<I", self.exe, 0x3c, 128)
        self.exe[128:132] = b"PE\0\0"
        struct.pack_into("<H", self.exe, 132, 0x8664)
        self.receipt = dict(self.job, status="EXE_QA_UNSIGNED", stage="PRE_IDENTITY_WINDOWS_EXE",
                            executable="test-desk.exe", executable_bytes=len(self.exe),
                            executable_sha256=hashlib.sha256(self.exe).hexdigest(),
                            msix_status="NOT_BUILT", official_identity_status="NOT_COLLECTED")
        self.handoff = dict(self.job, product_type="APP", packaging_family="MSIX",
                            partner_center_registration_type="MSIX_OR_PWA_APP",
                            partner_center_selection="MSIX or PWA app", identity_cas_allowed=False,
                            msix_status="NOT_BUILT", windows_gui_status="UNVERIFIED",
                            identity_return_target={"owner": "36_MIN_WINDOWS_E2E",
                                                    "stage": "AUTHENTICATED_IDENTITY_EVIDENCE_AND_CAS"})

    def archive(self, exe=None, receipt=None, handoff=None, duplicate=False):
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("test-desk.exe", bytes(self.exe if exe is None else exe))
            archive.writestr("exe-receipt.json", json.dumps(self.receipt if receipt is None else receipt))
            archive.writestr("registration-handoff.json", json.dumps(self.handoff if handoff is None else handoff))
            if duplicate:
                archive.writestr("test-desk.exe", bytes(self.exe))
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_real_binary_passes_without_claiming_msix_or_gui(self):
        result = verify(self.path, self.job, self.archive())
        self.assertEqual(result["status"], "BINARY_VERIFIED")
        self.assertFalse(result["identity_cas_allowed"])
        self.assertEqual(result["msix_status"], "NOT_BUILT")
        self.assertEqual(result["windows_gui_status"], "UNVERIFIED")

    def test_wrong_pinned_zip_digest_fails(self):
        self.archive()
        with self.assertRaisesRegex(ArtifactVerificationError, "ZIP SHA-256 mismatch"):
            verify(self.path, self.job, "b" * 64)

    def test_corrupted_exe_with_consistent_zip_digest_fails(self):
        altered = bytearray(self.exe)
        altered[-1] ^= 1
        digest = self.archive(exe=altered)
        with self.assertRaisesRegex(ArtifactVerificationError, "EXE SHA-256 mismatch"):
            verify(self.path, self.job, digest)

    def test_wrong_request_fails_even_when_both_metadata_agree(self):
        bad = dict(self.job, request_id="app-test-desk-" + "b" * 12)
        digest = self.archive()
        with self.assertRaisesRegex(ArtifactVerificationError, "request/source mismatch"):
            verify(self.path, bad, digest)

    def test_handoff_cas_claim_fails(self):
        digest = self.archive(handoff=dict(self.handoff, identity_cas_allowed=True))
        with self.assertRaisesRegex(ArtifactVerificationError, "unsafe handoff state"):
            verify(self.path, self.job, digest)

    def test_wrong_pe_machine_fails(self):
        altered = bytearray(self.exe)
        struct.pack_into("<H", altered, 132, 0x014c)
        digest = self.archive(exe=altered)
        with self.assertRaisesRegex(ArtifactVerificationError, "not an AMD64 PE"):
            verify(self.path, self.job, digest)

    def test_duplicate_zip_member_fails(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            digest = self.archive(duplicate=True)
        with self.assertRaisesRegex(ArtifactVerificationError, "unexpected, missing or duplicate"):
            verify(self.path, self.job, digest)


if __name__ == "__main__":
    unittest.main()
