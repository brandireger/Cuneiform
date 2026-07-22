#!/usr/bin/env python3
"""
25_p5_stratify.py -- P5.0 stratification preliminaries per
specs/P5_RERANK_SPEC.md. ANALYSIS ONLY, run FIRST (gates the rest of
P5's gate definitions).

Usage:
    python scripts/25_p5_stratify.py

1. Tier-stratifies the 182 dev joins (A/B/C) and re-emits P4B's B1 and
   B3 tables with per-tier rows, both index scales.
2. HARD SET: dev joins whose BM25 score to true partner falls in the
   bottom quartile of the 182 -- frozen to p5_hard_set.json.
3. CEILING: fraction of (all, hard set, each tier) whose true partner
   is in BM25 full_distractor top-200.

SCOPE NOTE: uses the SAME whole-fragment (non-exclusive-content)
rendering P4B used for all tiers including C, for direct comparability
with the already-reported 0.835/0.571/etc numbers -- this is a
stratification of the EXISTING measurement, not a re-derivation with
tier-C's honest exclusive-content evaluation (a P3-established, separate
methodology). Flagged here per project convention rather than silently
assumed.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder

SEED = 20260722
BEST_MIX = "real_only"
BEST_TAG = "base"
KS = (1, 10, 100)

_ns = {"__file__": str(Path("scripts/20_biencoder.py").resolve())}
with open("scripts/20_biencoder.py", encoding="utf-8") as _f:
    _src = _f.read().replace('if __name__ == "__main__":\n    main()', "")
exec(compile(_src, "scripts/20_biencoder.py", "exec"), _ns)
load_encoded_pool = _ns["load_encoded_pool"]
filter_join_pairs_by_split = _ns["filter_join_pairs_by_split"]
embed_all_mean = _ns["embed_all_mean"]
embed_all_lines = _ns["embed_all_lines"]


def wilson_ci(hits, n, z=1.96):
    if n == 0:
        return (None, None)
    p = hits / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def recall_at_ks_wilson(ranks, n_queries, ks=KS):
    out = {}
    for k in ks:
        hits = sum(1 for r in ranks if r is not None and r <= k)
        lo, hi = wilson_ci(hits, n_queries)
        out[f"recall@{k}"] = {"mean": hits / n_queries if n_queries else None,
                              "ci_wilson": [lo, hi], "hits": hits, "n": n_queries}
    return out


def ranks_from_scores(scores, cand_ids, query_ids, positives_by_query):
    ranks = []
    for qi, qid in enumerate(query_ids):
        ranked = eh.top_k_ranking(scores[qi], cand_ids, exclude_id=qid)
        positives = positives_by_query.get(qid, set())
        rank = None
        for i, cid in enumerate(ranked):
            if cid in positives:
                rank = i + 1
                break
        ranks.append(rank)
    return ranks


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    OUT = Path("p4_out")

    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    tok = ht.Tokenizer.load()
    with open("configs/biencoder_config.json", encoding="utf-8") as f:
        cfg = json.load(f)

    dev_real = frags[(frags["main_split"] == "dev") & (~frags["is_bin"])]
    test_only_ids = dev_real["fragment_id"].tolist()
    full_distractor = frags[frags["main_split"] != "test"]
    full_distractor_ids = full_distractor["fragment_id"].tolist()
    frags_lookup = frags.set_index("fragment_id")

    join_pairs = eh.build_join_positives(frags)
    dev_joins = filter_join_pairs_by_split(join_pairs, frags, "dev")
    dev_ids_set = set(test_only_ids)
    join_by_frag = defaultdict(set)
    tier_by_pair_members = defaultdict(set)  # fragment_id -> set of tiers it appears in
    for p in dev_joins:
        if p["fragment_id_a"] not in dev_ids_set or p["fragment_id_b"] not in dev_ids_set:
            continue
        join_by_frag[p["fragment_id_a"]].add(p["fragment_id_b"])
        join_by_frag[p["fragment_id_b"]].add(p["fragment_id_a"])
        tier_by_pair_members[p["fragment_id_a"]].add(p["tier"])
        tier_by_pair_members[p["fragment_id_b"]].add(p["tier"])
    query_ids = sorted(join_by_frag.keys())
    join_by_frag = dict(join_by_frag)
    print(f"dev real-join queries: {len(query_ids)}")

    query_tier = {}
    mixed = 0
    for q in query_ids:
        tiers = tier_by_pair_members[q]
        if len(tiers) == 1:
            query_tier[q] = next(iter(tiers))
        else:
            query_tier[q] = "mixed"
            mixed += 1
    print(f"tier distribution: {dict((t, list(query_tier.values()).count(t)) for t in set(query_tier.values()))}, mixed={mixed}")

    query_toks = [json.loads(frags_lookup.loc[q, "sign_attested"]) for q in query_ids]

    print("Scoring BM25 @ test_only and full_distractor...")
    to_toks = [json.loads(s) for s in frags_lookup.loc[test_only_ids, "sign_attested"]]
    bm25_to_scores, _ = eh.bm25_score_matrix(to_toks, query_toks)
    fd_toks = [json.loads(s) for s in frags_lookup.loc[full_distractor_ids, "sign_attested"]]
    bm25_fd_scores, _ = eh.bm25_score_matrix(fd_toks, query_toks)

    bm25_to_ranks = ranks_from_scores(bm25_to_scores, test_only_ids, query_ids, join_by_frag)
    bm25_fd_ranks = ranks_from_scores(bm25_fd_scores, full_distractor_ids, query_ids, join_by_frag)

    # per-query BM25 score to true partner (for hard-set definition), at full_distractor
    bm25_fd_dense = bm25_fd_scores.toarray()
    fd_index = {fid: i for i, fid in enumerate(full_distractor_ids)}
    score_to_true_partner = []
    for qi, qid in enumerate(query_ids):
        positives = join_by_frag.get(qid, set())
        row = bm25_fd_dense[qi]
        best = max((row[fd_index[p]] for p in positives if p in fd_index), default=0.0)
        score_to_true_partner.append(float(best))

    # ---- HARD SET: bottom quartile of BM25 score-to-true-partner ----
    q25 = float(np.percentile(score_to_true_partner, 25))
    hard_set = [qid for qid, s in zip(query_ids, score_to_true_partner) if s <= q25]
    print(f"Hard-set threshold (25th percentile of BM25 score to true partner): {q25:.3f}")
    print(f"Hard-set size: {len(hard_set)} / {len(query_ids)}")

    with open(OUT / "p5_hard_set.json", "w", encoding="utf-8") as f:
        json.dump({
            "definition": "dev joins whose BM25 (sign_attested, full_distractor) score to "
                          "the true partner falls in the bottom quartile of the 182 dev joins",
            "threshold_25th_percentile": q25,
            "n_total": len(query_ids), "n_hard": len(hard_set),
            "hard_set_query_ids": hard_set,
            "seed": SEED,
        }, f, ensure_ascii=False, indent=2)
    print("Hard set frozen -> p4_out/p5_hard_set.json")

    # ---- CEILING: fraction whose true partner is in BM25 full_distractor top-200 ----
    def ceiling_for(qids_subset):
        n = len(qids_subset)
        if n == 0:
            return {"n": 0, "ceiling_at_200": None}
        hits = 0
        for qid in qids_subset:
            qi = query_ids.index(qid)
            rank = bm25_fd_ranks[qi]
            if rank is not None and rank <= 200:
                hits += 1
        return {"n": n, "ceiling_at_200": hits / n, "hits": hits}

    ceilings = {"all": ceiling_for(query_ids), "hard_set": ceiling_for(hard_set)}
    for tier in ("A", "B", "C", "mixed"):
        tier_qids = [q for q in query_ids if query_tier[q] == tier]
        if tier_qids:
            ceilings[f"tier_{tier}"] = ceiling_for(tier_qids)
    with open(OUT / "p5_ceilings.json", "w", encoding="utf-8") as f:
        json.dump(ceilings, f, ensure_ascii=False, indent=2)
    print("Ceilings:", json.dumps(ceilings, indent=2))

    hard_set_ceiling = ceilings["hard_set"]["ceiling_at_200"]
    if hard_set_ceiling is not None and hard_set_ceiling < 0.5:
        print(f"*** FLAG: hard-set ceiling {hard_set_ceiling:.3f} < 0.5 -- D16b promoted "
             "from ablation to requirement per spec. ***")
    else:
        print(f"Hard-set ceiling {hard_set_ceiling:.3f} >= 0.5 -- D16b stays an ablation "
             "(still built and reported, per spec's own D16 section).")

    # ---- dense (real_only/line_max) for per-tier B1 ----
    print(f"Loading {BEST_MIX} checkpoint for per-tier B1...")
    encoded_pool = load_encoded_pool(tok, frags, line_index, edge_info, cfg["seq_len"])
    model = HittiteEncoder(len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
                           cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id).to(device)
    ckpt = torch.load(Path("runs") / f"biencoder_{BEST_TAG}_{BEST_MIX}" / "checkpoint.pt",
                      map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    model.eval()

    fd_ids_encoded = [f for f in full_distractor_ids if f in encoded_pool]
    to_ids_encoded = [f for f in test_only_ids if f in encoded_pool]
    print(f"Embedding {len(fd_ids_encoded)} fragments (mean_pool + line_max)...")
    mean_embs = embed_all_mean(model, fd_ids_encoded, encoded_pool, tok, device, cfg["seq_len"])
    line_embs = embed_all_lines(model, fd_ids_encoded, encoded_pool, tok, device, cfg["seq_len"])

    def dense_ranks_mean(cand_ids, query_ids_):
        cand_mat = np.stack([mean_embs[c] for c in cand_ids])
        q_mat = np.stack([mean_embs[q] for q in query_ids_])
        c_norm = cand_mat / (np.linalg.norm(cand_mat, axis=1, keepdims=True) + 1e-9)
        scores = q_mat @ c_norm.T
        scores = scores / (np.linalg.norm(q_mat, axis=1, keepdims=True) + 1e-9)
        ranks = []
        for qi, qid in enumerate(query_ids_):
            ranked = eh.top_k_ranking(scores[qi], cand_ids, exclude_id=qid)
            positives = join_by_frag.get(qid, set())
            rank = None
            for i, cid in enumerate(ranked):
                if cid in positives:
                    rank = i + 1
                    break
            ranks.append(rank)
        return ranks

    def dense_ranks_line_max(cand_ids, query_ids_):
        cand_arr = [line_embs[c] for c in cand_ids]
        ranks = []
        for qid in query_ids_:
            qlines = line_embs[qid]
            scores = np.full(len(cand_ids), -1.0)
            for ci, clines in enumerate(cand_arr):
                if cand_ids[ci] == qid:
                    continue
                sim = qlines @ clines.T
                scores[ci] = float(sim.max()) if sim.size else -1.0
            ranked = eh.top_k_ranking(scores, cand_ids, exclude_id=qid)
            positives = join_by_frag.get(qid, set())
            rank = None
            for i, cid in enumerate(ranked):
                if cid in positives:
                    rank = i + 1
                    break
            ranks.append(rank)
        return ranks

    print("Dense ranks @ test_only (mean_pool, line_max)...")
    dense_to_mean_ranks = dense_ranks_mean(to_ids_encoded, query_ids)
    dense_to_line_ranks = dense_ranks_line_max(to_ids_encoded, query_ids)
    print("Dense ranks @ full_distractor (mean_pool, line_max) -- slow one...")
    dense_fd_mean_ranks = dense_ranks_mean(fd_ids_encoded, query_ids)
    dense_fd_line_ranks = dense_ranks_line_max(fd_ids_encoded, query_ids)

    # ---- build per-tier B1 and B3 tables ----
    def subset_ranks(ranks, mask_qids):
        idx = [query_ids.index(q) for q in mask_qids]
        return [ranks[i] for i in idx]

    b1_per_tier = {}
    b3_per_tier = {}
    groups = {"all": query_ids, "hard_set": hard_set}
    for tier in ("A", "B", "C", "mixed"):
        tier_qids = [q for q in query_ids if query_tier[q] == tier]
        if tier_qids:
            groups[f"tier_{tier}"] = tier_qids

    for name, qids_subset in groups.items():
        n = len(qids_subset)
        b1_per_tier[name] = {
            "n": n,
            "test_only": {
                "bm25": recall_at_ks_wilson(subset_ranks(bm25_to_ranks, qids_subset), n),
                "dense_mean_pool": recall_at_ks_wilson(subset_ranks(dense_to_mean_ranks, qids_subset), n),
                "dense_line_max": recall_at_ks_wilson(subset_ranks(dense_to_line_ranks, qids_subset), n),
            },
            "full_distractor": {
                "bm25": recall_at_ks_wilson(subset_ranks(bm25_fd_ranks, qids_subset), n),
                "dense_mean_pool": recall_at_ks_wilson(subset_ranks(dense_fd_mean_ranks, qids_subset), n),
                "dense_line_max": recall_at_ks_wilson(subset_ranks(dense_fd_line_ranks, qids_subset), n),
            },
        }
        b3_row = {"test_only": {}, "full_distractor": {}}
        to_sub = subset_ranks(bm25_to_ranks, qids_subset)
        fd_sub = subset_ranks(bm25_fd_ranks, qids_subset)
        for k in (10, 20, 50, 100, 200):
            b3_row["test_only"][f"recall@{k}"] = sum(1 for r in to_sub if r and r <= k) / n if n else None
            b3_row["full_distractor"][f"recall@{k}"] = sum(1 for r in fd_sub if r and r <= k) / n if n else None
        b3_per_tier[name] = b3_row

    with open(OUT / "p5_b1_per_tier.json", "w", encoding="utf-8") as f:
        json.dump(b1_per_tier, f, ensure_ascii=False, indent=2, default=str)
    with open(OUT / "p5_b3_per_tier.json", "w", encoding="utf-8") as f:
        json.dump(b3_per_tier, f, ensure_ascii=False, indent=2, default=str)
    with open(OUT / "p5_query_tier.json", "w", encoding="utf-8") as f:
        json.dump(query_tier, f, ensure_ascii=False, indent=2)

    print("P5.0 done. p5_b1_per_tier.json, p5_b3_per_tier.json, p5_hard_set.json, "
         "p5_ceilings.json, p5_query_tier.json written.")


if __name__ == "__main__":
    main()
