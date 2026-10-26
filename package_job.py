"""Strict, offline APP Factory -> local package/Identity intake contract.

Validation is intentionally read-only: it does not call GitHub, build an app,
query Partner Center, register a product, or write approved-identity.json.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from urllib.parse import quote
from urllib.request import Request, HTTPRedirectHandler, build_opener
from pathlib import Path
import re
import sys

SCHEMA_VERSION = "1.0"
OWNER = "shihuiarenjinba-png"
FACTORY = "AI-App-Factory"
REPOSITORY = OWNER + "/" + FACTORY
BRANCH = "codex/factory-autoloop-20261026"
ACTIONS = (
    "BUILD_WINDOWS",
    "INSPECT_PACKAGE",
    "LOOKUP_OFFICIAL_IDENTITY",
    "PROPOSE_GITHUB_RETURN",
)
FIELDS = frozenset({
    "schema_version", "request_id", "product_type", "source_factory",
    "source_repository", "source_branch", "source_sha", "slug",
    "display_name", "target_owner", "dry_run", "requested_actions",
})
SLUG = re.compile(r"^[a-z][a-z0-9-]{3,39}$")
REQUEST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def validate_job(record: dict) -> dict:
    """Return a safe DRY_RUN receipt, never an authorization to build/write."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise ValueError("unexpected or missing job fields")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")
    if record["product_type"] != "APP":
        raise ValueError("wrong product_type for APP lane")
    if record["source_factory"] != FACTORY:
        raise ValueError("wrong source_factory for APP lane")
    if record["source_repository"] != REPOSITORY:
        raise ValueError("untrusted source_repository")
    if record["source_branch"] != BRANCH:
        raise ValueError("unapproved source_branch")
    if record["target_owner"] != OWNER:
        raise ValueError("unapproved target_owner")
    if record["dry_run"] is not True:
        raise ValueError("live execution not implemented or authorized")
    rid = record["request_id"]
    if not isinstance(rid, str) or not REQUEST.fullmatch(rid):
        raise ValueError("unsafe request_id")
    slug = record["slug"]
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ValueError("unsafe product slug")
    sha = record["source_sha"]
    if not isinstance(sha, str) or not SHA40.fullmatch(sha) or sha == "0" * 40:
        raise ValueError("exact non-placeholder Git commit SHA required")
    display = record["display_name"]
    if (not isinstance(display, str) or not 1 <= len(display) <= 100
            or display.strip() != display
            or any(ord(c) < 32 or ord(c) == 127 for c in display)):
        raise ValueError("invalid display_name")
    actions = record["requested_actions"]
    if (not isinstance(actions, list) or len(actions) != len(ACTIONS)
            or set(map(str, actions)) != set(ACTIONS)
            or any(not isinstance(x, str) for x in actions)):
        raise ValueError("unsupported requested_actions")
    # Bind the future idempotency key to the *entire* validated request.
    # A changed display name or action set must never reuse a prior job.
    # Action order is not semantically significant.
    canonical = dict(record)
    canonical["requested_actions"] = sorted(actions)
    material = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    key = sha256(b"APP_PACKAGE_JOB_V1\x00" + material.encode("ascii")).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": rid,
        "product_type": "APP",
        "status": "DRY_RUN",
        "idempotency_key": key,
        "source_repository": REPOSITORY,
        "source_branch": BRANCH,
        "source_sha": sha,
        "expected_head_sha": None,
        "source_head_verification": "NOT_CHECKED",
        "package": {
            "status": "NOT_BUILT", "sha256": None,
            "artifact_url": None, "package_identity": None,
        },
        "official_identity": {
            "status": "UNVERIFIED", "store_id": None, "name": None,
            "publisher": None, "version": None, "official_evidence_url": None,
        },
        "github_return": {
            "status": "NOT_APPLIED",
            "repository": REPOSITORY, "branch": BRANCH,
            "path": "products/" + slug + "/store/approved-identity.json",
            "commit_sha": None,
        },
        "errors": [],
        "next_stage": "VERIFY_LIVE_GITHUB_HEAD_AND_LOCAL_BUILD",
        "note": (
            "Read-only contract check only. Authenticated HEAD verification, "
            "durable idempotency ledger, Windows build, Partner Center evidence, "
            "and atomic GitHub identity return are NOT performed."
        ),
    }



class _NoRedirect(HTTPRedirectHandler):
    """Never forward a bearer token to a redirected URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_github_head(record: dict, *, token=None, opener=None) -> str:
    """Authenticated, read-only exact branch HEAD check; never trust job SHA alone.

    This check does not authorize package execution or Identity writes. A later
    mutating step must check HEAD again immediately before its own operation.
    """
    if (record.get("source_repository") != REPOSITORY
            or record.get("source_branch") != BRANCH
            or not isinstance(record.get("source_sha"), str)
            or not SHA40.fullmatch(record["source_sha"])):
        raise ValueError("untrusted source for GitHub HEAD verification")
    if token is None:
        token = os.environ.get("GITHUB_TOKEN")
    if (not isinstance(token, str) or not token or token != token.strip()
            or "\r" in token or "\n" in token):
        raise ValueError("authenticated GitHub token required")
    url = ("https://api.github.com/repos/" + REPOSITORY
           + "/branches/" + quote(BRANCH, safe=""))
    req = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "app-provisioner-head-check/1.0",
    })
    if opener is None:
        opener = build_opener(_NoRedirect()).open
    with opener(req, timeout=10) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("unexpected GitHub response or redirect")
        payload = response.read(65537)
    if len(payload) > 65536:
        raise ValueError("GitHub response exceeds limit")
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid GitHub HEAD response") from exc
    if not isinstance(body, dict) or not isinstance(body.get("commit"), dict):
        raise ValueError("missing GitHub branch commit")
    head = body["commit"].get("sha")
    if not isinstance(head, str) or not SHA40.fullmatch(head):
        raise ValueError("invalid GitHub branch SHA")
    if head != record["source_sha"]:
        raise ValueError("source SHA differs from current GitHub branch HEAD")
    return head


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-head", action="store_true",
                        help="Require authenticated read-only GitHub branch HEAD match")
    args = parser.parse_args(argv)
    try:
        if args.input.stat().st_size > 32768:
            raise ValueError("job JSON too large")
        data = json.loads(args.input.read_text(encoding="utf-8"),
                          object_pairs_hook=_reject_duplicates)
        receipt = validate_job(data)
        if args.verify_head:
            receipt["expected_head_sha"] = verify_github_head(data)
            receipt["source_head_verification"] = "VERIFIED"
            receipt["next_stage"] = "LOCAL_WINDOWS_BUILD_NOT_IMPLEMENTED"
            receipt["note"] = ("GitHub branch HEAD verified at read time only. "
                               "Recheck before mutation. Windows build, Partner Center "
                               "lookup, durable ledger, and Identity return NOT performed.")
        encoded = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            if args.output.is_symlink():
                raise ValueError("symlink output forbidden")
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("PACKAGE_INTAKE_HOLD: " + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
