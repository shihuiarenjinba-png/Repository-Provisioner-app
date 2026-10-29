"""Offline regressions for the authenticated five-artifact APP gate."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.app_cohort_dispatch import build_dispatch
from tools.app_cohort_github_gate import (
    REPO, fetch_and_verify, parse_location, validate_metadata,
    validate_workflow_run,
)
from tools.app_registration_contract import RegistrationContractError


def metadata_for(row):
    run_id, artifact_id = parse_location(row)
    api = f"https://api.github.com/repos/{REPO}/actions/artifacts/{artifact_id}"
    return {
        "id": artifact_id, "expired": False, "size_in_bytes": 10000,
        "digest": "sha256:" + row["artifact_zip_sha256"],
        "url": api, "archive_download_url": api + "/zip",
        "workflow_run": {"id": run_id, "head_branch": row["source_branch"],
                         # Workflow HEAD is not necessarily promoted source SHA.
                         "head_sha": "f" * 40},
    }

def run_for(row):
    run_id, _ = parse_location(row)
    return {
        "id": run_id, "status": "completed", "conclusion": "success",
        "head_branch": row["source_branch"],
        "head_sha": "f" * 40,
        "repository": {"full_name": REPO},
        "html_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
    }


class AuthenticatedArtifactGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = build_dispatch()["products"]

    def test_all_five_pinned_metadata_contracts(self):
        for row in self.rows:
            with self.subTest(slug=row["slug"]):
                self.assertEqual(validate_metadata(row, metadata_for(row)),
                                 parse_location(row))


    def test_rejects_failed_or_wrong_workflow_run(self):
        row = self.rows[0]
        validate_workflow_run(row, run_for(row))
        for field, value in (
            ("conclusion", "failure"), ("conclusion", None),
            ("status", "in_progress"), ("id", 999),
            ("head_branch", "other"), ("head_sha", "not-a-sha"),
            ("html_url", "https://example.com/run"),
        ):
            bad = run_for(row)
            bad[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(
                RegistrationContractError
            ):
                validate_workflow_run(row, bad)
        bad = run_for(row)
        bad["repository"] = {"full_name": "another/repo"}
        with self.assertRaisesRegex(RegistrationContractError, "repository mismatch"):
            validate_workflow_run(row, bad)

    def test_rejects_metadata_digest_mismatch(self):
        row = self.rows[0]
        bad = metadata_for(row)
        bad["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(RegistrationContractError, "digest mismatch"):
            validate_metadata(row, bad)

    def test_rejects_wrong_run_or_branch(self):
        row = self.rows[1]
        for field, value in (("id", 999), ("expired", True),
                             ("size_in_bytes", 0)):
            bad = metadata_for(row)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(RegistrationContractError):
                validate_metadata(row, bad)
        for field in ("id", "head_branch"):
            bad = metadata_for(row)
            bad["workflow_run"][field] = "other"
            with self.subTest(field=field), self.assertRaises(RegistrationContractError):
                validate_metadata(row, bad)

    def test_rejects_untrusted_api_url_and_artifact_url(self):
        row = self.rows[2]
        bad = metadata_for(row)
        bad["archive_download_url"] = "https://example.com/zip"
        with self.assertRaisesRegex(RegistrationContractError, "API URL mismatch"):
            validate_metadata(row, bad)
        bad_row = dict(row, artifact_url="https://example.com/123")
        with self.assertRaisesRegex(RegistrationContractError, "untrusted artifact URL"):
            parse_location(bad_row)

    def test_five_downloads_pass_only_after_binary_gate(self):
        calls = []
        def fake_api(endpoint, destination=None):
            if destination is not None:
                Path(destination).write_bytes(b"mock ZIP bytes")
                calls.append(("download", endpoint))
                return None
            if "/actions/runs/" in endpoint:
                run_id = int(endpoint.rsplit("/", 1)[-1])
                row = next(row for row in self.rows
                           if parse_location(row)[0] == run_id)
                calls.append(("run", endpoint))
                return run_for(row)
            artifact_id = int(endpoint.rsplit("/", 1)[-1])
            row = next(row for row in self.rows
                       if parse_location(row)[1] == artifact_id)
            calls.append(("metadata", endpoint))
            return metadata_for(row)

        def fake_verify(dispatch, paths):
            self.assertEqual(set(paths), {r["slug"] for r in self.rows})
            self.assertTrue(all(Path(path).exists() for path in paths.values()))
            dispatch["binary_verified_count"] = 5
            dispatch["downstream_binary_gate_pass"] = True
            return dispatch

        with patch.dict(os.environ, {"GH_TOKEN": "test-token"}, clear=True), \
             patch("tools.app_cohort_github_gate.shutil.which", return_value="/usr/bin/gh"), \
             patch("tools.app_cohort_github_gate._gh_api", side_effect=fake_api), \
             patch("tools.app_cohort_github_gate.verify_binary_dispatch",
                   side_effect=fake_verify):
            result = fetch_and_verify()
        self.assertEqual(len(calls), 15)
        self.assertEqual(sum(kind == "run" for kind, _ in calls), 5)
        self.assertTrue(all(
            proof["producing_workflow_run_completed_successfully"]
            for proof in result["actions_artifact_metadata_checks"]
        ))
        self.assertEqual(result["binary_verified_count"], 5)
        self.assertIn("NO_SIGNED_ATTESTATION", result["verification_scope"])
        self.assertFalse(result["identity_cas_allowed"])
        self.assertFalse(result["factory_stable"])

    def test_missing_token_fails_before_network(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("tools.app_cohort_github_gate._gh_api") as api:
            with self.assertRaisesRegex(RegistrationContractError, "TOKEN required"):
                fetch_and_verify()
            api.assert_not_called()

    def test_invalid_first_metadata_stops_before_download(self):
        def fake_api(endpoint, destination=None):
            if destination is not None:
                self.fail("download must not start after invalid metadata")
            bad = metadata_for(self.rows[0])
            bad["digest"] = "sha256:" + "0" * 64
            return bad
        with patch.dict(os.environ, {"GH_TOKEN": "test-token"}, clear=True), \
             patch("tools.app_cohort_github_gate.shutil.which", return_value="/usr/bin/gh"), \
             patch("tools.app_cohort_github_gate._gh_api", side_effect=fake_api):
            with self.assertRaisesRegex(RegistrationContractError, "digest mismatch"):
                fetch_and_verify()


if __name__ == "__main__":
    unittest.main()
