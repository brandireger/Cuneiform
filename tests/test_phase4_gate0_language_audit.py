import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import phase4_gate0_language_audit as audit  # noqa: E402


class TestPhase4Gate0LanguageAudit(unittest.TestCase):
    def test_valid_word_language_overrides_line_default(self):
        root = ET.fromstring(
            b"<AO><text xml:lang='Hit'>"
            b"<lb lg='Hit'/><w>nu</w><w lg='Hur'>ki-pi-ni</w>"
            b"</text></AO>"
        )
        result = audit.inspect_root(root)
        self.assertEqual(result["valid_word_overrides"][("Hit", "Hur")], 1)
        self.assertTrue(result["document_changed"])

    def test_explicit_empty_is_distinct_from_absence(self):
        root = ET.fromstring(
            b"<AO><text><lb lg='Hit'/><w>nu</w><w lg=''>wa</w></text></AO>"
        )
        result = audit.inspect_root(root)
        self.assertEqual(result["word_values"][""], 1)
        self.assertNotIn("<ABSENT>", result["word_values"])
        self.assertEqual(audit.canonicalize(""), (None, "explicit_empty"))
        self.assertEqual(audit.canonicalize(None), (None, "absent"))

    def test_hattian_mapping_is_explicit(self):
        self.assertEqual(audit.canonicalize("Hattian"), ("Hat", "valid_mapped"))

    def test_unknown_word_language_is_not_guessed(self):
        self.assertEqual(
            audit.canonicalize("Lin"), (None, "unrecognized_or_malformed")
        )


if __name__ == "__main__":
    unittest.main()
