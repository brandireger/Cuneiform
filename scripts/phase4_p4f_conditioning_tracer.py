#!/usr/bin/env python3
"""The conditioned-vs-unconditioned tracer required by
reports/phase4_p4f_gate3_proposal.md Sec.9, before either Stage 1 run
starts. Three canary-scale checks, no GPU epoch and no real corpus data
required -- a freshly initialized model and a tiny synthetic batch are
enough, in the tradition of scripts/00_tracers.py.

This cannot tell you language-conditioning HELPS the boundary/join task
(that is Stage 1's own falsifier, on real data, after real training). It
can only catch the specific failure mode this project has already lost a
research phase to once: a plumbing bug that silently prevents an intended
signal from ever reaching the model
(P5_CLOSEOUT.md Sec.2.4 -- the E2 content-blind scoring bug).

Usage:
    python scripts/phase4_p4f_conditioning_tracer.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import torch  # noqa: E402

import hittite_model_p4f as m  # noqa: E402


def main():
    results = []

    model = m.P4FEncoder(vocab_size=64, d_model=32, n_layers=2, n_heads=2,
                          d_ff=64, seq_len=16, condition_on_language=True)

    passed, worst = m.language_embedding_table_not_collapsed(model.lang_emb)
    results.append((
        "1. language embedding table is not collapsed at init", passed,
        f"worst pair {worst[0]},{worst[1]}: cosine similarity {worst[2]:.4f}"))

    torch.manual_seed(0)
    canary_ids = torch.randint(1, 64, (4, 16))
    canary_lang_ids = torch.tensor([
        [m.LANGUAGE_TO_ID[code] for code in
         ("Hit", "Hit", "Akk", "Sum", "Hit", "Hur", "Hit", "Hit",
          "Luw", "Hit", "Pal", "Hit", "Hat", "Hit", "Hit", "Hit")]
    ] * 4)
    changed, max_diff = m.conditioning_changes_forward_pass(
        model, canary_ids, canary_lang_ids)
    results.append((
        "2. conditioning measurably changes the forward pass", changed,
        f"max abs hidden-state difference vs constant-language input: "
        f"{max_diff:.6f}"))

    manifest_a = {
        "tag": "multilingual_unconditioned_p4f", "condition_on_language": False,
        "seed": 20260802, "max_steps": 60000, "d_model": 384,
    }
    manifest_b = {
        "tag": "multilingual_conditioned_p4f", "condition_on_language": True,
        "seed": 20260802, "max_steps": 60000, "d_model": 384,
    }
    ok, unexpected, missing = m.manifests_differ_only_in(
        manifest_a, manifest_b,
        expected_differing_keys={"tag", "condition_on_language"})
    results.append((
        "3. example Stage 1 manifest pair differs only where expected", ok,
        f"unexpected diffs: {unexpected or 'none'}; "
        f"missing expected diffs: {missing or 'none'}"))

    blocking = 0
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not passed:
            blocking += 1

    print(f"\n{len(results) - blocking}/{len(results)} passed.")
    if blocking:
        print(
            "BLOCKING: do not start a Stage 1 run until every check above "
            "passes (reports/phase4_p4f_gate3_proposal.md Sec.9).")
        sys.exit(1)


if __name__ == "__main__":
    main()
