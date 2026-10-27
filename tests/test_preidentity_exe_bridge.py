"""APP Factory pre-Identity EXE -> Provisioner contract regressions."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from package_identity_provisioner import ConflictError, HoldError, Job, PackageBuilder, Provisioner
from test_package_identity_pipeline import (
    FakeBuilder, FakeGitHub, FakeIdentity, FakeSource, config, job,
)


def write_factory_receipt(destination: Path, *, corrupt_sha: bool = False,
                          wrong_request: bool = False) -> None:
    raw = b"MZ" + b"x" * 2048
    (destination / "sample-product.exe").write_bytes(raw)
    receipt = {
        "schema_version": 1, "stage": "PRE_IDENTITY_WINDOWS_EXE",
        "status": "EXE_QA_UNSIGNED", "source_factory": "AI-App-Factory",
        "source_repository": config().source_repository,
        "source_branch": config().source_branch,
        "source_sha": "a" * 40,
        "request_id": "different-request" if wrong_request else job()["request_id"],
        "product_type": "APP",
        "slug": "sample-product", "display_name": "Sample Product",
        "executable": "sample-product.exe",
        "executable_sha256": ("0" * 64 if corrupt_sha else hashlib.sha256(raw).hexdigest()),
        "executable_bytes": len(raw), "official_identity_status": "NOT_COLLECTED",
        "store_id": None, "msix_status": "NOT_BUILT",
    }
    (destination / "exe-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")


class PreIdentityExeBridgeTests(unittest.TestCase):
    def test_real_exe_receipt_survives_missing_official_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, github = FakeIdentity(error=HoldError("not registered")), FakeGitHub()
            provisioner = Provisioner(
                config(), Path(tmp) / "state", Path(tmp) / "work",
                source=FakeSource(), builder=FakeBuilder(artifact_kind="exe"),
                identity=identity, github=github,
            )
            result = provisioner.run(job(), apply=True)
            self.assertEqual(result["status"], "HOLD")
            self.assertEqual(result["next_stage"], "OBTAIN_OFFICIAL_IDENTITY_AND_BUILD_MSIX")
            self.assertEqual(result["package"]["kind"], "exe")
            self.assertRegex(result["package"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(Path(result["package"]["path"]).is_file())
            self.assertEqual(result["official_identity"]["status"], "UNVERIFIED")
            self.assertEqual(result["github_return"]["status"], "NOT_APPLIED")
            self.assertEqual(identity.calls, 0)
            self.assertEqual(github.calls, 0)

    def test_operator_verified_identity_returns_after_exe_without_claiming_msix(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, github = FakeIdentity(), FakeGitHub()
            identity.evidence_path = Path(tmp) / "operator-export.json"
            provisioner = Provisioner(
                config(), Path(tmp) / "state", Path(tmp) / "work",
                source=FakeSource(), builder=FakeBuilder(artifact_kind="exe"),
                identity=identity, github=github,
            )
            result = provisioner.run(job(), apply=True)
            self.assertEqual(result["status"], "HOLD")
            self.assertEqual(result["package"]["kind"], "exe")
            self.assertEqual(result["github_return"]["status"], "APPLIED")
            self.assertEqual(result["official_identity"]["status"], "VERIFIED_OPERATOR_EXPORT")
            self.assertEqual(result["next_stage"], "GITHUB_PACKAGE_PINNED_EXE_AS_MSIX")
            self.assertEqual(result["source_factory"], "AI-App-Factory")
            self.assertEqual(result["display_name"], "Sample Product")
            self.assertEqual((identity.calls, github.calls), (1, 1))
            self.assertIsNone(result["windows_all_auto_record"])

    def test_operator_verified_identity_without_apply_stays_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity, github = FakeIdentity(), FakeGitHub()
            identity.evidence_path = Path(tmp) / "operator-export.json"
            result = Provisioner(
                config(), Path(tmp) / "state", Path(tmp) / "work",
                source=FakeSource(), builder=FakeBuilder(artifact_kind="exe"),
                identity=identity, github=github,
            ).run(job(), apply=False)
            self.assertEqual(result["status"], "HOLD")
            self.assertEqual(result["github_return"]["status"], "NOT_APPLIED")
            self.assertEqual(result["next_stage"], "APPLY_VERIFIED_GITHUB_RETURN")
            self.assertEqual((identity.calls, github.calls), (1, 1))

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
                    write_factory_receipt(destination)
            with patch.object(PackageBuilder, "_run", side_effect=fake_run):
                PackageBuilder()._build_windows(source, Job.validate(job(), config()), output)
            self.assertEqual(len(commands), 2)
            self.assertEqual(commands[0][0:4], ["git", "cat-file", "-e", "HEAD:tools/build_windows_exe.py"])
            self.assertIn("--expected-sha", commands[1])
            self.assertEqual(commands[1][commands[1].index("--expected-sha") + 1], "a" * 40)
            self.assertEqual(commands[1][commands[1].index("--slug") + 1], "sample-product")
            self.assertEqual(commands[1][commands[1].index("--source-branch") + 1], job()["source_branch"])
            self.assertEqual(commands[1][commands[1].index("--request-id") + 1], job()["request_id"])

    def test_factory_builder_rejects_request_provenance_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            (source / "tools").mkdir(parents=True)
            (source / "tools/build_windows_exe.py").write_text("# committed builder\\n")
            output = Path(tmp) / "artifacts"
            output.mkdir()

            def fake_run(command, cwd, timeout):
                if "--output" in command:
                    destination = Path(command[command.index("--output") + 1])
                    destination.mkdir()
                    write_factory_receipt(destination, wrong_request=True)

            with patch.object(PackageBuilder, "_run", side_effect=fake_run):
                with self.assertRaisesRegex(ConflictError, "pinned APP job"):
                    PackageBuilder()._build_windows(
                        source, Job.validate(job(), config()), output)

    def test_factory_builder_rejects_unexpected_receipt_directory_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            write_factory_receipt(target)
            (target / "extra.txt").write_text("unexpected")
            with self.assertRaisesRegex(HoldError, "evidence is incomplete"):
                PackageBuilder._verify_factory_exe_receipt(Job.validate(job(), config()), target)

    def test_factory_builder_rejects_receipt_sha_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            (source / "tools").mkdir(parents=True)
            (source / "tools/build_windows_exe.py").write_text("# committed builder\n")
            output = Path(tmp) / "artifacts"
            output.mkdir()

            def fake_run(command, cwd, timeout):
                if "--output" in command:
                    destination = Path(command[command.index("--output") + 1])
                    destination.mkdir()
                    write_factory_receipt(destination, corrupt_sha=True)

            with patch.object(PackageBuilder, "_run", side_effect=fake_run):
                with self.assertRaisesRegex(ConflictError, "SHA-256 mismatch"):
                    PackageBuilder()._build_windows(
                        source, Job.validate(job(), config()), output)

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


if __name__ == "__main__":
    unittest.main()
