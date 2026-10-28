"""Fifth APP cohort: immutable registration, identity safety and 5/5 cloud contract."""
import json
from pathlib import Path
import unittest
from tools.app_registration_contract import registration_request, RegistrationContractError
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/"docs"/name).read_text(encoding="utf-8"))
class ImageInventoryContractTests(unittest.TestCase):
    def setUp(self):
        self.job=read("APP_IMAGE_INVENTORY_PACKAGE_JOB.json")
        self.receipt=read("APP_IMAGE_INVENTORY_EXE_RECEIPT.json")
        self.request=read("APP_COHORT_IMAGE_INVENTORY_REGISTRATION_REQUEST.json")
        self.cohort=read("APP_COHORT_ROTATION.json")
    def test_real_registration_matches_job_and_receipt(self):
        actual=registration_request(self.job,self.receipt)
        for key in ("slug","source_sha","request_id","partner_center_registration_type"):
            self.assertEqual(actual[key],self.request[key])
        self.assertEqual(actual["partner_center_selection"],"MSIX or PWA app")
        self.assertEqual(actual["identity_status"],"WAITING_USER_IDENTITY")
    def test_unsigned_exe_correlated(self):
        self.assertEqual(self.receipt["executable_sha256"],self.request["pre_identity_exe"]["sha256"])
        self.assertEqual(self.receipt["executable_bytes"],self.request["pre_identity_exe"]["bytes"])
        self.assertEqual(self.receipt["source_sha"],self.request["identity_return_target"]["source_sha"])
        self.assertEqual(self.receipt["request_id"],self.request["identity_return_target"]["request_id"])
    def test_identity_not_invented_or_cas(self):
        self.assertIsNone(self.request["store_id"])
        self.assertIsNone(self.request["partner_center_display_name"])
        self.assertFalse(self.request["identity_cas_allowed"])
        self.assertFalse(self.request["reserved_display_name_verified"])
        self.assertEqual(len(self.request["required_fields"]),7)
        self.assertEqual(self.request["identity_return_target"]["owner"],"36_MIN_WINDOWS_E2E")
    def test_tampered_source_rejected(self):
        with self.assertRaises(RegistrationContractError):
            registration_request(self.job,{**self.receipt,"source_sha":"f"*40})
    def test_identity_in_unsigned_exe_rejected(self):
        with self.assertRaises(RegistrationContractError):
            registration_request(self.job,{**self.receipt,"store_id":"9MZ8ZZTRTS17"})
    def test_five_distinct_ready_products(self):
        products=self.cohort["products"]
        self.assertEqual(len(products),5)
        self.assertEqual(len({p["slug"] for p in products}),5)
        self.assertEqual(len({p["source_sha"] for p in products}),5)
        self.assertEqual(len({p["request_id"] for p in products}),5)
        self.assertTrue(all(p["status"]=="PRE_IDENTITY_READY_CLOUD_CONTRACT" for p in products))
        self.assertTrue(all(p["partner_center_registration_type"]=="MSIX_OR_PWA_APP" for p in products))
        self.assertEqual(self.cohort["metrics"]["pre_identity_ready_count"],5)
        self.assertFalse(self.cohort["new_product_generation_allowed"])
    def test_stability_and_gui_not_overclaimed(self):
        self.assertFalse(self.cohort["factory_stable"])
        self.assertTrue(all(p["windows_gui"]=="UNVERIFIED" and p["e2e"]=="NOT_PASSED" for p in self.cohort["products"]))
        self.assertIsNone(self.cohort["metrics"]["manual_interventions_total"])
        self.assertTrue(self.cohort["metrics"]["unknown_metrics_not_zero"])
if __name__=="__main__":unittest.main()
