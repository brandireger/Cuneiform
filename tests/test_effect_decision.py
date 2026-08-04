import unittest

from effect_decision import practical_increment_verdict


class PracticalIncrementVerdictTests(unittest.TestCase):
    def test_interval_including_zero_can_bound_a_material_increment(self):
        verdict = practical_increment_verdict(
            -0.0046, [-0.0162, 0.0058], 0.010,
            below_margin_label="NO_MATERIAL_CANINE_INCREMENT",
        )
        self.assertEqual(verdict, "NO_MATERIAL_CANINE_INCREMENT")

    def test_interval_including_zero_but_above_margin_is_inconclusive(self):
        verdict = practical_increment_verdict(
            0.0162, [-0.0012, 0.0324], 0.010,
            below_margin_label="CHARACTER_INCREMENT_BELOW_MARGIN",
        )
        self.assertEqual(verdict, "INCONCLUSIVE")

    def test_material_positive_requires_positive_lower_bound_and_margin(self):
        self.assertEqual(practical_increment_verdict(
            0.02, [0.005, 0.035], 0.01,
        ), "MATERIAL_INCREMENT_DETECTED")

    def test_invalid_margin_and_interval_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "margin"):
            practical_increment_verdict(0.1, [0.0, 0.2], 0.0)
        with self.assertRaisesRegex(ValueError, "reversed"):
            practical_increment_verdict(0.1, [0.2, 0.0], 0.01)


if __name__ == "__main__":
    unittest.main()
