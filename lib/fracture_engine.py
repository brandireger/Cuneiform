#!/usr/bin/env python3
"""
fracture_engine.py -- P4 D13: the fracture engine (reusable module).

Extracted from 18_fracture.py (same digit-prefix import restriction as
eval_harness.py/hittite_tokenizer.py) so 19_pretrain.py and
20_biencoder.py can import the cut operators and streaming generator
directly, instead of duplicating them. 18_fracture.py now imports from
here for its CLI/report role.

See 18_fracture.py's module docstring for the full design rationale
(calibrated cut operators, erosion, streaming-not-materialized).

D15 EXTENSION: stream_pairs()/eligible_fragments() now accept a
`split` argument ('train' for actual training data, 'dev' for the
"synthetic held-out joins" dev gate -- generated the same way but from
DEV-side fragments, NEVER used for gradient updates, only evaluation).
"""

import json
import random
from collections import Counter

import numpy as np

import hittite_tokenizer as ht

SEED = 20260722
MIN_LINES = 8
MIN_ATTESTED_SIGNS = 60
RESTORED = "restored"
ILLEGIBLE = "illegible_x"


# ---------------------------------------------------------------- calibration

def compute_calibration(frags, line_index, edge_info, join_pairs_path):
    train = frags[frags["main_split"] == "train"]

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

    tiers = Counter()
    with open(join_pairs_path, encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            tiers[p["geometry"]] += 1

    calib = {
        "seed": SEED,
        "n_train_fragments_used": len(n_lines_list),
        "del_span_length": {
            "mean": float(np.mean(del_span_lengths)) if del_span_lengths else 0,
            "median": float(np.median(del_span_lengths)) if del_span_lengths else 0,
            "p90": float(np.percentile(del_span_lengths, 90)) if del_span_lengths else 0,
            "histogram": dict(Counter(
                min(length, 20) for length in del_span_lengths)),
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
            "no-overlap seam signature) -- true real vertical GAP WIDTH is not "
            "directly measurable from this field; the fracture engine's "
            "gap-line-count sampling is a documented Poisson modeling "
            "assumption, not corpus-calibrated.",
    }
    return calib


# ---------------------------------------------------------------- cut operators

def get_fragment_tokens(fragment_id, frags_lookup, line_index, edge_info):
    parent = frags_lookup.loc[fragment_id, "parent_doc"]
    line_idxs, top_lost, bot_lost, by_line = edge_info[fragment_id]
    out = []
    for idx in sorted(line_idxs):
        toks = line_index.get((parent, idx), [])
        real = [(t, st) for t, st in toks if t not in ht.SPECIALS and st != RESTORED]
        out.append((idx, real))
    return out


def vertical_cut(lines, rng, gap_lambda=1.2, gap_prob=0.4):
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
        erode_n = rng.randint(0, min(erosion_max, max(0, n - 1)))
        offsets.append(cut)
        erosions.append(erode_n)
        left = toks[:max(0, cut - erode_n)]
        right = toks[cut + erode_n:]
        left_lines.append((idx, left))
        right_lines.append((idx, right))
    params = {"cut_type": "horizontal", "mean_offset_frac": mean_offset_frac,
              "jitter": jitter, "per_line_offsets": offsets, "per_line_erosions": erosions}
    return left_lines, right_lines, params


def erode(lines, rng, calib, edge_erosion_lines=2):
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


def stream_pairs(frags, line_index, edge_info, calib, seed=SEED, mode="cut", split="train"):
    """Generator, seeded, streaming. mode='cut' yields join-pair dicts;
    mode='self_supervised' yields two-view positive pairs (TRAIN+
    discovery only, regardless of `split`, since self-supervised views
    assert no cross-fragment relation). split='train' (actual training
    data) or split='dev' (D15's synthetic held-out joins dev gate --
    same mechanics, DEV-side source fragments, NEVER used for gradient
    updates)."""
    frags_lookup = frags.set_index("fragment_id")
    if mode == "cut":
        pool = eligible_fragments(frags, edge_info, [split])
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
