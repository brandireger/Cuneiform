"""Tests for the empty-middle census helpers.

The census reports a number that could motivate a scoring change, so its two
pure helpers are pinned here. `filtered_view` in particular must produce
something the REAL ranking functions consume unchanged -- the whole point of
building a filtered index view instead of post-processing a ranking is that
the counterfactual is computed by the calibrated ranking construction, not by
a second implementation of it.
"""
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
LIB = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(LIB))

import p2e2_abstention_calibration as p2e2  # noqa: E402
import p2e9_cross_line_calibration as p2e9  # noqa: E402
import real_gap_empty_middle_census as census  # noqa: E402


KEY = (("a", "b"), ("c", "d"))
CTH = 700


def index_with(entries):
    """A minimal anchor index: {proposal: {families}} under one (cth, key)."""
    return {CTH: {KEY: entries}}


class TestEmptyMiddleRank(unittest.TestCase):
    def test_absent_empty_middle_reports_none(self):
        ranking = {"alternatives": [
            {"proposal": ("x",)}, {"proposal": ("y",)}]}
        self.assertIsNone(census.empty_middle_rank(ranking))

    def test_rank_is_one_based(self):
        ranking = {"alternatives": [
            {"proposal": ("x",)}, {"proposal": ()}, {"proposal": ("y",)}]}
        self.assertEqual(census.empty_middle_rank(ranking), 2)

    def test_empty_at_the_top_is_rank_one(self):
        ranking = {"alternatives": [{"proposal": ()}, {"proposal": ("x",)}]}
        self.assertEqual(census.empty_middle_rank(ranking), 1)

    def test_no_alternatives_reports_none(self):
        self.assertIsNone(census.empty_middle_rank({"alternatives": []}))

    def test_a_list_proposal_is_matched_like_a_tuple(self):
        """Payloads round-tripped through JSON carry lists, not tuples."""
        self.assertEqual(
            census.empty_middle_rank({"alternatives": [{"proposal": []}]}), 1)


class TestFilteredView(unittest.TestCase):
    def test_the_empty_middle_is_the_only_thing_removed(self):
        index = index_with({(): {"f1"}, ("x",): {"f2"}, ("y", "z"): {"f3"}})
        view, = census.filtered_view((index,), CTH, KEY)
        self.assertEqual(
            set(view[CTH][KEY]), {("x",), ("y", "z")})

    def test_families_survive_untouched(self):
        index = index_with({(): {"f1"}, ("x",): {"f2", "f3"}})
        view, = census.filtered_view((index,), CTH, KEY)
        self.assertEqual(view[CTH][KEY][("x",)], {"f2", "f3"})

    def test_a_missing_key_yields_an_empty_view_not_an_error(self):
        view, = census.filtered_view((index_with({}),), CTH, ("nope", "nope"))
        self.assertEqual(view[CTH][("nope", "nope")], {})

    def test_every_index_is_viewed_for_the_merged_ranking(self):
        first = index_with({(): {"f1"}, ("x",): {"f2"}})
        second = index_with({(): {"f3"}, ("y",): {"f4"}})
        views = census.filtered_view((first, second), CTH, KEY)
        self.assertEqual(len(views), 2)
        self.assertEqual(set(views[0][CTH][KEY]), {("x",)})
        self.assertEqual(set(views[1][CTH][KEY]), {("y",)})


class TestFilteredViewFeedsTheRealRankingFunctions(unittest.TestCase):
    """The counterfactual must go through the calibrated ranking construction."""

    def test_same_line_ranking_consumes_the_view(self):
        index = index_with({(): {"f1", "f2"}, ("x",): {"f3"}})
        before = p2e2.proposal_ranking(index, CTH, KEY, "query")
        self.assertEqual(before["alternatives"][0]["proposal"], ())

        view, = census.filtered_view((index,), CTH, KEY)
        after = p2e2.proposal_ranking(view, CTH, KEY, "query")
        self.assertEqual(after["alternatives"][0]["proposal"], ("x",))
        self.assertEqual(after["alternative_count"], 1)

    def test_merged_ranking_consumes_the_views(self):
        first = index_with({(): {"f1", "f2"}})
        second = index_with({("x",): {"f3"}})
        before = p2e9.merged_ranking((first, second), CTH, KEY, "query")
        self.assertEqual(before["alternative_count"], 2)

        views = census.filtered_view((first, second), CTH, KEY)
        after = p2e9.merged_ranking(views, CTH, KEY, "query")
        self.assertEqual(after["alternative_count"], 1)
        self.assertEqual(after["alternatives"][0]["proposal"], ("x",))

    def test_filtering_can_leave_nothing_at_all(self):
        """The observed dominant case: the empty middle IS the whole case."""
        index = index_with({(): {"f1", "f2"}})
        view, = census.filtered_view((index,), CTH, KEY)
        after = p2e2.proposal_ranking(view, CTH, KEY, "query")
        self.assertEqual(after["alternatives"], [])
        self.assertFalse(after["unique_top"])

    def test_the_query_family_is_still_excluded_after_filtering(self):
        """Filtering must not smuggle the query's own family back in."""
        index = index_with({(): {"f1"}, ("x",): {"query"}})
        view, = census.filtered_view((index,), CTH, KEY)
        after = p2e2.proposal_ranking(view, CTH, KEY, "query")
        self.assertEqual(after["alternatives"], [])


if __name__ == "__main__":
    unittest.main()
