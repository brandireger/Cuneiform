#!/usr/bin/env python3
"""
18_fracture.py -- P4 D13: the fracture engine.

Usage:
    python 18_fracture.py

Manufactures labeled join pairs and self-supervised views by breaking
well-preserved TRAIN-side fragments with damage sampled from the
corpus's own measured statistics -- editors nowhere in the loop.

Eligibility: TRAIN-side fragments (>=8 lines, >=60 attested signs) for
cut pairs; TRAIN-side + discovery pool for self-supervised views only
(no cross-fragment relation asserted there, so the leakage concern
that excludes discovery from labeled positives doesn't apply). DEV and
TEST are NEVER used as a fracture-engine source, in either role.

Cut operators:
- VERTICAL: split at a sampled line boundary (top/bottom members),
  optionally deleting a sampled-width whole-line band at the seam
  (gap-join simulation) -- matches tier A/B "vertical" join geometry.
- HORIZONTAL: a per-line column-offset path (jittered around a mean),
  left member keeps signs before the path, right member after,
  optionally eroding a few signs at the seam per line (crumb loss) --
  matches tier C "horizontal" join geometry.
- EROSION: applied to every synthetic member after cutting -- extra
  edge damage + x-substitution at calibrated corpus rates, so
  synthetic members statistically resemble real damaged fragments,
  not perfectly-preserved cut-outs.

Streaming, not materialized: `stream_pairs()` is a generator (seeded)
for D14/D15 to consume directly. A FIXED 2,000-pair dev-diagnostic set
is materialized to fracture_dev_diagnostic.jsonl for inspection only.
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import eval_harness as eh
import hittite_tokenizer as ht
from fracture_engine import (
    SEED, MIN_LINES, MIN_ATTESTED_SIGNS, RESTORED, ILLEGIBLE,
    compute_calibration, get_fragment_tokens, vertical_cut, horizontal_cut,
    erode, render_tokens, member_stats, eligible_fragments, stream_pairs,
)

DEV_DIAGNOSTIC_N = 2000
OUT_DIR = Path("p4_out")


# ---------------------------------------------------------------- main

def main():
    OUT_DIR.mkdir(exist_ok=True)
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    print("Computing calibration...")
    calib = compute_calibration(frags, line_index, edge_info, eh.P2_OUT / "join_pairs.jsonl")
    with open(OUT_DIR / "fracture_calibration.json", "w", encoding="utf-8") as f:
        json.dump(calib, f, ensure_ascii=False, indent=2, default=str)

    eligible_cut = eligible_fragments(frags, edge_info, ["train"])
    eligible_ssl = eligible_cut + [f for f in frags[frags["is_bin"]]["fragment_id"] if f in edge_info]
    print(f"Eligible for cut pairs (TRAIN only): {len(eligible_cut)}")
    print(f"Eligible for self-supervised views (TRAIN+discovery): {len(eligible_ssl)}")

    print(f"Materializing {DEV_DIAGNOSTIC_N} dev-diagnostic cut pairs...")
    gen = stream_pairs(frags, line_index, edge_info, calib, seed=SEED, mode="cut")
    diagnostic_pairs = []
    with open(OUT_DIR / "fracture_dev_diagnostic.jsonl", "w", encoding="utf-8") as f:
        for _ in range(DEV_DIAGNOSTIC_N):
            p = next(gen)
            diagnostic_pairs.append(p)
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # ---- distribution-match: synthetic vs real
    real_n_lines = frags[frags["main_split"] == "train"]["fragment_id"].map(
        lambda f: len(edge_info.get(f, ([],))[0]))
    real_n_signs = frags[frags["main_split"] == "train"]["n_attested_signs"]
    synth_n_lines = [p["member_a_stats"]["n_lines"] for p in diagnostic_pairs] + \
                    [p["member_b_stats"]["n_lines"] for p in diagnostic_pairs]
    synth_n_signs = [p["member_a_stats"]["n_attested_signs"] for p in diagnostic_pairs] + \
                    [p["member_b_stats"]["n_attested_signs"] for p in diagnostic_pairs]

    def pctl_row(real, synth, label):
        r, s = np.asarray(real), np.asarray(synth)
        return (f"| {label} | {r.mean():.1f} | {np.percentile(r,50):.1f} | "
                f"{np.percentile(r,90):.1f} | {s.mean():.1f} | {np.percentile(s,50):.1f} | "
                f"{np.percentile(s,90):.1f} |")

    lines_out = [
        "# P4 D13 -- Fracture Engine Report", "",
        f"- Eligible TRAIN fragments for cut pairs (>= {MIN_LINES} lines, "
        f">= {MIN_ATTESTED_SIGNS} attested signs): **{len(eligible_cut)}**",
        f"- Eligible for self-supervised views (TRAIN + discovery pool): "
        f"**{len(eligible_ssl)}**",
        f"- Dev-diagnostic set materialized: {DEV_DIAGNOSTIC_N} cut pairs "
        f"({OUT_DIR / 'fracture_dev_diagnostic.jsonl'})",
        "- **Generator is streaming/seeded for D14/D15 -- millions of "
        "pairs are never materialized to disk.**",
        "",
        "## Calibration summary (full detail in fracture_calibration.json)", "",
        f"- Del-span length: mean={calib['del_span_length']['mean']:.1f}, "
        f"median={calib['del_span_length']['median']:.1f}, "
        f"p90={calib['del_span_length']['p90']:.1f} signs "
        f"(n={calib['del_span_length']['n_spans']:,} spans)",
        f"- Top edge lost rate: {calib['top_edge_lost_rate']:.1%}, "
        f"bottom edge lost rate: {calib['bottom_edge_lost_rate']:.1%}",
        f"- Illegible-x rate (of non-restored signs): "
        f"{calib['illegible_x_rate_of_nonrestored']:.2%}",
        f"- Left edge state distribution: {calib['left_edge_state_dist']}",
        f"- Right edge state distribution: {calib['right_edge_state_dist']}",
        f"- Real seam geometry share (from join tiers): {calib['real_seam_geometry_share']}",
        f"- **Note on vertical gap width**: {calib['vertical_seam_n_shared_lines_dist_NOTE']}",
        "",
        "## Distribution-match: synthetic vs real (shown, not asserted)", "",
        "| metric | real mean | real p50 | real p90 | synth mean | synth p50 | synth p90 |",
        "|---|---|---|---|---|---|---|",
        pctl_row(real_n_lines, synth_n_lines, "n_lines"),
        pctl_row(real_n_signs, synth_n_signs, "n_attested_signs"),
        "",
        "## 10 rendered examples (before/after, both members, seam params)", "",
    ]

    rng = random.Random(SEED)
    sample_examples = rng.sample(diagnostic_pairs, 10)
    for i, p in enumerate(sample_examples, 1):
        lines_out.append(f"### Example {i}/10 -- source `{p['source_fragment_id']}`, "
                         f"{p['params']['cut_type']} cut")
        lines_out.append(f"- params: {json.dumps(p['params'], default=str)}")
        lines_out.append(f"- member_a ({p['member_a_stats']}): "
                         f"`{' '.join(p['member_a_tokens'][:40])}`")
        lines_out.append(f"- member_b ({p['member_b_stats']}): "
                         f"`{' '.join(p['member_b_tokens'][:40])}`")
        lines_out.append("")

    with open("fracture_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print("Done. fracture_calibration.json + fracture_report.md + "
          "fracture_dev_diagnostic.jsonl written.")


if __name__ == "__main__":
    main()
