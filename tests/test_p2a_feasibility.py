"""Cleanroom and structural regression tests for the P2-A probe."""

import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2a_feasibility as p2a


class TestP2AFeasibility(unittest.TestCase):
    def test_consistent_shared_row_offset(self):
        relation = p2a.structural_relation([4, 5, 6], [2, 3, 4, 5, 6])
        self.assertEqual(relation["shared_rows"], 3)
        self.assertTrue(relation["row_offset_identifiable"])
        self.assertEqual(relation["n_distinct_row_deltas"], 1)

    def test_ordering_without_shared_rows(self):
        relation = p2a.structural_relation([1, 2], [5, 6])
        self.assertEqual(relation["ordering"], "a_before_b")
        self.assertFalse(relation["row_offset_identifiable"])

    def test_interleaved_without_shared_rows(self):
        relation = p2a.structural_relation([1, 3], [2, 4])
        self.assertEqual(
            relation["ordering"], "interleaved_without_shared_rows")
        self.assertFalse(relation["row_offset_identifiable"])

    def test_disallowed_payload_is_not_decoded(self):
        # The test-side tail is deliberately invalid JSON. A decoder that
        # touches it would raise; the split gate must skip it first.
        raw = (
            b'{"parent_doc": "test-doc", this is not valid JSON}\n'
            b'{"parent_doc": "dev-doc", "tier": "A", '
            b'"member_a": {"siglum": "1"}, '
            b'"member_b": {"siglum": "2"}, '
            b'"n_shared_lines": 0}\n'
        )
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(raw)
            path = Path(handle.name)
        try:
            audit = Counter()
            records = list(p2a.iter_allowed_join_metadata(
                path,
                {"test-doc": "test", "dev-doc": "dev"},
                set(),
                "dev",
                audit,
            ))
        finally:
            path.unlink()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["parent_doc"], "dev-doc")

    def test_ambiguous_parent_is_quarantined_before_decode(self):
        raw = b'{"parent_doc": "ambiguous", invalid tail}\n'
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(raw)
            path = Path(handle.name)
        try:
            audit = Counter()
            records = list(p2a.iter_allowed_join_metadata(
                path, {}, {"ambiguous"}, "dev", audit))
        finally:
            path.unlink()

        self.assertEqual(records, [])
        self.assertEqual(audit["ambiguous_parent_rows_skipped"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
