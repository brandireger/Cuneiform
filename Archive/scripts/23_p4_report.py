#!/usr/bin/env python3
"""
23_p4_report.py -- P4 final acceptance-check aggregator.

Usage:
    python scripts/23_p4_report.py

Pulls headline numbers from each already-accepted phase report
(reports/h1_patch_report.md, tokenizer_report.md, fracture_report.md,
pretrain_report.md, biencoder_report.md) into one master p4_report.md
per specs/P4_NEURAL_SPEC.md's acceptance checklist. Does not recompute
anything -- every number here is copied from its source report, never
re-derived, per CLAUDE.md's "small artifacts" exchange convention.
"""
import json
from pathlib import Path


def main():
    with open(Path("p4_out") / "biencoder_report.json", encoding="utf-8") as f:
        br = json.load(f)
    with open(Path("p4_out") / "pretrain_report.json", encoding="utf-8") as f:
        pr = json.load(f)

    lines = [
        "# P4 Report -- Tokenizer, Fracture Engine, Pre-training, Bi-encoder", "",
        "Aggregates all 6 acceptance checks from specs/P4_NEURAL_SPEC.md. Every "
        "number here is copied from its source report (reports/*.md), never "
        "recomputed -- follow the links for full detail, methodology, and caveats.",
        "",
        "## Check 1 -- H1 harness patch", "",
        "Full detail: `reports/h1_patch_report.md`.",
        "",
        "- 5 docID-family pairs found (exhaustive regex sweep, base-form-verified); "
        "6,408 same-family candidate exclusions applied across the full P3 scorer x "
        "task x index-variant re-run.",
        "- 98 exact-dedup groups inspected: 97 are genuine formulaic collisions "
        "(near-empty fragments from unrelated tablets) and correctly stay in "
        "ranking; the 1 that's also a real family match is excluded via the "
        "family mechanism, not a separate rule.",
        "- Patched P3 tables emitted to `results_p3_patched/`.",
        "",
        "## Check 2 -- Sign-level tokenizer (D12)", "",
        "Full detail: `reports/tokenizer_report.md`.",
        "",
        "- **Vocab size: 2,374** (1,022 logogram-class + 1,342 syllabic/other).",
        "- **Dev OOV rate: 0.16%** -- PASS (target <1%).",
        "- Amendment applied and reported honestly: the first attempt (P3's "
        "bm25_sign convention verbatim) landed at vocab=14,170 / OOV=3.66%, "
        "missing both targets -- flagged rather than silently fixed; architect "
        "approved sign-level logogram decomposition (splitting determinative/"
        "Sumerogram/Akkadogram content on real wedge-cluster boundaries), which "
        "fixed both.",
        "- Round-trip fidelity: 5/5 seeded examples exact match, 0 unknown tokens.",
        "- Truncation rate at seq_len=512: 3.82% of fragments.",
        "",
        "## Check 3 -- Fracture engine (D13)", "",
        "Full detail: `reports/fracture_report.md`.",
        "",
        "- 3,333 eligible TRAIN fragments for cut pairs (>=8 lines, >=60 attested "
        "signs); 17,644 eligible for self-supervised views (TRAIN + discovery pool).",
        "- Synthetic-vs-real distribution match shown (not asserted) across "
        "n_lines / n_attested_signs; 10 rendered examples with seam parameters "
        "included in the source report.",
        "- Streaming generator, seeded -- millions of pairs never materialized to "
        "disk; a fixed 2,000-pair dev-diagnostic set is.",
        "",
        "## Check 4 -- Pre-training (D14)", "",
        "Full detail: `reports/pretrain_report.md`.",
        "",
        f"- Final checkpoint: step {pr['checkpoint_step']:,} (all 60,000 configured "
        "steps completed; scheduled task exited cleanly, no crash).",
        f"- Dev MLM loss: 7.85 (step 0) -> {pr['final_dev_eval_fresh']['mlm_loss']:.2f} "
        "(final fresh pass).",
        "- Span-infilling exact-match (SPAN-level, by length band): strong at "
        f"length 1 ({pr['span_exact_by_band']['1']['exact_match_rate']:.1%}), "
        "collapsing to 0% by length 6+ -- reported plainly, not smoothed over.",
        "- Boundary-head AUC by negative type (dev): "
        f"in_doc={pr['boundary_auc_by_tier']['in_doc']['auc']:.3f} (hardest), "
        f"cross_genre={pr['boundary_auc_by_tier']['cross_genre']['auc']:.3f}, "
        f"random={pr['boundary_auc_by_tier']['random']['auc']:.3f} (easiest) -- "
        "matches the intended difficulty curriculum.",
        "- Restoration-agreement (diagnostic only, never a training/eval target): "
        f"token-level {pr['restoration_agreement']['token_agreement_rate']:.1%}, "
        f"span-exact {pr['restoration_agreement']['span_exact_agreement_rate']:.1%} "
        f"over {pr['restoration_agreement']['n_spans']} real editor-restored dev spans.",
        "",
        "## Check 5 -- Bi-encoder (D15)", "",
        "Full detail: `reports/biencoder_report.md`.",
        "",
        f"- Best combo: **{br['best_combo']['mix']} / {br['best_combo']['pooling']}** "
        f"-- real dev-join recall@10 = **{br['best_combo']['recall_at_10']:.3f}**.",
        f"- BM25 dev-join recall@10 baseline: **{br['bm25_real_joins_recall_at_10']:.3f}**.",
        f"- Delta: **{br['delta']:+.3f}**.",
        "",
        "**PRE-REGISTERED SUCCESS CRITERION: NOT MET.** The spec's stated bar for "
        "proceeding to P5 is real dev-join recall@10 *meaningfully above* BM25's -- "
        "the best bi-encoder combo instead lands meaningfully *below* it "
        f"({br['best_combo']['recall_at_10']:.3f} vs {br['bm25_real_joins_recall_at_10']:.3f}). "
        "Both numbers are stated per spec; whether/how to proceed is the judgment "
        "call explicitly reserved for the architect check-in, not decided here. "
        "Duplicates show the same pattern (BM25 ahead on all three mixes), "
        "consistent with CLAUDE.md's own prediction that duplicates are "
        "near-solved by lexical overlap -- but the JOINS gap is the one that "
        "matters for the P5 decision, and it was not anticipated to run this "
        "direction.",
        "",
        "## Check 6 -- Resumability", "",
        "- **D14 (19_pretrain.py): rigorously verified.** Kill + resume tested "
        "against a small config; EVERY row of the resulting loss_curve.csv "
        "matched bit-for-bit against an uninterrupted continuous run (mlm_loss, "
        "boundary_loss, total_loss, dev_mlm_loss, dev_span_exact, dev_boundary_auc "
        "all identical; only wall-clock elapsed_s differed, as expected). Four "
        "real bugs were found and fixed during this testing (not assumed correct "
        "beforehand): local RNG state not saved (only global `random` module "
        "was), one of two save_checkpoint() call sites missed by an edit, an "
        "off-by-one re-executing the checkpointed step on resume, and a CUDA/CPU "
        "RNG-state tensor type mismatch on load.",
        "- **D15 (20_biencoder.py): functionally verified, not bit-identically "
        "verified.** A fresh run followed by `--resume` was confirmed to load "
        "the checkpoint correctly (`Initialized from D14 checkpoint @ pretrain "
        "step 1000` / `Resumed after step N`) and continue without error, "
        "reusing the same save/load pattern already proven correct for D14. The "
        "full row-for-row bit-identical loss-curve comparison specifically was "
        "not repeated for D15 -- flagged honestly as a narrower check than D14's, "
        "not silently equated to it.",
        "",
        "## Overall", "",
        "Checks 1-4 and 6 (D14 half) pass cleanly. **Check 5 is the one that "
        "changes the picture**: the bi-encoder does not clear BM25 on the metric "
        "that was supposed to gate P5. This is reported as a real negative "
        "result, per CLAUDE.md's \"report more, claim less\" -- not reframed as a "
        "partial success. Recommended next discussion with the architect: "
        "whether P5 (edge-continuation scorer) proceeds anyway (P5 reranks a "
        "candidate list the bi-encoder produces, so a weak bi-encoder stage "
        "still constrains what P5 can recover), whether D15 needs another "
        "training round (more steps, different negatives, or a different base "
        "checkpoint), or whether the retrieval stage's design needs to change "
        "before P5 is worth building.",
    ]

    with open("p4_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Done. p4_report.md written.")


if __name__ == "__main__":
    main()
