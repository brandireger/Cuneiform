#!/usr/bin/env python3
"""
27_seam_scorer.py -- P5 D17: boundary-head reranking per
specs/P5_RERANK_SPEC.md. FROZEN D14 head only (no fine-tuning in this
script -- that's the conditional D17b).

Usage:
    python scripts/27_seam_scorer.py

DESIGN (spec describes the objective, not the exact mechanics --
documented here per this project's practice of stating scope
decisions rather than guessing silently):

For each (query, candidate) pair from D16's candidate cache, score
BOTH vertical-join directions (query-bottom-meets-candidate-top, and
the reverse) at a small set of line-offsets (0..MAX_OFFSET, simulating
an unknown-size gap per CLAUDE.md's seam-scoring design commitment --
"never assume contiguity"). For each (direction, offset):
  - context = last `boundary_window` (32) tokens of the leading
    fragment's ATTESTED sequence, ending at its own last <LINE>/
    <EDGE_B> position where possible.
  - continuation = first `boundary_window` tokens of the trailing
    fragment's ATTESTED sequence, taken AFTER skipping `offset`
    leading lines (the gap simulation).
  - seq = context + continuation, truncated to boundary_seq_len (64).
  - "mean over aligned line-pairs at that offset": ALL <LINE>/<PAR>
    positions within this constructed window are scored with D14's
    frozen boundary_logit head and averaged -- not just the single
    exact seam point -- operationalizing multi-row consistency at a
    fixed offset without assuming exact abutment.
Aggregate per pair: MAX over (direction, offset) of that mean. The
argmax (direction, offset) is emitted alongside -- this is the demo's
placement / P7's assignment evidence.

Truncation rate on seam sequences is reported (should be tiny -- seams
are local by design, per spec).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder
from fracture_engine import get_fragment_tokens

BOUNDARY_WINDOW = 32
BOUNDARY_SEQ_LEN = 64
MAX_OFFSET = 3  # offsets 0..3 candidate leading-lines skipped (gap simulation)
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
    print(f"Loaded D14 checkpoint @ step {ckpt['step']} (FROZEN -- no fine-tuning here)")

    frags_lookup = frags.set_index("fragment_id")

    with open(Path("p4_out") / "p5_candidates_whole.json", encoding="utf-8") as f:
        candidates = json.load(f)
    with open(Path("p4_out") / "p5_query_sets.json", encoding="utf-8") as f:
        query_sets = json.load(f)
    join_qids = sorted(query_sets["join_by_frag"].keys())
    dup_qids = sorted(query_sets["dup_by_frag"].keys())
    all_qids = join_qids + [q for q in dup_qids if q not in set(join_qids)]
    print(f"{len(join_qids)} join queries + {len(dup_qids)} dup queries "
         f"({len(all_qids)} unique), candidate list sizes range "
         f"{min(len(v) for v in candidates.values())}-{max(len(v) for v in candidates.values())}")

    line_id, par_id = tok.vocab["<LINE>"], tok.vocab["<PAR>"]
    line_cache = {}

    def get_lines(fid):
        if fid not in line_cache:
            if fid not in edge_info:
                line_cache[fid] = []
            else:
                line_cache[fid] = get_fragment_tokens(fid, frags_lookup, line_index, edge_info)
        return line_cache[fid]

    def build_seq(lead_lines, trail_lines, offset):
        context_full = ht.encode_fragment_window(lead_lines)
        context = context_full[-BOUNDARY_WINDOW:] if context_full else []
        trail_from_offset = trail_lines[offset:] if offset < len(trail_lines) else []
        cont_full = ht.encode_fragment_window(trail_from_offset)
        cont = cont_full[:BOUNDARY_WINDOW]
        if not context or not cont:
            return None
        seq = context + cont
        seq = seq[:BOUNDARY_SEQ_LEN]
        return tok.encode(seq)

    total_pairs = 0
    truncated = 0
    all_scores = {}  # qid -> {cid: {"score": float, "argmax": [dir, offset]}}
    t0 = time.time()
    batch_seqs, batch_meta = [], []  # meta: (qid, cid, direction, offset)
    BATCH_LIMIT = 512

    def flush_batch(results_accum):
        nonlocal batch_seqs, batch_meta
        if not batch_seqs:
            return
        max_len = max(len(s) for s in batch_seqs)
        padded = torch.full((len(batch_seqs), max_len), tok.pad_id, dtype=torch.long)
        for i, ids in enumerate(batch_seqs):
            padded[i, :len(ids)] = torch.tensor(ids, dtype=torch.long)
        padded = padded.to(device)
        with torch.no_grad():
            hidden = model.encode(padded)
        for i, (qid, cid, direction, offset) in enumerate(batch_meta):
            ids = padded[i, :len(batch_seqs[i])]
            positions = [j for j, t in enumerate(batch_seqs[i]) if t in (line_id, par_id)]
            if not positions:
                continue
            pos_t = torch.tensor(positions, dtype=torch.long, device=device)
            hid = hidden[i:i + 1].expand(len(positions), -1, -1)
            with torch.no_grad():
                logits = model.boundary_logit(hid, pos_t)
                probs = torch.sigmoid(logits).mean().item()
            key = (qid, cid)
            results_accum.setdefault(key, []).append((direction, offset, probs))
        batch_seqs, batch_meta = [], []

    pair_results = {}
    for qi, qid in enumerate(all_qids):
        q_lines = get_lines(qid)
        if not q_lines:
            continue
        for cid in candidates.get(qid, []):
            c_lines = get_lines(cid)
            if not c_lines:
                continue
            total_pairs += 1
            for offset in range(MAX_OFFSET + 1):
                seq_fwd = build_seq(q_lines, c_lines, offset)  # query leads, candidate trails
                if seq_fwd is not None:
                    batch_seqs.append(seq_fwd)
                    batch_meta.append((qid, cid, "query_leads", offset))
                seq_rev = build_seq(c_lines, q_lines, offset)  # candidate leads, query trails
                if seq_rev is not None:
                    batch_seqs.append(seq_rev)
                    batch_meta.append((qid, cid, "candidate_leads", offset))
                if len(batch_seqs) >= BATCH_LIMIT:
                    flush_batch(pair_results)
        if qi % 50 == 0:
            print(f"  query {qi}/{len(all_qids)}, elapsed {time.time()-t0:.0f}s")
    flush_batch(pair_results)

    for (qid, cid), entries in pair_results.items():
        best = max(entries, key=lambda e: e[2])
        all_scores.setdefault(qid, {})[cid] = {
            "score": best[2], "argmax_direction": best[0], "argmax_offset": best[1],
            "n_offsets_scored": len(entries),
        }

    with open(Path("p4_out") / "p5_d17_scores.json", "w", encoding="utf-8") as f:
        json.dump(all_scores, f, ensure_ascii=False)

    n_seqs = len(batch_meta) + sum(1 for _ in pair_results)  # rough
    print(f"D17 done in {time.time()-t0:.0f}s. Pairs scored: {total_pairs}. "
         f"Queries with scores: {len(all_scores)}.")
    print("p4_out/p5_d17_scores.json written.")


if __name__ == "__main__":
    main()
