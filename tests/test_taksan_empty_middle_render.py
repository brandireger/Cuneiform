"""The Takšan prototype must not draw an empty middle as a reading.

There was no renderer test for this page before. It is added with the
empty-middle change specifically because that defect is invisible: the page
rendered a candidate card whose sign line was blank, captioned as a
"witnessed omission", which reads as a positive claim that no sign stood
there. Nothing failed; it just quietly said the wrong thing.

These are string assertions against the page source, matching how
`tests/test_phase4_workbench_interface.py` pins the workbench's display
contract. They do not execute the page.
"""
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import expert_decision_contract as edc  # noqa: E402


class TestTaksanEmptyMiddleRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (
            ROOT / "demo" / "taksan_missing_text_prototype.html"
        ).read_text(encoding="utf-8")

    def test_the_page_reads_the_display_block(self):
        self.assertIn('opt.display.kind === "EMPTY_MIDDLE"', self.html)

    def test_the_old_witnessed_omission_wording_is_gone(self):
        """It asserted the omission was real. The witnesses do not establish
        that; they contradict the query's structure."""
        self.assertNotIn("a witnessed omission, not missing data", self.html)
        self.assertNotIn("(empty — witnessed omission)", self.html)

    def test_the_card_is_marked_as_not_a_reading(self):
        self.assertIn("not-a-reading", self.html)
        self.assertIn("empty-middle", self.html)

    def test_the_rank_track_record_label_is_suppressed(self):
        """Captioning an UNAVAILABLE box 'Track record of this rank' invites
        the reader to supply the missing number themselves."""
        self.assertIn("No rank track record applies here", self.html)

    def test_the_select_button_does_not_call_it_a_reading(self):
        self.assertIn("Record that no sign stood here", self.html)

    def test_the_preview_dropdown_is_also_corrected(self):
        self.assertIn("contradicts the markup, not a reading", self.html)

    def test_injected_contract_text_is_escaped(self):
        self.assertIn("function escapeHtml(", self.html)
        for field in ("em.render_signs_as", "em.headline", "em.detail"):
            with self.subTest(field=field):
                self.assertIn(f"escapeHtml({field})", self.html)


class TestExportedPacketsCarryTheAnnotation(unittest.TestCase):
    """Guard the built artifact, not just the code that builds it."""

    EXPORT = ROOT / "Phase3" / "demo_out" / "missing_text_demo_data.js"

    def test_every_empty_option_in_the_export_is_annotated(self):
        if not self.EXPORT.exists():
            self.skipTest("demo export not built")
        import json
        import re
        text = self.EXPORT.read_text(encoding="utf-8")
        packets = json.loads(re.search(r"=\s*(\[.*\]);\s*$", text, re.S).group(1))
        empty = [
            (packet["packet_id"], option)
            for packet in packets
            for option in packet.get("candidate_set", {}).get("options", [])
            if not option.get("signs")
        ]
        self.assertTrue(empty, "expected empty middles in the export")
        for packet_id, option in empty:
            with self.subTest(packet_id=packet_id):
                self.assertEqual(option["display"]["kind"], "EMPTY_MIDDLE")
                self.assertFalse(option["display"]["is_a_reading"])
                self.assertEqual(option["option_audit"]["kind"], "UNAVAILABLE")

    def test_annotated_packets_carry_the_limitation_and_contradiction(self):
        if not self.EXPORT.exists():
            self.skipTest("demo export not built")
        import json
        import re
        text = self.EXPORT.read_text(encoding="utf-8")
        packets = json.loads(re.search(r"=\s*(\[.*\]);\s*$", text, re.S).group(1))
        for packet in packets:
            options = packet.get("candidate_set", {}).get("options", [])
            if not any(not option.get("signs") for option in options):
                continue
            with self.subTest(packet_id=packet["packet_id"]):
                codes = [item["code"] for item in packet["limitations"]]
                self.assertIn(edc.EMPTY_MIDDLE_LIMITATION_CODE, codes)
                types = [
                    item["type"] for item in packet["contradictory_evidence"]]
                self.assertIn("WITNESS_ANCHORS_ADJACENT", types)


if __name__ == "__main__":
    unittest.main()
