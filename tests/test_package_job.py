"""Read-only APP package-intake regression tests."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from package_job import validate_job, verify_github_head

SHA = "a" * 40


def sample():
    return {
        "schema_version": "1.0",
        "request_id": "app-20261026-001",
        "product_type": "APP",
        "source_factory": "AI-App-Factory",
        "source_repository": "shihuiarenjinba-png/AI-App-Factory",
        "source_branch": "codex/factory-autoloop-20261026",
        "source_sha": SHA,
        "slug": "useful-desktop-app",
        "display_name": "Useful Desktop App",
        "target_owner": "shihuiarenjinba-png",
        "dry_run": True,
        "requested_actions": [
            "BUILD_WINDOWS", "INSPECT_PACKAGE",
            "LOOKUP_OFFICIAL_IDENTITY", "PROPOSE_GITHUB_RETURN",
        ],
    }


class IntakeTests(unittest.TestCase):
    def test_safe_receipt_no_claim_of_real_actions(self):
        receipt = validate_job(sample())
        self.assertEqual(receipt["status"], "DRY_RUN")
        self.assertEqual(receipt["package"]["status"], "NOT_BUILT")
        self.assertIsNone(receipt["expected_head_sha"])
        self.assertIsNone(receipt["official_identity"]["store_id"])
        self.assertEqual(receipt["github_return"]["status"], "NOT_APPLIED")
        self.assertEqual(
            receipt["github_return"]["path"],
            "products/useful-desktop-app/store/approved-identity.json",
        )
        self.assertIsNone(receipt["github_return"]["commit_sha"])

    def test_deterministic_receipt(self):
        self.assertEqual(validate_job(sample()), validate_job(sample()))

    def test_idempotency_key_is_source_specific(self):
        a = sample()
        b = copy.deepcopy(a)
        b["source_sha"] = "b" * 40
        self.assertNotEqual(validate_job(a)["idempotency_key"],
                            validate_job(b)["idempotency_key"])

    def test_idempotency_key_binds_all_validated_job_content(self):
        original = sample()
        baseline = validate_job(original)["idempotency_key"]
        for field, value in (
            ("display_name", "Renamed Desktop App"),
            ("request_id", "app-20261026-002"),
            ("slug", "different-desktop-app"),
            ("source_sha", "b" * 40),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed[field] = value
                self.assertNotEqual(
                    baseline, validate_job(changed)["idempotency_key"])
        # The actions are a set: reordering must not create a new job.
        reordered = copy.deepcopy(original)
        reordered["requested_actions"].reverse()
        self.assertEqual(
            baseline, validate_job(reordered)["idempotency_key"])

    def test_factory_strict_job_is_accepted_by_both_consumers(self):
        """The actual Factory one-action contract must pass the intake CLI."""
        from package_identity_provisioner import Job, ProductConfig

        data = sample()
        data.update(
            source_branch="codex/app-preidentity-strict-job-20261030",
            source_sha="dd94bd2cd52a84653623f6ccdf727a6cf7903b98",
            request_id="app-focus-strict-dd94bd2cd52a",
            slug="focus-session-desk",
            display_name="Focus Session Desk — Offline Timer and Task Checklist",
            requested_actions=["BUILD_WINDOWS"],
        )
        receipt = validate_job(data)
        self.assertEqual(receipt["source_branch"], data["source_branch"])
        self.assertEqual(receipt["github_return"]["branch"], data["source_branch"])
        self.assertEqual(receipt["status"], "DRY_RUN")
        self.assertEqual(receipt["package"]["status"], "NOT_BUILT")
        self.assertEqual(receipt["official_identity"]["status"], "UNVERIFIED")
        config = ProductConfig.load(Path(__file__).resolve().parents[1] / "config.json")
        actual = Job.validate(data, config)
        self.assertEqual(actual.source_sha, data["source_sha"])
        self.assertEqual(actual.requested_actions, ("BUILD_WINDOWS",))
        with tempfile.TemporaryDirectory() as temp:
            job_path = Path(temp) / "factory-job.json"
            output_path = Path(temp) / "intake.json"
            job_path.write_text(json.dumps(data), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "package_job.py", "--input", str(job_path),
                 "--output", str(output_path)],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(output_path.read_text()), receipt)

    def test_action_subset_and_branch_are_bound_to_idempotency_key(self):
        data = sample()
        base = validate_job(data)["idempotency_key"]
        data["requested_actions"] = ["BUILD_WINDOWS"]
        self.assertNotEqual(base, validate_job(data)["idempotency_key"])
        subset_key = validate_job(data)["idempotency_key"]
        data["source_branch"] = "codex/other-safe-branch"
        self.assertNotEqual(subset_key, validate_job(data)["idempotency_key"])
        self.assertEqual(validate_job(data)["github_return"]["branch"],
                         "codex/other-safe-branch")

    def test_reject_malformed_and_cross_lane(self):
        changes = [
            ("schema_version", 1),
            ("product_type", "GAME"),
            ("product_type", "GAME_3D"),
            ("source_factory", "AI-Game-Factory"),
            ("source_repository", "shihuiarenjinba-png/AI-Game-Factory"),
            ("source_branch", "main"),
            ("source_branch", "codex/../bad"),
            ("source_branch", "codex/.hidden"),
            ("source_branch", "codex/foo.lock"),
            ("source_branch", "codex//double"),
            ("source_branch", "codex/trailing/"),
            ("source_branch", "codex/unsafe@{1}"),
            ("target_owner", "unapproved-owner"),
            ("dry_run", False),
            ("request_id", "../../secret"),
            ("slug", "../wrong-path"),
            ("slug", "UPPERCASE"),
            ("source_sha", "0" * 40),
            ("source_sha", "a" * 39),
            ("source_sha", "A" * 40),
            ("display_name", ""),
            ("display_name", "hidden\ncommand"),
            ("requested_actions", []),
            ("requested_actions", ["BUILD_WINDOWS", "BUILD_WINDOWS"]),
            ("requested_actions", [
                "BUILD_WINDOWS", "INSPECT_PACKAGE",
                "LOOKUP_OFFICIAL_IDENTITY", "rm -rf /",
            ]),
        ]
        for field, bad in changes:
            with self.subTest(field=field, bad=bad):
                data = sample()
                data[field] = bad
                with self.assertRaises(ValueError):
                    validate_job(data)

    def test_reject_unknown_and_missing_fields(self):
        data = sample()
        data["command"] = "powershell -EncodedCommand ..."
        with self.assertRaises(ValueError):
            validate_job(data)
        data = sample()
        del data["source_sha"]
        with self.assertRaises(ValueError):
            validate_job(data)

    def test_cli_dry_run_and_no_external_side_effect(self):
        with tempfile.TemporaryDirectory() as temp:
            inp = Path(temp) / "job.json"
            out = Path(temp) / "receipt.json"
            inp.write_text(json.dumps(sample()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "package_job.py", "--input", str(inp),
                 "--output", str(out)],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(out.read_text())["status"], "DRY_RUN")
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()),
                             ["job.json", "receipt.json"])

    def test_cli_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            inp = Path(temp) / "job.json"
            out = Path(temp) / "receipt.json"
            inp.write_text(json.dumps(sample()), encoding="utf-8")
            out.write_text("protected", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "package_job.py", "--input", str(inp),
                 "--output", str(out)],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(out.read_text(encoding="utf-8"), "protected")

    def test_cli_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            inp = Path(temp) / "job.json"
            data = json.dumps(sample())
            data = data[:-1] + ', "dry_run": false}'
            inp.write_text(data, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "package_job.py", "--input", str(inp)],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("PACKAGE_INTAKE_HOLD", result.stderr)

    def test_cli_does_not_follow_symlink_output(self):
        with tempfile.TemporaryDirectory() as temp:
            inp = Path(temp) / "job.json"
            target = Path(temp) / "target.json"
            link = Path(temp) / "receipt.json"
            inp.write_text(json.dumps(sample()), encoding="utf-8")
            target.write_text("protected", encoding="utf-8")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            result = subprocess.run(
                [sys.executable, "package_job.py", "--input", str(inp),
                 "--output", str(link)],
                capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_text(), "protected")


    def test_authenticated_github_head_exact_match(self):
        data = sample()
        seen = []
        class Response:
            status = 200
            def __init__(self, url):
                self.url = url
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def geturl(self):
                return self.url
            def read(self, size):
                self_size = json.dumps({"commit": {"sha": SHA}}).encode()
                return self_size[:size]
        def open_mock(req, timeout):
            seen.append((req, timeout))
            return Response(req.full_url)
        self.assertEqual(verify_github_head(data, token="test-secret", opener=open_mock), SHA)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1], 10)
        self.assertIn("/branches/codex%2Ffactory-autoloop-20261026",
                      seen[0][0].full_url)
        self.assertEqual(seen[0][0].get_header("Authorization"), "Bearer test-secret")

    def test_authenticated_github_head_uses_dynamic_exact_branch(self):
        data = sample()
        data["source_branch"] = "codex/app-preidentity-strict-job-20261030"
        observed = []
        class Response:
            status = 200
            def __init__(self, url):
                self.url = url
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def geturl(self):
                return self.url
            def read(self, size):
                return json.dumps({"commit": {"sha": SHA}}).encode()[:size]
        def open_mock(req, timeout):
            observed.append(req.full_url)
            return Response(req.full_url)
        self.assertEqual(verify_github_head(data, token="test-secret", opener=open_mock), SHA)
        self.assertEqual(len(observed), 1)
        self.assertTrue(observed[0].endswith(
            "/branches/codex%2Fapp-preidentity-strict-job-20261030"))

    def test_authenticated_github_head_fail_closed(self):
        data = sample()
        class Response:
            status = 200
            def __init__(self, url, body, redirect=False):
                self.url = url + ("/redirect" if redirect else "")
                self.body = body
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def geturl(self):
                return self.url
            def read(self, size):
                return self.body[:size]
        for body, redirect in [
            (json.dumps({"commit": {"sha": "b" * 40}}).encode(), False),
            (b"not json", False),
            (b'{"commit":{}}', False),
            (b"x" * 65537, False),
            (json.dumps({"commit": {"sha": SHA}}).encode(), True),
        ]:
            with self.subTest(body=body[:20], redirect=redirect):
                with self.assertRaises(ValueError):
                    verify_github_head(
                        data, token="test-secret",
                        opener=lambda req, timeout: Response(req.full_url, body, redirect),
                    )
        with self.assertRaises(ValueError):
            verify_github_head(data, token="", opener=lambda req, timeout: None)
        with self.assertRaises(ValueError):
            verify_github_head(data, token="bad" + chr(10) + "header", opener=lambda req, timeout: None)
        changed = sample()
        changed["source_repository"] = "other/repo"
        with self.assertRaises(ValueError):
            verify_github_head(changed, token="test-secret", opener=lambda req, timeout: None)

    def test_cli_verify_head_requires_auth_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            inp = Path(temp) / "job.json"
            out = Path(temp) / "receipt.json"
            inp.write_text(json.dumps(sample()), encoding="utf-8")
            import os
            env = dict(os.environ)
            env.pop("GITHUB_TOKEN", None)
            result = subprocess.run(
                [sys.executable, "package_job.py", "--input", str(inp),
                 "--output", str(out), "--verify-head"],
                capture_output=True, text=True, timeout=15, env=env,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("PACKAGE_INTAKE_HOLD", result.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
