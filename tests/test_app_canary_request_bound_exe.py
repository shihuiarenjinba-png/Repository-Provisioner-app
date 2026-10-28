"""Fail-closed tests for one pinned request-bound Windows EXE stage."""
import hashlib
import json
import subprocess
from pathlib import Path
import tempfile
import unittest

from package_identity_provisioner import ProductConfig
from tools.app_canary_request_bound_exe import (
    EXPECTED_REQUEST_ID, EXPECTED_SOURCE_SHA, JOB_PATH, ROOT,
    validate_canary_job, verify_clean_factory_checkout, verify_exe_receipt,
)


class RequestBoundExeTests(unittest.TestCase):
    def setUp(self):
        self.config = ProductConfig.load(ROOT / "config.json")
        self.raw = json.loads(JOB_PATH.read_text(encoding="utf-8"))
        self.job = validate_canary_job(self.raw, self.config)

    def test_committed_job_is_exactly_pinned(self):
        self.assertEqual(self.job.request_id, EXPECTED_REQUEST_ID)
        self.assertEqual(self.job.source_sha, EXPECTED_SOURCE_SHA)

    def test_rejects_wrong_request_id(self):
        with self.assertRaisesRegex(ValueError, "immutable"):
            validate_canary_job({**self.raw, "request_id": "app-other-request"}, self.config)

    def test_rejects_other_source_sha(self):
        with self.assertRaisesRegex(ValueError, "immutable"):
            validate_canary_job({**self.raw, "source_sha": "a" * 40}, self.config)

    def test_rejects_dry_run_mutation(self):
        with self.assertRaisesRegex(ValueError, "immutable"):
            validate_canary_job({**self.raw, "dry_run": True}, self.config)

    def _local_git_checkout(self, root):
        source = Path(root) / "source"
        source.mkdir()
        subprocess.run(["git", "init", "--quiet", str(source)], check=True)
        (source / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (source / "builder.py").write_text("print('clean')\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore", "builder.py"], cwd=source, check=True)
        subprocess.run([
            "git", "-c", "user.name=QA", "-c", "user.email=qa@example.com",
            "commit", "--quiet", "-m", "baseline",
        ], cwd=source, check=True)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        return source, sha

    def test_clean_factory_checkout_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = self._local_git_checkout(tmp)
            verify_clean_factory_checkout(source, sha)

    def test_dirty_factory_checkout_rejected_before_builder_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, sha = self._local_git_checkout(tmp)
            cases = (
                ("tracked modification", source / "builder.py", "print('tampered')\n"),
                ("untracked payload", source / "extra.py", "print('untracked')\n"),
                ("ignored payload", source / "ignored.txt", "unsafe\n"),
            )
            for name, path, payload in cases:
                with self.subTest(name=name):
                    path.write_text(payload, encoding="utf-8")
                    if name == "ignored payload":
                        self.assertEqual(subprocess.run(
                            ["git", "check-ignore", "--quiet", "ignored.txt"],
                            cwd=source, check=False,
                        ).returncode, 0)
                    with self.assertRaisesRegex(ValueError, "modified, untracked or ignored"):
                        verify_clean_factory_checkout(source, sha)
                    if path.name == "builder.py":
                        path.write_text("print('clean')\n", encoding="utf-8")
                    else:
                        path.unlink()
            verify_clean_factory_checkout(source, sha)

    def test_factory_checkout_wrong_sha_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, _ = self._local_git_checkout(tmp)
            with self.assertRaisesRegex(ValueError, "pinned source"):
                verify_clean_factory_checkout(source, "a" * 40)

    def _evidence(self, root):
        output = Path(root) / "artifact"
        output.mkdir()
        exe = output / (self.job.slug + ".exe")
        exe.write_bytes(b"MZ" + b"\x00" * 2048)
        receipt = {
            "schema_version": 1, "stage": "PRE_IDENTITY_WINDOWS_EXE",
            "status": "EXE_QA_UNSIGNED", "source_repository": self.job.source_repository,
            "source_factory": self.job.source_factory, "source_branch": self.job.source_branch,
            "source_sha": self.job.source_sha, "request_id": self.job.request_id,
            "product_type": self.job.product_type, "slug": self.job.slug,
            "display_name": self.job.display_name, "executable": exe.name,
            "executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
            "executable_bytes": exe.stat().st_size,
            "official_identity_status": "NOT_COLLECTED", "store_id": None,
            "msix_status": "NOT_BUILT",
        }
        (output / "exe-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        return output, receipt

    def test_exact_receipt_and_exe_hash_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, receipt = self._evidence(tmp)
            self.assertEqual(verify_exe_receipt(self.job, output), receipt)

    def test_request_id_null_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, receipt = self._evidence(tmp)
            receipt["request_id"] = None
            (output / "exe-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "request_id"):
                verify_exe_receipt(self.job, output)

    def test_exe_tamper_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = self._evidence(tmp)
            with (output / (self.job.slug + ".exe")).open("r+b") as handle:
                handle.seek(32)
                handle.write(b"X")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                verify_exe_receipt(self.job, output)

    def test_store_identity_cannot_be_fabricated(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, receipt = self._evidence(tmp)
            receipt["store_id"] = "9MZ8ZZTRTS17"
            (output / "exe-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "store_id"):
                verify_exe_receipt(self.job, output)

    def test_unexpected_artifact_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = self._evidence(tmp)
            (output / "unrelated.msix").write_text("fake", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected"):
                verify_exe_receipt(self.job, output)


if __name__ == "__main__":
    unittest.main()
