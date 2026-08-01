import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import real_gap_calibration as rgc  # noqa: E402


class TestRealGapCalibrationScope(unittest.TestCase):
    def test_scope_is_union_without_losing_population_identity(self):
        same_line = {10: object(), 20: object()}
        cross = {"cth_to_fold": {20: object(), 30: object()}}

        scopes = rgc.calibration_scope_cths(same_line, cross)

        self.assertEqual(scopes["same_line"], [10, 20])
        self.assertEqual(scopes["cross_line"], [20, 30])
        self.assertEqual(scopes["union"], [10, 20, 30])

    def test_unratified_cross_line_fails_closed_to_same_line_scope(self):
        scopes = rgc.calibration_scope_cths({10: object(), 20: object()}, None)

        self.assertEqual(scopes["same_line"], [10, 20])
        self.assertEqual(scopes["cross_line"], [])
        self.assertEqual(scopes["union"], [10, 20])

    def test_exclude_indeterminate_lacunae_drops_only_bare_ellipsis_runs(self):
        # Split estimand (item 5a, reports/phase5_lacuna_scope_decision.md):
        # a single-sign run whose only token is the indeterminate-lacuna
        # ellipsis asserts an UNKNOWN amount of text is missing, not one
        # sign, so it is excluded from the narrower denominator. A run that
        # merely contains the ellipsis alongside other tokens, or an
        # ordinary restored sign, is a real single-sign (or multi-sign)
        # claim and must be kept.
        lacuna = {"run": {"tokens": ["…"]}}
        restored_sign = {"run": {"tokens": ["ku"]}}
        multi_sign_with_ellipsis = {"run": {"tokens": ["…", "ku"]}}

        kept = rgc.exclude_indeterminate_lacunae(
            [lacuna, restored_sign, multi_sign_with_ellipsis])

        self.assertEqual(kept, [restored_sign, multi_sign_with_ellipsis])


if __name__ == "__main__":
    unittest.main()
