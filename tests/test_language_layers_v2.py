import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

import language_layers_v2 as llv2  # noqa: E402
import phase4_language_layers_v2 as migration  # noqa: E402
import phase4_multilingual_token_dataset as token_dataset  # noqa: E402


CONTRACT_PATH = ROOT / "configs" / "language_layers_v2.json"


class TestLanguageLayersV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = llv2.load_language_contract(CONTRACT_PATH)

    def classify(self, raw, present=True, level="WORD"):
        return llv2.classify_language(
            raw,
            attribute_present=present,
            level=level,
            contract=self.contract,
        )

    def test_canonicalization_preserves_distinct_source_states(self):
        self.assertEqual(self.classify("Hit").canonical, "Hit")
        mapped = self.classify("Hattian")
        self.assertEqual((mapped.status, mapped.canonical), ("valid", "Hat"))
        self.assertEqual(
            self.classify("", level="WORD").status, "explicit_empty")
        self.assertEqual(
            self.classify(None, present=False).status, "missing")
        self.assertEqual(self.classify("bad value").status, "malformed")
        self.assertEqual(self.classify("Lin").status, "unrecognized")

    def test_valid_word_override_and_absent_word_inheritance(self):
        line = self.classify("Hit", level="LINE")
        word = self.classify("Hur")
        resolved = llv2.resolve_word_language(
            word, line, word_attribute_present=True, contract=self.contract)
        self.assertEqual(
            (resolved.canonical, resolved.source, resolved.status),
            ("Hur", "WORD_EXPLICIT", "RESOLVED"),
        )

        absent = self.classify(None, present=False)
        inherited = llv2.resolve_word_language(
            absent, line, word_attribute_present=False, contract=self.contract)
        self.assertEqual(
            (inherited.canonical, inherited.source, inherited.status),
            ("Hit", "LINE_INHERITED", "RESOLVED"),
        )

    def test_empty_word_tag_is_preserved_and_anomaly_resolved(self):
        line = self.classify("Hit", level="LINE")
        empty = self.classify("")
        resolved = llv2.resolve_word_language(
            empty, line, word_attribute_present=True, contract=self.contract)
        self.assertEqual(
            (
                resolved.canonical,
                resolved.source,
                resolved.status,
                resolved.workbench_category,
            ),
            (
                "Hit",
                "LINE_INHERITED_AFTER_EMPTY_WORD_TAG",
                "RESOLVED_WITH_SOURCE_ANOMALY",
                "EMPTY_LANGUAGE_TAG",
            ),
        )

    def test_invalid_explicit_word_tag_never_falls_back(self):
        line = self.classify("Hit", level="LINE")
        for raw, category in (
                ("Lin", "UNRECOGNIZED_LANGUAGE_TAG"),
                ("bad value", "MALFORMED_LANGUAGE_TAG")):
            resolved = llv2.resolve_word_language(
                self.classify(raw),
                line,
                word_attribute_present=True,
                contract=self.contract,
            )
            self.assertIsNone(resolved.canonical)
            self.assertEqual(resolved.source, "UNRESOLVED")
            self.assertEqual(resolved.workbench_category, category)

    def test_invalid_line_does_not_trigger_document_fallback(self):
        invalid_line = self.classify("Lin", level="LINE")
        absent_word = self.classify(None, present=False)
        resolved = llv2.resolve_word_language(
            absent_word,
            invalid_line,
            word_attribute_present=False,
            contract=self.contract,
        )
        self.assertIsNone(resolved.canonical)
        self.assertEqual(resolved.status, "UNRESOLVED_LINE_LANGUAGE")
        self.assertEqual(resolved.source, "UNRESOLVED")

    def test_language_scopes_fail_closed_and_preserve_structure(self):
        with self.assertRaises(llv2.LanguageScopeError):
            llv2.token_in_language_scope(
                None,
                effective_language="Hit",
                is_structural_token=False,
                contract=self.contract,
            )
        with self.assertRaises(llv2.LanguageScopeError):
            llv2.token_in_language_scope(
                "SAME_LANGUAGE_AS_QUERY",
                effective_language="Hit",
                is_structural_token=False,
                contract=self.contract,
            )
        self.assertTrue(llv2.token_in_language_scope(
            "HITTITE_ONLY",
            effective_language=None,
            is_structural_token=True,
            contract=self.contract,
        ))
        self.assertTrue(llv2.token_in_language_scope(
            "SAME_LANGUAGE_AS_QUERY",
            effective_language="Hur",
            is_structural_token=False,
            query_language="Hur",
            contract=self.contract,
        ))
        self.assertTrue(llv2.token_in_language_scope(
            "CROSS_LANGUAGE_PARALLEL",
            effective_language="Akk",
            is_structural_token=False,
            query_language="Hit",
            contract=self.contract,
        ))
        self.assertIsNone(llv2.projected_language_identity(
            "ALL_LANGUAGES_UNCONDITIONED",
            "Hit",
            contract=self.contract,
        ))

    def test_token_join_uses_explicit_word_and_line_for_structure(self):
        line = self.classify("Hit", level="LINE")
        hurrian = self.classify("Hur")
        language_layer = {
            "line_lookup": {("Example", 0): line},
            "word_lookup": {("Example", 0, 1): hurrian},
        }
        word_token = {
            "doc_id": "Example",
            "line_index_in_doc": 0,
            "word_pos": 2,
            "token": "ki",
            "damage_state": "attested",
            "word_index_in_line": 1,
        }
        resolved = token_dataset.token_language_fields(
            word_token, language_layer, self.contract)
        self.assertEqual(
            resolved["effective"].canonical, "Hur")
        self.assertEqual(
            resolved["effective"].source, "WORD_EXPLICIT")
        self.assertFalse(resolved["is_structural"])

        structural_token = {
            **word_token,
            "word_pos": 3,
            "token": "<PAR>",
            "word_index_in_line": None,
        }
        structural = token_dataset.token_language_fields(
            structural_token, language_layer, self.contract)
        self.assertEqual(
            structural["effective"].canonical, "Hit")
        self.assertTrue(structural["is_structural"])

    def test_extractor_records_explicit_word_spans_with_parser_keys(self):
        root = ET.fromstring(
            b"<AO><docID>Example</docID><text xml:lang='Hit'>"
            b"<lb lg='Hit'/><w>nu</w><w lg='Hur'>ki-pi-ni</w>"
            b"<w lg=''>x</w><lb lg='Akk'/><w lg='Sum'>LUGAL</w>"
            b"</text></AO>"
        )
        rows, source_counts, anomalies = (
            migration.extract_document_rows(
            root,
            doc_id="Example",
            main_split="train",
            archive_member="CTH 1_XML/Example.xml",
            payload_sha256="0" * 64,
            contract=self.contract,
        ))
        self.assertEqual(
            source_counts,
            {"DOCUMENT": 1, "LINE": 2, "WORD": 3},
        )
        self.assertEqual(anomalies, [])
        word_rows = [
            row for row in rows if row["language_level"] == "WORD"]
        self.assertEqual(
            [
                (row["line_index_in_doc"], row["word_index_in_line"])
                for row in word_rows
            ],
            [(0, 1), (0, 2), (1, 0)],
        )
        self.assertNotIn(
            (0, 0),
            {
                (row["line_index_in_doc"], row["word_index_in_line"])
                for row in word_rows
            },
        )
        self.assertEqual(
            word_rows[1]["effective_lang_status"],
            "RESOLVED_WITH_SOURCE_ANOMALY",
        )

    def test_word_language_outside_primary_text_is_quarantined(self):
        root = ET.fromstring(
            b"<AO><docID>Example</docID><text><lb lg='Hit'/>"
            b"<w lg='Hur'>a</w></text><note><w lg='Akk'>b</w></note></AO>"
        )
        rows, source_counts, anomalies = (
            migration.extract_document_rows(
                root,
                doc_id="Example",
                main_split="train",
                archive_member="CTH 1_XML/Example.xml",
                payload_sha256="0" * 64,
                contract=self.contract,
            )
        )
        self.assertEqual(source_counts["WORD"], 1)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["category"], "PARSER_ANOMALY")
        self.assertEqual(
            anomalies[0]["anomaly_type"],
            "explicit_word_language_outside_primary_text",
        )
        self.assertEqual(
            anomalies[0]["ground_truth_status"], "NOT_CORPUS_TRUTH")
        self.assertEqual(
            len([row for row in rows if row["language_level"] == "WORD"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
