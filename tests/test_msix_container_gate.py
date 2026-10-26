"""MSIX container regression: manifest-only ZIPs must never reach Identity approval."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from package_identity_provisioner import HoldError, inspect_package

MANIFEST = (
    '<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10">'
    '<Identity Name="Sample.Product" Publisher="CN=Test Publisher" Version="1.2.3.4" />'
    '</Package>'
)
BLOCKMAP = '<BlockMap xmlns="http://schemas.microsoft.com/appx/2010/blockmap" />'
CONTENT_TYPES = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types" />'


def write_archive(path, entries):
    with zipfile.ZipFile(path, "w") as archive:
        for name, contents in entries:
            archive.writestr(name, contents)
    return path


class MSIXContainerGateTests(unittest.TestCase):
    def test_manifest_only_zip_is_not_an_msix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_archive(Path(directory) / "candidate.msix", [
                ("AppxManifest.xml", MANIFEST), ("payload.txt", "data"),
            ])
            with self.assertRaisesRegex(HoldError, "metadata"):
                inspect_package(path)

    def test_invalid_blockmap_xml_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_archive(Path(directory) / "candidate.msix", [
                ("AppxManifest.xml", MANIFEST),
                ("AppxBlockMap.xml", "<not-closed"),
                ("[Content_Types].xml", CONTENT_TYPES),
            ])
            with self.assertRaises(HoldError):
                inspect_package(path)

    def test_case_insensitive_duplicate_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_archive(Path(directory) / "candidate.msix", [
                ("AppxManifest.xml", MANIFEST),
                ("appxmanifest.xml", MANIFEST),
                ("AppxBlockMap.xml", BLOCKMAP),
                ("[Content_Types].xml", CONTENT_TYPES),
            ])
            with self.assertRaisesRegex(HoldError, "Duplicate"):
                inspect_package(path)

    def test_complete_metadata_passes_structural_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_archive(Path(directory) / "candidate.msix", [
                ("AppxManifest.xml", MANIFEST),
                ("AppxBlockMap.xml", BLOCKMAP),
                ("[Content_Types].xml", CONTENT_TYPES),
                ("payload.txt", "data"),
            ])
            with patch("package_identity_provisioner.signature_status", return_value="INSPECTION_SKIPPED"):
                result = inspect_package(path)
            self.assertEqual(result["package_identity"], "Sample.Product")
            self.assertEqual(result["publisher"], "CN=Test Publisher")
            self.assertEqual(result["version"], "1.2.3.4")
            self.assertEqual(result["status"], "INSPECTED")


if __name__ == "__main__":
    unittest.main()
