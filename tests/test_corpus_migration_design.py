"""Regression tests for the TLHdig 0.3 migration-design audit."""

import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import corpus_migration_design as design


def fixture_index(entries):
    by_stem = defaultdict(list)
    for stem, infos in entries.items():
        by_stem[stem].extend(infos)
    return {
        "by_stem": by_stem,
        "duplicates": {
            stem: infos for stem, infos in by_stem.items()
            if len(infos) != 1
        },
    }


class FakeInfo:
    def __init__(self, filename):
        self.filename = filename


class TestIdentifierReconciliation(unittest.TestCase):
    def test_conservative_revisions_and_ambiguity(self):
        baseline = fixture_index({
            "KBo 1.1": [FakeInfo("old/CTH 1_XML/KBo 1.1.xml")],
            "P 5": [FakeInfo("old/CTH 1_XML/P 5.xml")],
            "C╠ºorum 2": [FakeInfo("old/CTH 1_XML/C.xml")],
            "KBo 2.2 (comment)": [FakeInfo("old/CTH 1_XML/A.xml")],
        })
        candidate = fixture_index({
            "KBo 1.1+": [FakeInfo("new/CTH 1_XML/KBo 1.1+.xml")],
            "P. 5": [FakeInfo("new/CTH 1_XML/P. 5.xml")],
            "Corum 2": [FakeInfo("new/CTH 1_XML/C.xml")],
            "KBo 2.2": [FakeInfo("new/CTH 1_XML/A.xml")],
            "KBo 2.2+": [FakeInfo("new/CTH 1_XML/B.xml")],
            "EBo 99": [FakeInfo("new/CTH 832_XML/EBo 99.xml")],
        })
        result = design.reconcile_identifiers(baseline, candidate)
        self.assertEqual(result["probable_revision_pair_count"], 3)
        self.assertEqual(result["ambiguous_candidate_stem_count"], 2)
        self.assertEqual(
            result["unresolved_candidate_stems"], ["EBo 99"])

    def test_duplicate_target_is_not_resolved(self):
        baseline = fixture_index({
            "KBo 3.3": [FakeInfo("old/CTH 1_XML/KBo 3.3.xml")],
        })
        candidate = fixture_index({
            "KBo 3.3+": [
                FakeInfo("new/CTH 1_XML/KBo 3.3+.xml"),
                FakeInfo("new/CTH 2_XML/KBo 3.3+.xml"),
            ],
        })
        result = design.reconcile_identifiers(baseline, candidate)
        self.assertEqual(result["probable_revision_pair_count"], 0)
        self.assertEqual(result["ambiguous_candidate_stem_count"], 1)


class TestParserDiagnostics(unittest.TestCase):
    def classify(self, xml):
        raw = xml.encode("utf-8")
        with self.assertRaises(ET.ParseError) as raised:
            ET.fromstring(raw)
        return design.classify_parse_failure(raw, raised.exception)

    def test_invalid_qname_is_classified(self):
        result = self.classify(
            "<AOxml xmlns:AO='x'><AO:-LineNrExpl>x</AO:-LineNrExpl></AOxml>")
        self.assertEqual(result["category"], "invalid_qname_ao_dash_linenr")

    def test_unescaped_markup_in_attribute_is_classified(self):
        result = self.classify('<AOxml><note c="x</sGr>y"/></AOxml>')
        self.assertEqual(
            result["category"], "unescaped_markup_inside_attribute")

    def test_namespace_mismatch_is_classified(self):
        result = self.classify(
            "<AOxml xmlns:AO='x'><AO:TxtPubl>x</TxtPubl></AOxml>")
        self.assertEqual(result["category"], "namespace_prefix_mismatch")

    def test_unclosed_inline_element_is_classified(self):
        result = self.classify("<AOxml><w><sGr>x</w></AOxml>")
        self.assertEqual(
            result["category"], "unclosed_inline_element_before_word_close")

    def test_unclosed_damage_word_is_classified(self):
        result = self.classify(
            "<AOxml><text><w><del_in/><del_fin/></text></AOxml>")
        self.assertEqual(
            result["category"],
            "unclosed_empty_damage_word_at_line_boundary",
        )

    def test_prohibited_payload_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "root/CTH 1_XML/train.xml",
                    "<AOxml><w><sGr>x</w></AOxml>",
                )
                archive.writestr(
                    "root/CTH 1_XML/test.xml",
                    b"THIS MUST NEVER BE READ",
                )
            index = design.audit.archive_index(archive_path)
            result = design.diagnose_allowed_parse_errors(
                archive_path,
                index,
                {"train", "test"},
                {"train": "train", "test": "test"},
                set(),
                {"train", "dev", "discovery"},
                {"test"},
            )
            self.assertEqual(result["payloads_read"], 1)
            self.assertEqual(
                result["skipped_without_payload_read"],
                {"PROTECTED_TEST": 1},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
