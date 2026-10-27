"""APP EXE -> authenticated Identity CAS contract, without rebuilding the EXE.

All Partner Center values and GitHub commits in this test are local fakes.
"""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from package_identity_provisioner import (
    GitHubReturnClient, HoldError, Job, Provisioner,
)
from test_package_identity_pipeline import (
    FakeGitHub, FakeIdentity, FakeSource, config, evidence, job,
)


class ReceiptBuilder:
    def __init__(self):
        self.calls = 0
        self.exe = None

    def build(self, request, source, output_dir, _config):
        self.calls += 1
        directory = output_dir / "preidentity-verified"
        directory.mkdir(parents=True, exist_ok=True)
        self.exe = directory / (request.slug + ".exe")
        self.exe.write_bytes(b"MZ" + b"real-test-payload" * 100)
        data = self.exe.read_bytes()
        receipt = {
            "schema_version": 1, "stage": "PRE_IDENTITY_WINDOWS_EXE",
            "status": "EXE_QA_UNSIGNED", "request_id": request.request_id,
            "product_type": request.product_type, "source_factory": request.source_factory,
            "source_repository": request.source_repository,
            "source_branch": request.source_branch, "source_sha": request.source_sha,
            "slug": request.slug, "display_name": request.display_name,
            "executable": self.exe.name, "official_identity_status": "NOT_COLLECTED",
            "store_id": None, "msix_status": "NOT_BUILT",
            "executable_sha256": hashlib.sha256(data).hexdigest(),
            "executable_bytes": len(data),
        }
        (directory / "exe-receipt.json").write_text(
            json.dumps(receipt), encoding="utf-8")
        return self.exe


class AppExeIdentityResumeTests(unittest.TestCase):
    def make_runner(self, root, builder, identity, github):
        return Provisioner(config(), Path(root) / "state", Path(root) / "work",
                           source=FakeSource(), builder=builder,
                           identity=identity, github=github)

    def test_missing_partner_center_identity_keeps_exe_and_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            builder, github = ReceiptBuilder(), FakeGitHub()
            runner = self.make_runner(
                tmp, builder, FakeIdentity(error=HoldError("No authenticated evidence")), github)
            result = runner.run(job(), apply=True)
            self.assertEqual(result["status"], "HOLD")
            self.assertEqual(result["next_stage"], "OBTAIN_AUTHENTICATED_OFFICIAL_IDENTITY")
            self.assertEqual(result["package"]["kind"], "exe")
            self.assertIsNone(result["windows_all_auto_record"])
            self.assertEqual(github.calls, 0)

    def test_same_exe_reused_through_verified_identity_and_cas(self):
        with tempfile.TemporaryDirectory() as tmp:
            builder, github = ReceiptBuilder(), FakeGitHub()
            runner = self.make_runner(
                tmp, builder, FakeIdentity(error=HoldError("Identity pending")), github)
            first = runner.run(job(), apply=True)
            pinned = first["package"]["sha256"]
            runner.identity = FakeIdentity()
            second = runner.run(job(), apply=False)
            self.assertEqual(second["status"], "HOLD")
            self.assertEqual(second["next_stage"], "APPLY_VERIFIED_GITHUB_RETURN")
            self.assertEqual(second["package"]["sha256"], pinned)
            third = runner.run(job(), apply=True)
            self.assertEqual(third["status"], "COMPLETED")
            self.assertEqual(third["next_stage"], "BUILD_MSIX_FROM_PINNED_EXE")
            self.assertEqual(third["package"]["sha256"], pinned)
            self.assertIsNone(third["windows_all_auto_record"])
            self.assertEqual(third["github_return"]["commit_sha"], "b" * 40)
            self.assertEqual(builder.calls, 1)

    def test_modified_exe_is_conflict_and_never_rebuilt(self):
        with tempfile.TemporaryDirectory() as tmp:
            builder, github = ReceiptBuilder(), FakeGitHub()
            runner = self.make_runner(
                tmp, builder, FakeIdentity(error=HoldError("Identity pending")), github)
            self.assertEqual(runner.run(job())["status"], "HOLD")
            builder.exe.write_bytes(builder.exe.read_bytes() + b"changed")
            runner.identity = FakeIdentity()
            result = runner.run(job(), apply=True)
            self.assertEqual(result["status"], "CONFLICT")
            self.assertEqual(builder.calls, 1)
            self.assertEqual(github.calls, 0)

    def test_receipt_missing_refuses_identity_return(self):
        class NoReceiptBuilder(ReceiptBuilder):
            def build(self, *args):
                exe = super().build(*args)
                (exe.parent / "exe-receipt.json").unlink()
                return exe
        with tempfile.TemporaryDirectory() as tmp:
            github = FakeGitHub()
            result = self.make_runner(
                tmp, NoReceiptBuilder(), FakeIdentity(), github).run(job(), apply=True)
            self.assertEqual(result["status"], "HOLD")
            self.assertEqual(github.calls, 0)

    def test_cas_approved_identity_has_exact_exe_contract(self):
        requests = []
        def api(endpoint, body=None, allow_missing=False):
            if "git/ref/heads/" in endpoint:
                return {"object": {"sha": "a" * 40}}
            if "/manifest.json" in endpoint:
                raw = json.dumps({"slug": "sample-product", "kind": "app"}).encode()
                return {"encoding": "base64", "content": base64.b64encode(raw).decode()}
            if "/approved-identity.json" in endpoint:
                return None
            if endpoint == "graphql":
                requests.append(body)
                return {"data": {"createCommitOnBranch": {"commit": {
                    "oid": "b" * 40, "url": "https://github.invalid/commit"}}}}
            raise AssertionError(endpoint)
        request = Job.validate(job(), config())
        package = {"kind": "exe", "sha256": "d" * 64,
                   "size_bytes": 12345, "signature_status": "NOTSIGNED"}
        result = GitHubReturnClient(api).return_identity(
            request, config(), evidence(), package, apply=True)
        self.assertEqual(result["status"], "APPLIED")
        mutation = requests[0]["variables"]["input"]
        self.assertEqual(mutation["expectedHeadOid"], request.source_sha)
        addition = mutation["fileChanges"]["additions"][0]
        approved = json.loads(base64.b64decode(addition["contents"]))
        for key, expected in {
            "request_id": request.request_id, "source_branch": request.source_branch,
            "source_sha": request.source_sha, "expected_head_sha": request.source_sha,
            "display_name": request.display_name, "package_kind": "exe",
            "package_sha256": package["sha256"], "package_bytes": package["size_bytes"],
            "store_id": evidence()["store_id"], "name": evidence()["name"],
            "publisher": evidence()["publisher"], "version": evidence()["version"],
        }.items():
            self.assertEqual(approved[key], expected, key)


if __name__ == "__main__":
    unittest.main()
