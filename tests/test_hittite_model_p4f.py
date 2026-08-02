"""Tests for lib/hittite_model_p4f.py (P4-F Stage 0,
reports/phase4_p4f_gate3_proposal.md).

Skipped entirely when torch is unavailable -- requirements-ci.txt
deliberately does not include it (Gate 3/model-ladder territory, same
reason scripts/00_tracers.py is not part of the CI-run suite). Locally,
where torch is installed, these are the actual regression tests for the
Gate 3 proposal's Stage 0 deliverable and its required tracer.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

if TORCH_AVAILABLE:
    import hittite_model_p4f as m


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestArchitecturalParityWithD14(unittest.TestCase):
    """Archive/reports/pretrain_report.md records D14 as 12,817,991 params
    under this exact config. If this ever stops matching, the reproduction
    in this module has silently drifted from the checkpoint it is meant to
    be compared against."""

    def test_unconditioned_param_count_matches_recorded_d14_figure(self):
        model = m.P4FEncoder(vocab_size=2374, condition_on_language=False)
        n_params = sum(p.numel() for p in model.parameters())
        self.assertEqual(n_params, 12817991)

    def test_conditioning_adds_exactly_the_language_embedding_params(self):
        unconditioned = m.P4FEncoder(vocab_size=2374, condition_on_language=False)
        conditioned = m.P4FEncoder(vocab_size=2374, condition_on_language=True)
        n_unconditioned = sum(p.numel() for p in unconditioned.parameters())
        n_conditioned = sum(p.numel() for p in conditioned.parameters())
        expected_extra = len(m.LANGUAGE_CODES) * unconditioned.d_model
        self.assertEqual(n_conditioned - n_unconditioned, expected_extra)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestFailClosedConditioning(unittest.TestCase):
    """The arm A / arm B cross-contamination guard, Sec.9 item 3's actual
    enforcement mechanism at the model level."""

    def _small_model(self, condition_on_language):
        return m.P4FEncoder(
            vocab_size=32, d_model=16, n_layers=1, n_heads=2, d_ff=32,
            seq_len=8, condition_on_language=condition_on_language)

    def test_conditioned_model_requires_lang_ids(self):
        model = self._small_model(True)
        input_ids = torch.randint(1, 32, (2, 8))
        with self.assertRaises(ValueError):
            model.encode(input_ids)

    def test_unconditioned_model_rejects_lang_ids(self):
        model = self._small_model(False)
        input_ids = torch.randint(1, 32, (2, 8))
        lang_ids = torch.zeros((2, 8), dtype=torch.long)
        with self.assertRaises(ValueError):
            model.encode(input_ids, lang_ids=lang_ids)

    def test_unconditioned_model_runs_without_lang_ids(self):
        model = self._small_model(False)
        input_ids = torch.randint(1, 32, (2, 8))
        hidden = model.encode(input_ids)
        self.assertEqual(tuple(hidden.shape), (2, 8, 16))

    def test_conditioned_model_runs_with_lang_ids(self):
        model = self._small_model(True)
        input_ids = torch.randint(1, 32, (2, 8))
        lang_ids = torch.zeros((2, 8), dtype=torch.long)
        hidden = model.encode(input_ids, lang_ids=lang_ids)
        self.assertEqual(tuple(hidden.shape), (2, 8, 16))


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestLanguageIdsForTokens(unittest.TestCase):
    def test_canonical_codes_map_to_their_registered_index(self):
        ids = m.language_ids_for_tokens(["Hit", "Akk", "Sum", "Pal"])
        self.assertEqual(ids, [m.LANGUAGE_TO_ID[c] for c in
                                ("Hit", "Akk", "Sum", "Pal")])

    def test_none_maps_to_unresolved(self):
        ids = m.language_ids_for_tokens([None])
        self.assertEqual(ids, [m.LANGUAGE_TO_ID["<UNRESOLVED>"]])

    def test_explicit_unresolved_string_maps_to_unresolved(self):
        ids = m.language_ids_for_tokens(["<UNRESOLVED>"])
        self.assertEqual(ids, [m.LANGUAGE_TO_ID["<UNRESOLVED>"]])

    def test_unrecognized_code_raises_rather_than_guessing(self):
        with self.assertRaises(m.UnrecognizedLanguageCodeError):
            m.language_ids_for_tokens(["Hittite"])  # not the canonical "Hit"

    def test_all_seven_canonical_codes_are_distinct_indices(self):
        ids = m.language_ids_for_tokens(list(m.LANGUAGE_CODES[:7]))
        self.assertEqual(len(set(ids)), 7)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestConditioningTracer(unittest.TestCase):
    """Unit-level coverage for the three functions
    scripts/phase4_p4f_conditioning_tracer.py runs as Sec.9's required
    pre-Stage-1 check."""

    def test_freshly_initialized_table_is_not_collapsed(self):
        model = m.P4FEncoder(
            vocab_size=32, d_model=16, n_layers=1, n_heads=2, d_ff=32,
            seq_len=8, condition_on_language=True)
        passed, worst = m.language_embedding_table_not_collapsed(model.lang_emb)
        self.assertTrue(passed, f"worst pair similarity: {worst}")

    def test_a_manually_collapsed_table_is_detected(self):
        """The check must actually be able to fail -- a table with two
        identical rows must not pass."""
        model = m.P4FEncoder(
            vocab_size=32, d_model=16, n_layers=1, n_heads=2, d_ff=32,
            seq_len=8, condition_on_language=True)
        with torch.no_grad():
            model.lang_emb.weight[1] = model.lang_emb.weight[0].clone()
        passed, worst = m.language_embedding_table_not_collapsed(model.lang_emb)
        self.assertFalse(passed)
        self.assertAlmostEqual(worst[2], 1.0, places=4)

    def test_conditioning_changes_forward_pass_on_a_real_model(self):
        model = m.P4FEncoder(
            vocab_size=32, d_model=16, n_layers=1, n_heads=2, d_ff=32,
            seq_len=8, condition_on_language=True)
        input_ids = torch.randint(1, 32, (2, 8))
        lang_ids = torch.tensor([[0, 1, 2, 3, 0, 1, 2, 3]] * 2)
        changed, max_diff = m.conditioning_changes_forward_pass(
            model, input_ids, lang_ids)
        self.assertTrue(changed, f"max diff was only {max_diff}")

    def test_conditioning_check_requires_a_conditioned_model(self):
        model = m.P4FEncoder(
            vocab_size=32, d_model=16, n_layers=1, n_heads=2, d_ff=32,
            seq_len=8, condition_on_language=False)
        input_ids = torch.randint(1, 32, (2, 8))
        lang_ids = torch.zeros((2, 8), dtype=torch.long)
        with self.assertRaises(ValueError):
            m.conditioning_changes_forward_pass(model, input_ids, lang_ids)

    def test_manifests_differing_only_in_expected_keys_passes(self):
        a = {"tag": "a", "seed": 1, "steps": 60000}
        b = {"tag": "b", "seed": 1, "steps": 60000}
        ok, unexpected, missing = m.manifests_differ_only_in(
            a, b, expected_differing_keys={"tag"})
        self.assertTrue(ok)
        self.assertEqual(unexpected, set())
        self.assertEqual(missing, set())

    def test_an_unexpected_confound_is_caught(self):
        """The concrete failure mode this check exists for: arm B silently
        also getting a different seed."""
        a = {"tag": "a", "seed": 1, "steps": 60000}
        b = {"tag": "b", "seed": 2, "steps": 60000}
        ok, unexpected, missing = m.manifests_differ_only_in(
            a, b, expected_differing_keys={"tag"})
        self.assertFalse(ok)
        self.assertEqual(unexpected, {"seed"})

    def test_a_missing_expected_difference_is_caught(self):
        """If arm A and arm B end up with the SAME tag, something is
        wrong even though nothing "extra" differs."""
        a = {"tag": "same", "seed": 1}
        b = {"tag": "same", "seed": 1}
        ok, unexpected, missing = m.manifests_differ_only_in(
            a, b, expected_differing_keys={"tag"})
        self.assertFalse(ok)
        self.assertEqual(missing, {"tag"})


if __name__ == "__main__":
    unittest.main()
