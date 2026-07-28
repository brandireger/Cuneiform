"""Tests for P2-E9 cross-line per-rank calibration.

The property worth pinning here is support counting. `LAYOUT_AGNOSTIC`
searches two anchor indices, and the same witness family can appear in both.
Support is a count of *independent sources*, and it is exactly the quantity
the selector rule thresholds on — so double-counting one family would inflate
the evidence bar's own input and let weaker spans through as if they were
better corroborated.
"""
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

import p2e9_cross_line_calibration as p2e9  # noqa: E402

KEY = (("a", "b"), ("c", "d"))


def index(mapping):
    """{proposal: {families}} -> the nested shape the ranking reads."""
    return {7: {KEY: {proposal: set(families)
                      for proposal, families in mapping.items()}}}


class TestMergedRanking(unittest.TestCase):
    def test_a_family_in_both_indices_is_counted_once(self):
        cross = index({("x",): {"fam-1"}})
        same = index({("x",): {"fam-1"}})
        ranking = p2e9.merged_ranking((cross, same), 7, KEY, "query-fam")
        self.assertEqual(ranking["alternatives"][0]["support_count"], 1)

    def test_distinct_families_across_indices_accumulate(self):
        cross = index({("x",): {"fam-1"}})
        same = index({("x",): {"fam-2"}})
        ranking = p2e9.merged_ranking((cross, same), 7, KEY, "query-fam")
        self.assertEqual(ranking["alternatives"][0]["support_count"], 2)
        self.assertEqual(
            ranking["alternatives"][0]["supporting_families"],
            ("fam-1", "fam-2"))

    def test_the_query_own_family_never_supports_its_own_span(self):
        cross = index({("x",): {"query-fam"}})
        ranking = p2e9.merged_ranking((cross,), 7, KEY, "query-fam")
        self.assertEqual(ranking["alternatives"], [])
        self.assertFalse(ranking["unique_top"])

    def test_ranking_orders_by_support_then_deterministically(self):
        cross = index({
            ("low",): {"fam-1"},
            ("high",): {"fam-1", "fam-2", "fam-3"},
            ("mid",): {"fam-1", "fam-2"},
        })
        ranking = p2e9.merged_ranking((cross,), 7, KEY, "other")
        self.assertEqual(
            [a["proposal"] for a in ranking["alternatives"]],
            [("high",), ("mid",), ("low",)])

    def test_tied_top_is_not_a_unique_top(self):
        cross = index({("x",): {"fam-1"}, ("y",): {"fam-2"}})
        ranking = p2e9.merged_ranking((cross,), 7, KEY, "other")
        self.assertFalse(ranking["unique_top"])
        self.assertEqual(ranking["support_margin"], 0)

    def test_dominance_and_margin_reflect_merged_support(self):
        cross = index({("x",): {"fam-1", "fam-2", "fam-3"}, ("y",): {"fam-4"}})
        ranking = p2e9.merged_ranking((cross,), 7, KEY, "other")
        self.assertTrue(ranking["unique_top"])
        self.assertEqual(ranking["top_support"], 3)
        self.assertEqual(ranking["support_margin"], 2)
        self.assertAlmostEqual(ranking["dominance"], 0.75)

    def test_layout_agnostic_support_is_never_below_strict(self):
        """It admits a superset of witnesses, so it cannot rank a span lower."""
        cross = index({("x",): {"fam-1"}})
        same = index({("x",): {"fam-2"}, ("y",): {"fam-3"}})
        strict = p2e9.merged_ranking((cross,), 7, KEY, "q")
        agnostic = p2e9.merged_ranking((cross, same), 7, KEY, "q")
        self.assertGreaterEqual(
            agnostic["top_support"], strict["top_support"])
        self.assertGreaterEqual(
            agnostic["alternative_count"], strict["alternative_count"])


class TestTargetSensitivity(unittest.TestCase):
    """The sweep must describe the evidence, never rescue a target."""

    def records(self, correct, total):
        out = []
        for i in range(total):
            gold = ("g",)
            top = gold if i < correct else ("wrong",)
            out.append({
                "cth": 1, "gold": gold,
                "ranking": {
                    "alternatives": [{"proposal": top, "support_count": 5}],
                    "unique_top": True, "top_support": 5,
                    "runner_up_support": 0, "support_margin": 5,
                    "dominance": 1.0, "alternative_count": 1,
                },
            })
        return out

    def test_an_unreachable_target_is_reported_as_unreachable(self):
        rules = [{"minimum_top_support_families": 1, "minimum_support_margin": 0,
                  "minimum_dominance": 0.0, "maximum_alternatives": None}]
        sweep = p2e9.target_sensitivity(
            self.records(60, 100), rules, 50, [0.5, 0.9])
        self.assertTrue(sweep[0]["reachable"])
        self.assertFalse(sweep[1]["reachable"])
        self.assertIsNone(sweep[1]["achieved_rate"])

    def test_a_rule_below_the_accept_floor_is_not_used(self):
        rules = [{"minimum_top_support_families": 1, "minimum_support_margin": 0,
                  "minimum_dominance": 0.0, "maximum_alternatives": None}]
        sweep = p2e9.target_sensitivity(
            self.records(10, 10), rules, 50, [0.5])
        self.assertFalse(sweep[0]["reachable"])



class TestUnratifiedTargetFailsClosed(unittest.TestCase):
    """A null target must stop a consumer, not fall back to same-line's."""

    def test_null_target_is_refused(self):
        with self.assertRaises(p2e9.UnratifiedPolicyError):
            p2e9.require_calibration_target(
                {"calibration_target": None,
                 "calibration_target_status": "UNRATIFIED"})

    def test_a_value_without_ratified_status_is_refused(self):
        """A number someone typed in is not a ratification."""
        with self.assertRaises(p2e9.UnratifiedPolicyError):
            p2e9.require_calibration_target(
                {"calibration_target": 0.8,
                 "calibration_target_status": "UNRATIFIED"})

    def test_a_ratified_value_is_returned(self):
        self.assertEqual(
            p2e9.require_calibration_target(
                {"calibration_target": 0.8,
                 "calibration_target_status": "RATIFIED"}),
            0.8)

    def test_the_shipped_config_records_who_ratified_what(self):
        """A ratified value must carry its provenance, not just a number.

        The point of this test is that changing the policy requires touching
        the ratification fields too, so a target cannot drift without a record
        of who set it and why.
        """
        import json
        config = json.loads(
            p2e9.CROSS_LINE_CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(config["witness_admission_rule"], "LAYOUT_AGNOSTIC")
        self.assertEqual(config["witness_admission_rule_status"], "RATIFIED")
        self.assertEqual(config["calibration_target"], 0.75)
        self.assertEqual(config["calibration_target_status"], "RATIFIED")
        for field in ("witness_admission_rule_ratified",
                      "calibration_target_ratified",
                      "calibration_target_rationale"):
            self.assertTrue(config.get(field), f"{field} must be recorded")

    def test_the_cross_line_target_is_not_the_same_line_target(self):
        """Guards the substitution the whole exercise exists to prevent."""
        import json
        cross = json.loads(
            p2e9.CROSS_LINE_CONFIG_PATH.read_text(encoding="utf-8"))
        same = json.loads(p2e9.CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertNotEqual(
            cross["calibration_target"], same["calibration_target"])

if __name__ == "__main__":
    unittest.main()
