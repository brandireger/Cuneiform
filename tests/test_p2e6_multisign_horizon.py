"""Regression tests for P2-E6 adaptive multi-sign candidate sets."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2e6_multisign_horizon as p2e6


def alternative(proposal, support):
    return {
        "proposal": (proposal,),
        "support_count": support,
        "supporting_families": tuple(f"f{i}" for i in range(support)),
    }


def ranking(*alternatives):
    return {
        "alternatives": list(alternatives),
        "unique_top": True,
        "top_support": alternatives[0]["support_count"] if alternatives else 0,
        "runner_up_support":
            alternatives[1]["support_count"] if len(alternatives) > 1 else 0,
        "support_margin": (
            alternatives[0]["support_count"]
            - alternatives[1]["support_count"]
            if len(alternatives) > 1 else 0),
        "dominance": 1.0,
        "alternative_count": len(alternatives),
    }


class TestP2E6MultisignHorizon(unittest.TestCase):
    def test_tie_complete_boundary_does_not_lexically_exclude(self):
        values = ranking(
            alternative("a", 3),
            alternative("b", 2),
            alternative("c", 1),
            alternative("d", 1),
        )
        displayed = p2e6.tie_complete_alternatives(values, 3)
        self.assertEqual(
            [value["proposal"] for value in displayed],
            [("a",), ("b",), ("c",), ("d",)],
        )

    def test_adaptive_policy_uses_longest_supported_anchor(self):
        base = {
            "fragment_id": "q",
            "line_position_in_fragment": 0,
            "sign_offset_in_line": 3,
            "gold": ("g",),
            "left_anchor": ("L",),
            "right_anchor": ("R",),
            "ranking": ranking(alternative("a1", 1)),
        }
        a2 = {
            **base,
            "left_anchor": ("L0", "L"),
            "right_anchor": ("R", "R0"),
            "ranking": ranking(alternative("a2", 1)),
        }
        a3 = {
            **base,
            "left_anchor": ("L1", "L0", "L"),
            "right_anchor": ("R", "R0", "R1"),
            "ranking": ranking(),
        }
        result = p2e6.build_adaptive_records(
            {"a1_m2": [base], "a2_m2": [a2], "a3_m2": [a3]},
            [2],
            [1, 2, 3],
        )[2][0]
        self.assertEqual(result["adaptive_anchor_length"], 2)
        self.assertEqual(
            result["ranking"]["alternatives"][0]["proposal"], ("a2",))

    def test_horizon_metrics_separate_coverage_and_inclusion(self):
        records = [
            {
                "cth": 1,
                "gold": ("g",),
                "adaptive_anchor_length": 2,
                "ranking": ranking(alternative("g", 1)),
            },
            {
                "cth": 1,
                "gold": ("g",),
                "adaptive_anchor_length": None,
                "ranking": ranking(),
            },
        ]
        metrics = p2e6.horizon_metrics(records, 5)
        self.assertEqual(metrics["presentation_coverage_percent"], 50.0)
        self.assertEqual(
            metrics["displayed_set_attested_inclusion_percent_of_presented"],
            100.0,
        )
        self.assertEqual(
            metrics["effective_attested_recoverability_percent_of_eligible"],
            50.0,
        )

    def test_adaptive_policy_tracer_passes(self):
        self.assertEqual(
            p2e6.adaptive_policy_tracer()["blocking_failures"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
