"""Regression tests for P2-E5 alignment aggregation and evaluation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2e5_alignment_probe as p2e5


def alignment_config():
    return {
        "flank_window": 6,
        "seed_ngram": 2,
        "maximum_seeded_witness_lines": 20,
        "maximum_alignments_per_witness_line": 1,
        "minimum_exact_matches_per_flank": 2,
        "minimum_normalized_score": 0.5,
        "match_score": 2,
        "mismatch_score": -1,
        "gap_score": -1,
        "maximum_witness_middle_length": 3,
    }


class TestP2E5AlignmentProbe(unittest.TestCase):
    def test_family_support_is_aggregated_once(self):
        lines = [
            {
                "fragment_id": "w1",
                "family": "f1",
                "line_position_in_fragment": 0,
                "line_index_in_doc": 0,
                "tokens": ("A", "B", "X", "D", "E"),
                "seed_overlap": 2,
            },
            {
                "fragment_id": "w2",
                "family": "f1",
                "line_position_in_fragment": 0,
                "line_index_in_doc": 0,
                "tokens": ("A", "B", "X", "D", "E"),
                "seed_overlap": 2,
            },
        ]
        config = {
            **alignment_config(),
            "maximum_middle_length": 3,
        }
        ranking = p2e5.generate_alignment_candidates(
            ("A", "B"), ("D", "E"), lines, config)
        candidate = next(
            value for value in ranking["alternatives"]
            if value["proposal"] == ("X",))
        self.assertEqual(candidate["support_count"], 1)

    def test_same_family_is_excluded_before_alignment(self):
        lines = {
            ("query", 0): {
                "line_id": ("query", 0),
                "fragment_id": "query",
                "family": "query-family",
                "cth": 1,
                "line_position_in_fragment": 0,
                "line_index_in_doc": 0,
                "tokens": ("A", "B", "X", "D", "E"),
            },
            ("other", 0): {
                "line_id": ("other", 0),
                "fragment_id": "other",
                "family": "other-family",
                "cth": 1,
                "line_position_in_fragment": 0,
                "line_index_in_doc": 0,
                "tokens": ("A", "B", "Y", "D", "E"),
            },
        }
        index = {1: {}}
        for line_id, line in lines.items():
            for seed in p2e5.ngrams(line["tokens"], 2):
                index[1].setdefault(seed, set()).add(line_id)
        selected, _ = p2e5.seeded_witness_lines(
            1,
            "query-family",
            ("A", "B"),
            ("D", "E"),
            lines,
            index,
            alignment_config(),
        )
        self.assertEqual(
            {value["family"] for value in selected}, {"other-family"})

    def test_synthetic_tracer_passes(self):
        self.assertEqual(
            p2e5.synthetic_alignment_tracer(
                alignment_config())["blocking_failures"],
            0,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
