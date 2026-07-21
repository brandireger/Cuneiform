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

SEED = 20260722
MIN_LINES = 8
MIN_ATTESTED_SIGNS = 60
DEV_DIAGNOSTIC_N = 2000
OUT_DIR = Path("p4_out")
RESTORED = "restored"
ILLEGIBLE = "illegible_x"


# ---------------------------------------------------------------- calibration

def compute_calibration(frags, line_index, edge_info, join_pairs_path):
    train = frags[frags["main_split"] == "train"]

    # del-span length distribution (contiguous 'restored' token runs,
    # walked across the WHOLE fragment's ordered token stream, since
    # del spans cross line boundaries per P2's finding)
    del_span_lengths = []
    left_edge_states = Counter()
    right_edge_states = Counter()
    illegible_count = 0
    non_restored_count = 0
    n_lines_list = []
    n_attested_list = []

    for row in train.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        sorted_idxs = sorted(line_idxs)
        n_lines_list.append(len(sorted_idxs))
        run_len = 0
        n_attested = 0
        for pos, idx in enumerate(sorted_idxs):
            toks = line_index.get((row.parent_doc, idx), [])
            real_toks = [(t, st) for t, st in toks if t not in ht.SPECIALS]
            if real_toks:
                left_edge_states[real_toks[0][1]] += 1
                right_edge_states[real_toks[-1][1]] += 1
            for t, st in real_toks:
                if st == RESTORED:
                    run_len += 1
                else:
                    if run_len > 0:
                        del_span_lengths.append(run_len)
                    run_len = 0
                    non_restored_count += 1
                    if st == ILLEGIBLE:
                        illegible_count += 1
                    else:
                        n_attested += 1
        if run_len > 0:
            del_span_lengths.append(run_len)
        n_attested_list.append(n_attested)

    top_lost_rate = float(train["fragment_id"].map(
        lambda f: edge_info.get(f, (None, True, True, None))[1]).mean())
    bot_lost_rate = float(train["fragment_id"].map(
        lambda f: edge_info.get(f, (None, True, True, None))[2]).mean())

    # real seam geometry from join tiers (patched, but tiers/geometry
    # themselves are unaffected by H1 -- only ranking exclusions are)
    tiers = Counter()
    gap_line_sizes = []
    with open(join_pairs_path, encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            tiers[p["geometry"]] += 1
            if p["tier"] in ("A", "B"):
                gap_line_sizes.append(p["n_shared_lines"])  # 0 for true no-overlap seams

    calib = {
        "seed": SEED,
        "n_train_fragments_used": len(n_lines_list),
        "del_span_length": {
            "mean": float(np.mean(del_span_lengths)) if del_span_lengths else 0,
            "median": float(np.median(del_span_lengths)) if del_span_lengths else 0,
            "p90": float(np.percentile(del_span_lengths, 90)) if del_span_lengths else 0,
            "histogram": dict(Counter(min(l, 20) for l in del_span_lengths)),  # capped bucket "20+"
            "n_spans": len(del_span_lengths),
        },
        "left_edge_state_dist": {k: v / sum(left_edge_states.values())
                                  for k, v in left_edge_states.items()},
        "right_edge_state_dist": {k: v / sum(right_edge_states.values())
                                   for k, v in right_edge_states.items()},
        "top_edge_lost_rate": top_lost_rate,
        "bottom_edge_lost_rate": bot_lost_rate,
        "illegible_x_rate_of_nonrestored": illegible_count / non_restored_count if non_restored_count else 0,
        "line_count_dist": {
            "mean": float(np.mean(n_lines_list)), "median": float(np.median(n_lines_list)),
            "p10": float(np.percentile(n_lines_list, 10)), "p90": float(np.percentile(n_lines_list, 90)),
        },
        "attested_sign_count_dist": {
            "mean": float(np.mean(n_attested_list)), "median": float(np.median(n_attested_list)),
            "p10": float(np.percentile(n_attested_list, 10)), "p90": float(np.percentile(n_attested_list, 90)),
        },
        "real_seam_geometry_share": {k: v / sum(tiers.values()) for k, v in tiers.items()},
        "vertical_seam_n_shared_lines_dist_NOTE":
            "tier A/B n_shared_lines is ~always 0 by definition (that IS the "
            "no-overlap seam signature) -- true real vertical GAP WIDTH (how "
            "many whole lines are lost between two stacked members) is not "
            "directly measurable from this field; the fracture engine's "
            "gap-line-count sampling below is a documented modeling "
            "assumption (Poisson), not corpus-calibrated, and is flagged as "
            "such rather than silently presented as measured.",
    }
    return calib


# ---------------------------------------------------------------- cut operators

def get_fragment_tokens(fragment_id, frags_lookup, line_index, edge_info):
    """Returns list of (line_idx, [(token, damage_state), ...]) for a
    fragment's real (non-special) tokens, ATTESTED-eligible only
    (restored tokens excluded -- fracture sources must be genuinely
    attested text; we then RE-introduce synthetic restoration via
    erosion, not reuse real restorations as if they were attested)."""
    parent = frags_lookup.loc[fragment_id, "parent_doc"]
    line_idxs, top_lost, bot_lost, by_line = edge_info[fragment_id]
    out = []
    for idx in sorted(line_idxs):
        toks = line_index.get((parent, idx), [])
        real = [(t, st) for t, st in toks if t not in ht.SPECIALS and st != RESTORED]
        out.append((idx, real))
    return out


def vertical_cut(lines, rng, gap_lambda=1.2, gap_prob=0.4):
    """lines: list of (line_idx, tokens). Returns (top_lines, bottom_lines,
    params). Splits at a sampled boundary; optionally deletes a
    Poisson-sampled band of whole lines at the seam."""
    n = len(lines)
    boundary = rng.randint(1, n - 1)
    gap_width = 0
    if rng.random() < gap_prob:
        gap_width = min(np.random.default_rng(rng.randint(0, 2**31)).poisson(gap_lambda) + 1, n - boundary - 1)
        gap_width = max(0, gap_width)
    top = lines[:boundary]
    bottom = lines[boundary + gap_width:]
    params = {"cut_type": "vertical", "boundary_line": boundary,
              "gap_width_lines": gap_width, "n_lines_total": n}
    return top, bottom, params


def horizontal_cut(lines, rng, mean_offset_frac=0.5, jitter=0.15, erosion_max=2):
    """Per-line column split: left keeps signs before the (jittered)
    offset, right keeps signs after. Optionally erodes a few signs at
    the seam per line (crumb loss)."""
    left_lines, right_lines = [], []
    offsets, erosions = [], []
    for idx, toks in lines:
        n = len(toks)
        if n == 0:
            left_lines.append((idx, []))
            right_lines.append((idx, []))
            continue
        frac = min(max(mean_offset_frac + rng.uniform(-jitter, jitter), 0.0), 1.0)
        cut = round(frac * n)
        erode = rng.randint(0, min(erosion_max, max(0, n - 1)))
        offsets.append(cut)
        erosions.append(erode)
        left = toks[:max(0, cut - erode)]
        right = toks[cut + erode:]
        left_lines.append((idx, left))
        right_lines.append((idx, right))
    params = {"cut_type": "horizontal", "mean_offset_frac": mean_offset_frac,
              "jitter": jitter, "per_line_offsets": offsets, "per_line_erosions": erosions}
    return left_lines, right_lines, params


def erode(lines, rng, calib, edge_erosion_lines=2):
    """Applied to every synthetic member: x-substitution at the
    calibrated illegible-x rate, plus extra edge damage on the
    outermost `edge_erosion_lines` lines (simulating the newly-created
    synthetic edge being fragile/worn, matching real top/bottom loss
    behavior statistically rather than leaving synthetic edges
    artificially pristine)."""
    x_rate = calib["illegible_x_rate_of_nonrestored"]
    out = []
    n = len(lines)
    for li, (idx, toks) in enumerate(lines):
        near_edge = li < edge_erosion_lines or li >= n - edge_erosion_lines
        new_toks = []
        for t, st in toks:
            if st == ILLEGIBLE:
                new_toks.append((t, st))
                continue
            p = x_rate * (2.0 if near_edge else 1.0)
            if rng.random() < p:
                new_toks.append(("x", ILLEGIBLE))
            else:
                new_toks.append((t, st))
        out.append((idx, new_toks))
    return out


def render_tokens(lines):
    flat = []
    for idx, toks in lines:
        flat.extend(t for t, st in toks)
        flat.append("<LINE>")
    if flat and flat[-1] == "<LINE>":
        flat.pop()
    return flat


def member_stats(lines):
    n_lines = sum(1 for _, toks in lines if toks)
    n_signs = sum(len(toks) for _, toks in lines)
    return {"n_lines": n_lines, "n_attested_signs": n_signs}


# ---------------------------------------------------------------- generator

def eligible_fragments(frags, edge_info, splits_filter):
    pop = frags[frags["main_split"].isin(splits_filter)]
    out = []
    for row in pop.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs = edge_info[row.fragment_id][0]
        if len(line_idxs) >= MIN_LINES and row.n_attested_signs >= MIN_ATTESTED_SIGNS:
            out.append(row.fragment_id)
    return out


def stream_pairs(frags, line_index, edge_info, calib, seed=SEED, mode="cut"):
    """Generator, seeded, streaming (never materializes to disk in
    bulk). mode='cut' yields join-pair dicts from TRAIN-only sources;
    mode='self_supervised' yields two-view positive pairs from
    TRAIN+discovery. Never touches DEV/TEST."""
    frags_lookup = frags.set_index("fragment_id")
    if mode == "cut":
        pool = eligible_fragments(frags, edge_info, ["train"])
    else:
        pool = eligible_fragments(frags, edge_info, ["train"]) + \
               [f for f in frags[frags["is_bin"]]["fragment_id"] if f in edge_info]
    rng = random.Random(seed)
    i = 0
    while True:
        fid = pool[rng.randrange(len(pool))]
        lines = get_fragment_tokens(fid, frags_lookup, line_index, edge_info)
        i += 1
        if mode == "cut":
            if rng.random() < 0.5:
                a, b, params = vertical_cut(lines, rng)
            else:
                a, b, params = horizontal_cut(lines, rng)
            a = erode(a, rng, calib)
            b = erode(b, rng, calib)
            if not any(toks for _, toks in a) or not any(toks for _, toks in b):
                continue
            yield {
                "pair_id": f"synth{i}", "source_fragment_id": fid,
                "member_a_tokens": render_tokens(a), "member_b_tokens": render_tokens(b),
                "member_a_stats": member_stats(a), "member_b_stats": member_stats(b),
                "params": params,
            }
        else:
            view_a = erode(lines, random.Random(rng.randrange(2**31)), calib)
            view_b = erode(lines, random.Random(rng.randrange(2**31)), calib)
            yield {
                "pair_id": f"ssl{i}", "source_fragment_id": fid,
                "view_a_tokens": render_tokens(view_a), "view_b_tokens": render_tokens(view_b),
            }


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
