#!/usr/bin/env python3
"""
28_edge_continuation.py -- P5 D18: short-horizon edge-continuation
score per specs/P5_RERANK_SPEC.md.

Usage:
    python scripts/28_edge_continuation.py

PMI-style continuation lift at the seam: mask the first H signs of the
candidate's seam-adjacent line, score the model's probability of the
candidate's actual signs GIVEN the query context vs GIVEN a null
context. H <= 5 HARD CAP (D14 measured span-infilling collapse at
length 6+ -- do not spend compute past the measured horizon). Reports
per-H results for H in {1, 3, 5}.

DESIGN (spec describes the objective; mechanics documented here per
this project's practice):
  - Reuses D17's argmax (direction, offset) per (query, candidate)
    pair -- the seam geometry D17's offset search already found best
    -- rather than an independent second search (saves substantial
    compute; the two scorers evaluate the SAME hypothesized seam,
    which is what D19's cascade actually needs to combine).
  - with-context sequence: last `WINDOW` tokens of the leading
    fragment (query context) + H <MASK> tokens (the candidate's first
    H real signs at the found offset) + up to `WINDOW` further REAL
    candidate tokens as right-context (matching D14's trained
    bidirectional-span-infilling expectation -- a masked span embedded
    in real surrounding text, not dangling at a sequence's end).
  - null-context sequence: the SAME masked span + right-context, but
    with NO query context prepended -- isolates the candidate
    continuation's own prior predictability from what the query
    context specifically adds.
  - lift = mean log P(true token | with-context) - mean log P(true
    token | null-context), averaged over the H masked positions.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder
from fracture_engine import get_fragment_tokens

WINDOW = 32
H_VALUES = (1, 3, 5)
MAX_H = 5
D14_CKPT = Path("runs") / "pretrain_base" / "checkpoint.pt"


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    tok = ht.Tokenizer.load()
    with open("configs/pretrain_config.json", encoding="utf-8") as f:
        pretrain_cfg = json.load(f)

    model = HittiteEncoder(len(tok.vocab), pretrain_cfg["d_model"], pretrain_cfg["n_layers"],
                           pretrain_cfg["n_heads"], pretrain_cfg["d_ff"], pretrain_cfg["seq_len"],
                           pretrain_cfg["dropout"], tok.pad_id).to(device)
    ckpt = torch.load(D14_CKPT, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    model.eval()
    print(f"Loaded D14 checkpoint @ step {ckpt['step']} (FROZEN)")

    frags_lookup = frags.set_index("fragment_id")
    with open(Path("p4_out") / "p5_d17_scores.json", encoding="utf-8") as f:
        d17_scores = json.load(f)
    print(f"D17 scores loaded for {len(d17_scores)} queries")

    mask_id = tok.vocab["<MASK>"]
    line_cache = {}

    def get_lines(fid):
        if fid not in line_cache:
            line_cache[fid] = get_fragment_tokens(fid, frags_lookup, line_index, edge_info) if fid in edge_info else []
        return line_cache[fid]

    def build_pair_seqs(lead_lines, trail_lines, offset, H):
        """Returns (with_ctx_ids, null_ctx_ids, true_ids, mask_positions_with, mask_positions_null)
        or None if not enough content."""
        context_full = ht.encode_fragment_window(lead_lines)
        context = context_full[-WINDOW:] if context_full else []
        trail_from_offset = ht.encode_fragment_window(trail_lines[offset:]) if offset < len(trail_lines) else []
        if len(trail_from_offset) < H:
            return None
        true_toks = trail_from_offset[:H]
        right_ctx = trail_from_offset[H:H + WINDOW]
        true_ids = tok.encode(true_toks)

        with_ctx_seq = context + ["<MASK>"] * H + right_ctx
        null_ctx_seq = ["<MASK>"] * H + right_ctx
        with_ids = tok.encode(with_ctx_seq)
        null_ids = tok.encode(null_ctx_seq)
        with_mask_pos = list(range(len(context), len(context) + H))
        null_mask_pos = list(range(0, H))
        return with_ids, null_ids, true_ids, with_mask_pos, null_mask_pos

    results = {}
    total_pairs = 0
    t0 = time.time()
    BATCH_LIMIT = 256
    batch_ids, batch_meta = [], []  # meta: (qid, cid, H, which['with'/'null'], mask_positions, true_ids)

    def flush(accum):
        nonlocal batch_ids, batch_meta
        if not batch_ids:
            return
        max_len = max(len(s) for s in batch_ids)
        padded = torch.full((len(batch_ids), max_len), tok.pad_id, dtype=torch.long)
        for i, ids in enumerate(batch_ids):
            padded[i, :len(ids)] = torch.tensor(ids, dtype=torch.long)
        padded = padded.to(device)
        with torch.no_grad():
            hidden = model.encode(padded)
            logits = model.mlm_logits(hidden)
            log_probs = F.log_softmax(logits, dim=-1)
        for i, (qid, cid, H, which, mask_positions, true_ids) in enumerate(batch_meta):
            lp_sum = 0.0
            for pos, tid in zip(mask_positions, true_ids):
                lp_sum += log_probs[i, pos, tid].item()
            mean_lp = lp_sum / len(true_ids) if true_ids else 0.0
            accum.setdefault((qid, cid, H), {})[which] = mean_lp
        batch_ids, batch_meta = [], []

    qi_count = 0
    for qid, cand_dict in d17_scores.items():
        q_lines = get_lines(qid)
        if not q_lines:
            continue
        for cid, d17_entry in cand_dict.items():
            c_lines = get_lines(cid)
            if not c_lines:
                continue
            direction = d17_entry["argmax_direction"]
            offset = d17_entry["argmax_offset"]
            lead_lines, trail_lines = (q_lines, c_lines) if direction == "query_leads" else (c_lines, q_lines)
            total_pairs += 1
            for H in H_VALUES:
                built = build_pair_seqs(lead_lines, trail_lines, offset, H)
                if built is None:
                    continue
                with_ids, null_ids, true_ids, with_pos, null_pos = built
                batch_ids.append(with_ids); batch_meta.append((qid, cid, H, "with", with_pos, true_ids))
                batch_ids.append(null_ids); batch_meta.append((qid, cid, H, "null", null_pos, true_ids))
                if len(batch_ids) >= BATCH_LIMIT:
                    flush(results)
        qi_count += 1
        if qi_count % 50 == 0:
            print(f"  query {qi_count}/{len(d17_scores)}, elapsed {time.time()-t0:.0f}s")
    flush(results)

    # aggregate into per-pair, per-H lift
    lifts = {}
    for (qid, cid, H), vals in results.items():
        if "with" in vals and "null" in vals:
            lift = vals["with"] - vals["null"]
            lifts.setdefault(qid, {}).setdefault(cid, {})[str(H)] = lift

    with open(Path("p4_out") / "p5_d18_scores.json", "w", encoding="utf-8") as f:
        json.dump(lifts, f, ensure_ascii=False)

    # per-H summary table
    all_lifts_by_H = {H: [] for H in H_VALUES}
    for qid, cd in lifts.items():
        for cid, hd in cd.items():
            for H in H_VALUES:
                if str(H) in hd:
                    all_lifts_by_H[H].append(hd[str(H)])
    summary = {H: {"n": len(v), "mean_lift": float(np.mean(v)) if v else None,
                   "median_lift": float(np.median(v)) if v else None}
              for H, v in all_lifts_by_H.items()}
    with open(Path("p4_out") / "p5_d18_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"D18 done in {time.time()-t0:.0f}s. Pairs: {total_pairs}. "
         f"Confirmed no H > {MAX_H} was run.")
    print("Summary:", json.dumps(summary, indent=2))
    print("p4_out/p5_d18_scores.json + p5_d18_summary.json written.")


if __name__ == "__main__":
    main()
