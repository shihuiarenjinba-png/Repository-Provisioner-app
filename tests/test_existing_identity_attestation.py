"""Regression tests: existing approved Identity must retain its original attestation."""
import base64
import json
from pathlib import Path
import unittest

from package_identity_provisioner import ConflictError, GitHubReturnClient, Job, ProductConfig


CONFIG = ProductConfig.load(Path(__file__).resolve().parents[1] / "config.json")
SHA = "a" * 40


def sample_job():
    return Job.validate({
        "schema_version": "1.0", "request_id": "identity-replay-0001",
        "product_type": CONFIG.product_type,
        "source_factory": CONFIG.source_factory,
        "source_repository": CONFIG.source_repository,
        "source_branch": CONFIG.source_branch,
        "source_sha": SHA, "slug": "sample-product",
        "display_name": "Sample Product", "target_owner": CONFIG.target_owner,
        "dry_run": False, "requested_actions": [
            "BUILD_WINDOWS", "INSPECT_PACKAGE",
            "LOOKUP_OFFICIAL_IDENTITY", "PROPOSE_GITHUB_RETURN",
        ],
    }, CONFIG)


def official_record():
    return {
        "store_id": "9N1234567890", "name": "Sample.Product",
        "publisher": "CN=Test Publisher", "version": "1.2.3.4",
        "authenticated_account": "verified-operator",
        "official_evidence_url": "https://partner.microsoft.com/dashboard/products/123",
    }


def package_record():
    return {"kind": "msix", "sha256": "f" * 64, "size_bytes": 2048}


def approved_record():
    official = official_record()
    job = sample_job()
    return {
        "reviewed": True, "source": "partner_center",
        **{key: official[key] for key in ("store_id", "name", "publisher", "version")},
        "verified_by": official["authenticated_account"],
        "evidence_url": official["official_evidence_url"],
        "request_id": job.request_id, "product_type": job.product_type,
        "source_factory": job.source_factory, "source_repository": job.source_repository,
        "source_branch": job.source_branch, "source_sha": job.source_sha,
        "expected_head_sha": job.source_sha, "slug": job.slug,
        "display_name": job.display_name, "package_kind": package_record()["kind"],
        "package_sha256": package_record()["sha256"],
        "package_bytes": package_record()["size_bytes"],
    }


class ExistingIdentityAttestationTests(unittest.TestCase):
    def client(self, existing_record):
        def api(endpoint, body=None, allow_missing=False):
            if "git/ref/heads/" in endpoint:
                return {"object": {"sha": SHA}}
            if "/manifest.json" in endpoint:
                manifest = {"slug": "sample-product", "kind": "app"}
                return {"encoding": "base64",
                        "content": base64.b64encode(json.dumps(manifest).encode()).decode()}
            if "/approved-identity.json" in endpoint:
                return {"sha": "b" * 40, "encoding": "base64",
                        "content": base64.b64encode(json.dumps(existing_record).encode()).decode()}
            raise AssertionError("unexpected GitHub API call: " + endpoint)
        return GitHubReturnClient(api)

    def test_complete_matching_attestation_is_verified_without_new_commit(self):
        result = self.client(approved_record()).return_identity(
            sample_job(), CONFIG, official_record(), apply=True, package=package_record())
        self.assertEqual(result["status"], "EXISTING_VERIFIED")
        # GitHub Contents API sha is a *blob*, not a commit SHA.
        self.assertEqual(result["commit_sha"], SHA)
        self.assertNotEqual(result["commit_sha"], "b" * 40)

    def test_unreviewed_identity_with_matching_store_fields_is_conflict(self):
        record = approved_record()
        record["reviewed"] = False
        with self.assertRaises(ConflictError):
            self.client(record).return_identity(sample_job(), CONFIG, official_record(), True, package=package_record())

    def test_wrong_partner_center_evidence_is_conflict(self):
        record = approved_record()
        record["evidence_url"] = "https://partner.microsoft.com/dashboard/products/other"
        with self.assertRaises(ConflictError):
            self.client(record).return_identity(sample_job(), CONFIG, official_record(), True, package=package_record())

    def test_different_operator_is_conflict(self):
        record = approved_record()
        record["verified_by"] = "different-operator"
        with self.assertRaises(ConflictError):
            self.client(record).return_identity(sample_job(), CONFIG, official_record(), True, package=package_record())

    def test_missing_source_is_conflict(self):
        record = approved_record()
        record.pop("source")
        with self.assertRaises(ConflictError):
            self.client(record).return_identity(sample_job(), CONFIG, official_record(), True, package=package_record())


if __name__ == "__main__":
    unittest.main()
