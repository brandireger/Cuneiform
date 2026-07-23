"""Cleanroom and classification tests for the P2-B materiality probe."""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2b_materiality_inventory as p2b


class TestP2BMaterialityInventory(unittest.TestCase):
    def test_test_xml_is_skipped_before_parse(self):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
            path = Path(handle.name)
        try:
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("CTH 1_XML/test-doc.xml", b"invalid XML")
                archive.writestr(
                    "CTH 1_XML/dev-doc.xml",
                    b"<AOxml><body><text><lb lnr='1'/></text></body></AOxml>",
                )
            result = p2b.scan_non_test_schema(
                path,
                {"test-doc": "test", "dev-doc": "dev"},
                set(),
            )
        finally:
            path.unlink()

        self.assertEqual(result["status"]["test_skipped_before_read"], 1)
        self.assertEqual(result["status"]["allowed_parsed"], 1)
        self.assertEqual(result["status"].get("allowed_parse_error", 0), 0)
        self.assertEqual(result["tag_documents"]["lb"], 1)

    def test_ambiguous_and_unmatched_entries_are_not_read(self):
        self.assertEqual(
            p2b.archive_access_status(
                "x/ambiguous.xml", {}, {"ambiguous"}),
            "ambiguous_stem_skipped",
        )
        self.assertEqual(
            p2b.archive_access_status("x/unknown.xml", {}, set()),
            "unmatched_stem_skipped",
        )

    def test_media_extension_allowlist(self):
        self.assertIn(".png", p2b.DIRECT_MEDIA_EXTENSIONS)
        self.assertIn(".ply", p2b.DIRECT_MEDIA_EXTENSIONS)
        self.assertNotIn(".xml", p2b.DIRECT_MEDIA_EXTENSIONS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
