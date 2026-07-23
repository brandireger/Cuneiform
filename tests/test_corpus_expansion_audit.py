"""Cleanroom regressions for the TLHdig 0.3 corpus audit."""

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import corpus_expansion_audit as audit


class TestCorpusExpansionAudit(unittest.TestCase):
    def test_cth_folder_suffix_is_supported(self):
        self.assertEqual(
            audit.cth_from_path(
                "root/CTH 786_XML_HFR/KBo 17.86+.xml"),
            786,
        )

    def test_gate_fails_closed(self):
        split_lookup = {
            "train-doc": "train",
            "dev-doc": "dev",
            "test-doc": "test",
            "odd-doc": "unexpected",
        }
        allowed = {"train", "dev", "discovery"}
        prohibited = {"test"}
        self.assertEqual(
            audit.classify_stem(
                "train-doc", split_lookup, set(), set(), allowed, prohibited),
            "ALLOWED_TRAIN",
        )
        self.assertEqual(
            audit.classify_stem(
                "test-doc", split_lookup, set(), set(), allowed, prohibited),
            "PROTECTED_TEST",
        )
        self.assertEqual(
            audit.classify_stem(
                "new-doc", split_lookup, set(), set(), allowed, prohibited),
            "QUARANTINE_UNMATCHED",
        )
        self.assertEqual(
            audit.classify_stem(
                "train-doc",
                split_lookup,
                set(),
                {"train-doc"},
                allowed,
                prohibited,
            ),
            "QUARANTINE_DUPLICATE_STEM",
        )
        self.assertEqual(
            audit.classify_stem(
                "dev-doc",
                split_lookup,
                {"dev-doc"},
                set(),
                allowed,
                prohibited,
            ),
            "QUARANTINE_SPLIT_AMBIGUOUS",
        )

    def test_archive_payloads_read_only_for_allowed_unique_stems(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.zip"
            valid = (
                b"<AO><docID>train-doc</docID>"
                b"<lb lg='Hit'><w>nu</w></lb></AO>"
            )
            forbidden = b"THIS MUST NEVER BE PARSED"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("root/CTH 1_XML/train-doc.xml", valid)
                archive.writestr("root/CTH 1_XML/test-doc.xml", forbidden)
                archive.writestr("root/CTH 1_XML/new-doc.xml", forbidden)
                archive.writestr("root/CTH 1_XML/dup-doc.xml", forbidden)
                archive.writestr("root/CTH 2_XML/dup-doc.xml", forbidden)

            index = audit.archive_index(path)
            split_lookup = {
                "train-doc": "train",
                "test-doc": "test",
                "dup-doc": "train",
            }
            result = audit.scan_allowed_payloads(
                path,
                index,
                split_lookup,
                set(),
                {"train", "dev", "discovery"},
                {"test"},
            )
            self.assertEqual(
                result["payload_read_gate_counts"],
                {"ALLOWED_TRAIN": 1},
            )
            self.assertEqual(result["parsed_documents"], 1)
            self.assertEqual(result["parse_error_count"], 0)
            self.assertEqual(result["line_elements"], 1)
            gates = audit.gate_counts(
                index,
                split_lookup,
                set(),
                {"train", "dev", "discovery"},
                {"test"},
            )
            self.assertEqual(gates["PROTECTED_TEST"], 1)
            self.assertEqual(gates["QUARANTINE_UNMATCHED"], 1)
            self.assertEqual(gates["QUARANTINE_DUPLICATE_STEM"], 2)

    def test_compare_allowed_reports_only_common_safe_payloads(self):
        baseline = {
            "raw_sha256_by_stem": {"a": "same", "b": "old"},
            "cth_by_stem": {"a": 1, "b": 2},
            "tag_instances": {"lb": 1},
            "attribute_instances": {"lb@lg": 1},
            "parse_error_stems": {"b"},
        }
        candidate = {
            "raw_sha256_by_stem": {"a": "same", "b": "new", "c": "new"},
            "cth_by_stem": {"a": 1, "b": 3, "c": 4},
            "tag_instances": {"lb": 1, "newTag": 1},
            "attribute_instances": {"lb@lg": 1, "newTag@x": 1},
            "parse_error_stems": {"b", "c"},
        }
        result = audit.compare_allowed(baseline, candidate)
        self.assertEqual(result["common_allowed_unique_stems"], 2)
        self.assertEqual(result["byte_changed_documents"], 1)
        self.assertEqual(result["cth_folder_moved_documents"], 1)
        self.assertEqual(result["tags_added_in_candidate"], ["newTag"])
        self.assertEqual(
            result["parse_errors_persistent_on_common_stems"], ["b"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
