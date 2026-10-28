"""Fail-closed regression for stale cohort dispatch and Identity routing."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.app_cohort_dispatch import FILES, ROOT, build_dispatch
from tools.app_registration_contract import RegistrationContractError


class CurrentAppCohortDispatchTests(unittest.TestCase):
    def test_five_latest_improvement_revisions_not_old_source(self):
        result = build_dispatch()
        self.assertEqual(result["product_count"], 5)
        self.assertEqual(result["pre_identity_cloud_ready_count"], 5)
        self.assertFalse(result["factory_stable"])
        self.assertTrue(result["no_partner_center_mutation"])
        self.assertEqual(result["next_partner_center_new_product"], "focus-session-desk")
        self.assertEqual([r["slug"] for r in result["products"]],
                         [r[0] for r in FILES])
        rotation = json.loads((ROOT / "docs/APP_COHORT_ROTATION.json").read_text(encoding="utf-8"))
        for output, row in zip(result["products"], rotation["products"]):
            self.assertEqual(output["source_sha"], row["improvement_revision"]["source_sha"])
            self.assertEqual(output["request_id"], row["improvement_revision"]["request_id"])
            self.assertEqual(output["partner_center_selection"], "MSIX or PWA app")
            self.assertFalse(output["post_identity_ready"])
            self.assertFalse(output["msix_built"])
            self.assertFalse(output["windows_gui_pass"])
            self.assertIsNone(output["partner_center_display_name"])
        self.assertEqual(result["products"][0]["identity_status"], "REFERENCE_AVAILABLE")
        self.assertEqual(result["products"][0]["required_fields"], [])
        self.assertTrue(all(p["identity_status"] == "WAITING_USER_IDENTITY"
                            for p in result["products"][1:]))

    def test_old_frozen_source_cannot_be_dispatched(self):
        original = json.loads((ROOT / "docs/APP_COHORT_ROTATION.json").read_text(encoding="utf-8"))
        changed = copy.deepcopy(original)
        changed["products"][0]["improvement_revision"]["source_sha"] = (
            changed["products"][0]["source_sha"]
        )
        with patch("tools.app_cohort_dispatch.load_json",
                   side_effect=lambda path: changed if path.name == "APP_COHORT_ROTATION.json"
                   else json.loads((ROOT / "docs" / path.name).read_text(encoding="utf-8"))):
            with self.assertRaisesRegex(RegistrationContractError, "stale rotation source_sha"):
                build_dispatch()

    def test_missing_current_revision_fails_closed(self):
        original = json.loads((ROOT / "docs/APP_COHORT_ROTATION.json").read_text(encoding="utf-8"))
        changed = copy.deepcopy(original)
        del changed["products"][1]["improvement_revision"]
        with patch("tools.app_cohort_dispatch.load_json",
                   side_effect=lambda path: changed if path.name == "APP_COHORT_ROTATION.json"
                   else json.loads((ROOT / "docs" / path.name).read_text(encoding="utf-8"))):
            with self.assertRaisesRegex(RegistrationContractError, "missing current revision"):
                build_dispatch()

    def test_unattested_identity_cannot_be_promoted_to_cas(self):
        notes_path = "APP_NOTES_IMPROVEMENT_REGISTRATION_REQUEST.json"
        original = json.loads((ROOT / "docs" / notes_path).read_text(encoding="utf-8"))
        changed = {**original, "identity_cas_allowed": True}
        with patch("tools.app_cohort_dispatch.load_json",
                   side_effect=lambda path: changed if path.name == notes_path
                   else json.loads((ROOT / "docs" / path.name).read_text(encoding="utf-8"))):
            with self.assertRaisesRegex(RegistrationContractError, "identity_cas_allowed"):
                build_dispatch()


if __name__ == "__main__":
    unittest.main()
