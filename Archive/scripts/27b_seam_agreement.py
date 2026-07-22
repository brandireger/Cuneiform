#!/usr/bin/env python3
"""
27b_seam_agreement.py -- addendum to D17: "argmax-offset agreement
count" feature for D19's cascade.

Usage:
    python scripts/27b_seam_agreement.py

D17 (27_seam_scorer.py) already found each pair's best (direction,
offset) but didn't persist the full per-offset score list needed to
compute an agreement statistic (only the max was kept, to keep the
main run's memory footprint small). This addendum re-scores just the
4 offsets at each pair's ALREADY-KNOWN argmax_direction (not the full
2-direction x 4-offset search D17 did) -- a quarter of D17's per-pair
cost, since the direction is fixed -- and records
`n_agree_over_half`: how many of those 4 offsets scored a mean
boundary probability > 0.5. This is the seam signal's ROBUSTNESS
across neighboring offsets, not just a single lucky point estimate.
"""
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder
from fracture_engine import get_fragment_tokens

BOUNDARY_WINDOW = 32
BOUNDARY_SEQ_LEN = 64
MAX_OFFSET = 3
D14_CKPT = Path("runs") / "pretrain_base" / "checkpoint.pt"


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
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

    frags_lookup = frags.set_index("fragment_id")
    with open(Path("p4_out") / "p5_d17_scores.json", encoding="utf-8") as f:
        d17_scores = json.load(f)

    line_id, par_id = tok.vocab["<LINE>"], tok.vocab["<PAR>"]
    line_cache = {}

    def get_lines(fid):
        if fid not in line_cache:
            line_cache[fid] = get_fragment_tokens(fid, frags_lookup, line_index, edge_info) if fid in edge_info else []
        return line_cache[fid]

    def build_seq(lead_lines, trail_lines, offset):
        context_full = ht.encode_fragment_window(lead_lines)
        context = context_full[-BOUNDARY_WINDOW:] if context_full else []
        trail_from_offset = trail_lines[offset:] if offset < len(trail_lines) else []
        cont_full = ht.encode_fragment_window(trail_from_offset)
        cont = cont_full[:BOUNDARY_WINDOW]
        if not context or not cont:
            return None
        seq = (context + cont)[:BOUNDARY_SEQ_LEN]
        return tok.encode(seq)

    batch_ids, batch_meta = [], []
    agreement = {}
    t0 = time.time()
    BATCH_LIMIT = 512

    def flush():
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
        for i, (qid, cid, offset) in enumerate(batch_meta):
            positions = [j for j, t in enumerate(batch_ids[i]) if t in (line_id, par_id)]
            if not positions:
                continue
            pos_t = torch.tensor(positions, dtype=torch.long, device=device)
            hid = hidden[i:i + 1].expand(len(positions), -1, -1)
            with torch.no_grad():
                logits = model.boundary_logit(hid, pos_t)
                prob = torch.sigmoid(logits).mean().item()
            agreement.setdefault((qid, cid), []).append(prob > 0.5)
        batch_ids, batch_meta = [], []

    n_pairs = 0
    for qi, (qid, cand_dict) in enumerate(d17_scores.items()):
        q_lines = get_lines(qid)
        for cid, entry in cand_dict.items():
            c_lines = get_lines(cid)
            if not q_lines or not c_lines:
                continue
            direction = entry["argmax_direction"]
            lead_lines, trail_lines = (q_lines, c_lines) if direction == "query_leads" else (c_lines, q_lines)
            n_pairs += 1
            for offset in range(MAX_OFFSET + 1):
                seq = build_seq(lead_lines, trail_lines, offset)
                if seq is not None:
                    batch_ids.append(seq)
                    batch_meta.append((qid, cid, offset))
                    if len(batch_ids) >= BATCH_LIMIT:
                        flush()
        if qi % 100 == 0:
            print(f"  query {qi}/{len(d17_scores)}, elapsed {time.time()-t0:.0f}s")
    flush()

    out = {}
    for (qid, cid), flags in agreement.items():
        out.setdefault(qid, {})[cid] = sum(flags)

    with open(Path("p4_out") / "p5_d17_agreement.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"Done in {time.time()-t0:.0f}s. Pairs: {n_pairs}. p5_d17_agreement.json written.")


if __name__ == "__main__":
    main()
