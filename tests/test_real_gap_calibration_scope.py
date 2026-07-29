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


if __name__ == "__main__":
    unittest.main()
