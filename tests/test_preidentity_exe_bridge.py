"""APP Factory pre-Identity EXE -> Provisioner contract regressions."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from package_identity_provisioner import HoldError, Job, PackageBuilder, Provisioner
from test_app_exe_identity_resume import ReceiptBuilder
from test_package_identity_pipeline import (
    FakeBuilder, FakeGitHub, FakeIdentity, FakeSource, config, job,
)


class PreIdentityExeBridgeTests(unittest.TestCase):
    def test_real_exe_receipt_survives_missing_official_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, github = FakeIdentity(error=HoldError("not registered")), FakeGitHub()
            provisioner = Provisioner(
                config(), Path(tmp) / "state", Path(tmp) / "work",
                source=FakeSource(), builder=ReceiptBuilder(),
                identity=identity, github=github,
            )
            result = provisioner.run(job(), apply=True)
            self.assertEqual(result["status"], "HOLD")
            self.assertEqual(result["next_stage"], "OBTAIN_AUTHENTICATED_OFFICIAL_IDENTITY")
            self.assertEqual(result["package"]["kind"], "exe")
            self.assertRegex(result["package"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(Path(result["package"]["path"]).is_file())
            self.assertEqual(result["official_identity"]["status"], "UNVERIFIED")
            self.assertEqual(result["github_return"]["status"], "NOT_APPLIED")
            self.assertEqual(identity.calls, 1)
            self.assertEqual(github.calls, 0)

    def test_factory_builder_receives_exact_slug_and_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            (source / "tools").mkdir(parents=True)
            (source / "tools/build_windows_exe.py").write_text("# committed factory builder\n")
            output = Path(tmp) / "artifacts"
            output.mkdir()
            commands = []

            def fake_run(command, cwd, timeout):
                commands.append(command)
                if "--output" in command:
                    destination = Path(command[command.index("--output") + 1])
                    destination.mkdir()
                    exe = destination / "sample-product.exe"
                    exe.write_bytes(b"MZ" + b"x" * 2048)
                    data = job()
                    receipt = {
                        "schema_version": 1, "stage": "PRE_IDENTITY_WINDOWS_EXE",
                        "status": "EXE_QA_UNSIGNED", "product_type": data["product_type"],
                        "source_factory": data["source_factory"],
                        "source_repository": data["source_repository"],
                        "source_branch": data["source_branch"],
                        "source_sha": data["source_sha"], "request_id": data["request_id"],
                        "slug": data["slug"], "display_name": data["display_name"],
                        "executable": exe.name, "executable_bytes": exe.stat().st_size,
                        "executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
                        "official_identity_status": "NOT_COLLECTED",
                        "store_id": None, "msix_status": "NOT_BUILT",
                    }
                    (destination / "exe-receipt.json").write_text(json.dumps(receipt))
            with patch.object(PackageBuilder, "_run", side_effect=fake_run):
                PackageBuilder()._build_windows(source, Job.validate(job(), config()), output)
            self.assertEqual(len(commands), 2)
            self.assertEqual(commands[0][0:4], ["git", "cat-file", "-e", "HEAD:tools/build_windows_exe.py"])
            self.assertIn("--expected-sha", commands[1])
            self.assertEqual(commands[1][commands[1].index("--expected-sha") + 1], "a" * 40)
            self.assertEqual(commands[1][commands[1].index("--slug") + 1], "sample-product")
            self.assertEqual(commands[1][commands[1].index("--source-branch") + 1], job()["source_branch"])
            self.assertEqual(commands[1][commands[1].index("--request-id") + 1], job()["request_id"])

    def test_factory_builder_rejects_missing_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            (source / "tools").mkdir(parents=True)
            (source / "tools/build_windows_exe.py").write_text("# committed factory builder\n")
            output = Path(tmp) / "artifacts"
            output.mkdir()

            def fake_run(command, cwd, timeout):
                if "--output" in command:
                    destination = Path(command[command.index("--output") + 1])
                    destination.mkdir()
                    (destination / "sample-product.exe").write_bytes(b"MZ" + b"x" * 2048)
            with patch.object(PackageBuilder, "_run", side_effect=fake_run):
                with self.assertRaisesRegex(HoldError, "evidence is incomplete"):
                    PackageBuilder()._build_windows(
                        source, Job.validate(job(), config()), output)


    def test_mismatched_request_id_receipt_holds_before_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            (source / "tools").mkdir(parents=True)
            (source / "tools/build_windows_exe.py").write_text("# committed builder")
            output = Path(tmp) / "artifacts"
            output.mkdir()

            def fake_run(command, cwd, timeout):
                if "--output" in command:
                    dest = Path(command[command.index("--output") + 1])
                    dest.mkdir()
                    exe = dest / "sample-product.exe"
                    exe.write_bytes(b"MZ" + b"x" * 2048)
                    data = job()
                    (dest / "exe-receipt.json").write_text(json.dumps({
                        "schema_version": 1, "stage": "PRE_IDENTITY_WINDOWS_EXE",
                        "status": "EXE_QA_UNSIGNED", "product_type": data["product_type"],
                        "source_factory": data["source_factory"],
                        "source_repository": data["source_repository"],
                        "source_branch": data["source_branch"],
                        "source_sha": data["source_sha"], "request_id": "wrong-request",
                        "slug": data["slug"], "display_name": data["display_name"],
                        "executable": exe.name, "executable_bytes": exe.stat().st_size,
                        "executable_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
                        "official_identity_status": "NOT_COLLECTED",
                        "store_id": None, "msix_status": "NOT_BUILT",
                    }))
            with patch.object(PackageBuilder, "_run", side_effect=fake_run):
                with self.assertRaisesRegex(HoldError, "provenance"):
                    PackageBuilder()._build_windows(
                        source, Job.validate(job(), config()), output)


if __name__ == "__main__":
    unittest.main()
