"""Regression: a retry must never hand off an unchanged artifact from an earlier build."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from package_identity_provisioner import HoldError, PackageBuilder, ProductConfig

CONFIG = ProductConfig.load(Path(__file__).resolve().parents[1] / "config.json")


class BuildArtifactFreshnessTests(unittest.TestCase):
    def test_stale_output_does_not_count_as_success(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            output = Path(temp) / "artifacts"
            source.mkdir()
            output.mkdir()
            (output / "candidate.msix").write_bytes(b"previous-build")
            with patch.object(PackageBuilder, "_build_windows", return_value=None):
                with self.assertRaisesRegex(HoldError, "without a configured"):
                    PackageBuilder().build(None, source, output, CONFIG)

    def test_new_output_is_selected_over_stale_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            output = Path(temp) / "artifacts"
            source.mkdir()
            output.mkdir()
            (output / "old.msix").write_bytes(b"previous-build")
            fresh = output / "fresh.msix"

            def produce(_source, _job, _output_dir):
                fresh.write_bytes(b"current-build")

            with patch.object(PackageBuilder, "_build_windows", side_effect=produce):
                selected = PackageBuilder().build(None, source, output, CONFIG)
            self.assertEqual(selected, fresh.resolve())

    def test_rewritten_output_can_be_selected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            output = Path(temp) / "artifacts"
            source.mkdir()
            output.mkdir()
            candidate = output / "candidate.msix"
            candidate.write_bytes(b"old")

            def produce(_source, _job, _output_dir):
                candidate.write_bytes(b"new-content-longer")

            with patch.object(PackageBuilder, "_build_windows", side_effect=produce):
                selected = PackageBuilder().build(None, source, output, CONFIG)
            self.assertEqual(selected, candidate.resolve())


if __name__ == "__main__":
    unittest.main()
