#!/usr/bin/env python3
"""
24_p4b_diagnostics.py -- P4B diagnostics per specs/P4B_DIAGNOSTICS.md.

Usage:
    python scripts/24_p4b_diagnostics.py

ANALYSIS ONLY: zero GPU training hours. Everything here re-embeds
fragments through the ALREADY-TRAINED real_only/line_max checkpoint
(the best combo per biencoder_report.md) and scores with the existing
BM25 infrastructure. Test side touched by nothing (dev-side queries
only; full_distractor candidates draw from train/dev/discovery, never
test -- see build_full_distractor_candidates()).

Writes p4b_report.md with B1-B5 + a branch recommendation (H/R/T).
Recommendation only -- branch SELECTION is a joint call per the spec,
not made here.
"""
import json
import math
import random
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

# reuse 20_biencoder.py's helpers via the established exec-import technique
_ns = {"__file__": str(Path("scripts/20_biencoder.py").resolve())}
with open("scripts/20_biencoder.py", encoding="utf-8") as _f:
    _src = _f.read().replace('if __name__ == "__main__":\n    main()', "")
exec(compile(_src, "scripts/20_biencoder.py", "exec"), _ns)
load_encoded_pool = _ns["load_encoded_pool"]
filter_join_pairs_by_split = _ns["filter_join_pairs_by_split"]
embed_all_mean = _ns["embed_all_mean"]
embed_all_lines = _ns["embed_all_lines"]
pad_batch = _ns["pad_batch"]


# ---------------------------------------------------------------- Wilson CI

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


# ---------------------------------------------------------------- candidate universes

def build_candidate_sets(frags):
    dev_real = frags[(frags["main_split"] == "dev") & (~frags["is_bin"])]
    test_only_ids = dev_real["fragment_id"].tolist()
    # full_distractor: everything EXCEPT test (test side touched by nothing, per
    # engineering law above) -- train + dev + discovery-pool fragments.
    full_distractor = frags[frags["main_split"] != "test"]
    full_distractor_ids = full_distractor["fragment_id"].tolist()
    return dev_real, test_only_ids, full_distractor_ids


def main():
    OUT = Path("p4_out")
    if (OUT / "_p4b_state.npz").exists() and (OUT / "p4b_b1.json").exists():
        print("B1 cache found -- skipping straight to B2-B5.")
        run_b2_to_b5(cached_only=True)
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    tok = ht.Tokenizer.load()
    with open("configs/biencoder_config.json", encoding="utf-8") as f:
        cfg = json.load(f)

    dev_real, test_only_ids, full_distractor_ids = build_candidate_sets(frags)
    print(f"test_only candidates: {len(test_only_ids)}, full_distractor candidates: {len(full_distractor_ids)}")

    # ---- dev real join queries (identical across all B-items) ----
    join_pairs = eh.build_join_positives(frags)
    dev_joins = filter_join_pairs_by_split(join_pairs, frags, "dev")
    join_by_frag = defaultdict(set)
    dev_ids_set = set(test_only_ids)
    for p in dev_joins:
        if p["fragment_id_a"] not in dev_ids_set or p["fragment_id_b"] not in dev_ids_set:
            continue
        join_by_frag[p["fragment_id_a"]].add(p["fragment_id_b"])
        join_by_frag[p["fragment_id_b"]].add(p["fragment_id_a"])
    query_ids = sorted(join_by_frag.keys())
    print(f"dev real-join queries: {len(query_ids)}")

    frags_lookup = frags.set_index("fragment_id")
    query_toks = [json.loads(frags_lookup.loc[q, "sign_attested"]) for q in query_ids]

    # ---- BM25 scoring at both scales ----
    print("Scoring BM25 @ test_only...")
    to_toks = [json.loads(s) for s in frags_lookup.loc[test_only_ids, "sign_attested"]]
    bm25_to_scores, _ = eh.bm25_score_matrix(to_toks, query_toks)

    print("Scoring BM25 @ full_distractor...")
    fd_toks = [json.loads(s) for s in frags_lookup.loc[full_distractor_ids, "sign_attested"]]
    bm25_fd_scores, _ = eh.bm25_score_matrix(fd_toks, query_toks)

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

    bm25_to_ranks = ranks_from_scores(bm25_to_scores, test_only_ids, query_ids, join_by_frag)
    bm25_fd_ranks = ranks_from_scores(bm25_fd_scores, full_distractor_ids, query_ids, join_by_frag)

    print("BM25 test_only recall@10:", sum(1 for r in bm25_to_ranks if r and r <= 10) / len(query_ids))
    print("BM25 full_distractor recall@10:", sum(1 for r in bm25_fd_ranks if r and r <= 10) / len(query_ids))

    # ---- dense (real_only/line_max, the reported-best combo) at both scales ----
    print(f"Loading {BEST_MIX} checkpoint...")
    encoded_pool = load_encoded_pool(tok, frags, line_index, edge_info, cfg["seq_len"])
    model = HittiteEncoder(len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
                           cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id).to(device)
    ckpt = torch.load(Path("runs") / f"biencoder_{BEST_TAG}_{BEST_MIX}" / "checkpoint.pt",
                      map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    model.eval()

    # full_distractor_ids already == encoded_pool's coverage (train+dev+discovery, no test)
    fd_ids_encoded = [f for f in full_distractor_ids if f in encoded_pool]
    print(f"Embedding {len(fd_ids_encoded)} fragments (mean_pool)...")
    mean_embs = embed_all_mean(model, fd_ids_encoded, encoded_pool, tok, device, cfg["seq_len"])
    print(f"Embedding {len(fd_ids_encoded)} fragments (line_max)...")
    line_embs = embed_all_lines(model, fd_ids_encoded, encoded_pool, tok, device, cfg["seq_len"])

    def dense_ranks_mean(cand_ids, query_ids, positives_by_query):
        cand_mat = np.stack([mean_embs[c] for c in cand_ids])
        q_mat = np.stack([mean_embs[q] for q in query_ids])
        scores = q_mat @ (cand_mat / (np.linalg.norm(cand_mat, axis=1, keepdims=True) + 1e-9)).T
        scores = scores / (np.linalg.norm(q_mat, axis=1, keepdims=True) + 1e-9)
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
        return ranks, scores

    def dense_ranks_line_max(cand_ids, query_ids, positives_by_query):
        cand_arr = [line_embs[c] for c in cand_ids]
        ranks = []
        per_query_scores = {}
        for qid in query_ids:
            qlines = line_embs[qid]
            scores = np.full(len(cand_ids), -1.0)
            for ci, clines in enumerate(cand_arr):
                if cand_ids[ci] == qid:
                    continue
                sim = qlines @ clines.T
                scores[ci] = float(sim.max()) if sim.size else -1.0
            per_query_scores[qid] = scores
            ranked = eh.top_k_ranking(scores, cand_ids, exclude_id=qid)
            positives = positives_by_query.get(qid, set())
            rank = None
            for i, cid in enumerate(ranked):
                if cid in positives:
                    rank = i + 1
                    break
            ranks.append(rank)
        return ranks, per_query_scores

    to_ids_encoded = [f for f in test_only_ids if f in encoded_pool]
    print("Dense ranks @ test_only (mean_pool)...")
    dense_to_mean_ranks, _ = dense_ranks_mean(to_ids_encoded, query_ids, join_by_frag)
    print("Dense ranks @ test_only (line_max)...")
    dense_to_line_ranks, dense_to_line_scores = dense_ranks_line_max(to_ids_encoded, query_ids, join_by_frag)
    print("Dense ranks @ full_distractor (mean_pool)...")
    dense_fd_mean_ranks, _ = dense_ranks_mean(fd_ids_encoded, query_ids, join_by_frag)
    print("Dense ranks @ full_distractor (line_max)  -- this is the slow one...")
    dense_fd_line_ranks, dense_fd_line_scores = dense_ranks_line_max(fd_ids_encoded, query_ids, join_by_frag)

    print("Dense(line_max) test_only recall@10:", sum(1 for r in dense_to_line_ranks if r and r <= 10) / len(query_ids))
    print("Dense(line_max) full_distractor recall@10:", sum(1 for r in dense_fd_line_ranks if r and r <= 10) / len(query_ids))

    # ---- B1 table ----
    b1 = {
        "index_variant_of_original_report": "test_only (dev-side-only candidates, n=883) -- "
                                            "matches biencoder_report.md's 0.835/0.571 numbers",
        "test_only": {
            "n_candidates": len(to_ids_encoded),
            "bm25": recall_at_ks_wilson(bm25_to_ranks, len(query_ids)),
            "dense_mean_pool": recall_at_ks_wilson(dense_to_mean_ranks, len(query_ids)),
            "dense_line_max": recall_at_ks_wilson(dense_to_line_ranks, len(query_ids)),
        },
        "full_distractor": {
            "n_candidates": len(fd_ids_encoded),
            "bm25": recall_at_ks_wilson(bm25_fd_ranks, len(query_ids)),
            "dense_mean_pool": recall_at_ks_wilson(dense_fd_mean_ranks, len(query_ids)),
            "dense_line_max": recall_at_ks_wilson(dense_fd_line_ranks, len(query_ids)),
        },
    }

    OUT = Path("p4_out")
    with open(OUT / "p4b_b1.json", "w", encoding="utf-8") as f:
        json.dump(b1, f, ensure_ascii=False, indent=2, default=str)
    print("B1 done -> p4_out/p4b_b1.json")
    print(json.dumps(b1, indent=2, default=str)[:2000])

    # save intermediate state (ranks, scores, embeddings-derived matrices) for B2-B5
    np.savez(OUT / "_p4b_state.npz",
             query_ids=np.array(query_ids, dtype=object),
             fd_ids_encoded=np.array(fd_ids_encoded, dtype=object),
             bm25_fd_ranks=np.array([r if r is not None else -1 for r in bm25_fd_ranks]),
             dense_fd_line_ranks=np.array([r if r is not None else -1 for r in dense_fd_line_ranks]),
             bm25_fd_scores_dense=bm25_fd_scores.toarray(),
             )
    with open(OUT / "_p4b_dense_fd_line_scores.json", "w", encoding="utf-8") as f:
        json.dump({qid: dense_fd_line_scores[qid].tolist() for qid in query_ids}, f)
    print("Saved B2-B5 intermediate state.")

    run_b2_to_b5(cached_only=False, frags=frags, join_by_frag=dict(join_by_frag),
                query_ids=query_ids, fd_ids_encoded=fd_ids_encoded,
                bm25_fd_scores_dense=bm25_fd_scores.toarray(),
                dense_fd_line_scores=dense_fd_line_scores,
                line_index=line_index, edge_info=edge_info, tok=tok, cfg=cfg, device=device)


def rrf_fuse(rank_lists, k=60):
    """rank_lists: list of dict cand_id -> rank (1-indexed) for each ranker.
    Returns dict cand_id -> fused RRF score (higher = better)."""
    scores = defaultdict(float)
    for ranks in rank_lists:
        for cid, r in ranks.items():
            scores[cid] += 1.0 / (k + r)
    return scores


def run_b2_to_b5(cached_only, frags=None, join_by_frag=None, query_ids=None,
                 fd_ids_encoded=None, bm25_fd_scores_dense=None, dense_fd_line_scores=None,
                 line_index=None, edge_info=None, tok=None, cfg=None, device=None):
    OUT = Path("p4_out")
    if cached_only:
        print("Loading cached state...")
        frags, splits, doc_table = eh.load_fragment_universe()
        npz = np.load(OUT / "_p4b_state.npz", allow_pickle=True)
        query_ids = list(npz["query_ids"])
        fd_ids_encoded = list(npz["fd_ids_encoded"])
        with open(OUT / "_p4b_dense_fd_line_scores.json", encoding="utf-8") as f:
            raw = json.load(f)
        dense_fd_line_scores = {k: np.array(v) for k, v in raw.items()}
        # Recompute BM25 scores restricted to EXACTLY fd_ids_encoded (the dense
        # model's candidate set is a strict subset of the cached BM25 scores'
        # candidate set -- min-length filtering in load_encoded_pool drops a
        # few short fragments BM25 still scores -- so the cached
        # bm25_fd_scores_dense array is NOT column-aligned with fd_ids_encoded;
        # recomputing on the identical candidate list is the only safe fix).
        frags_lookup_tmp = frags.set_index("fragment_id")
        fd_toks_tmp = [json.loads(s) for s in frags_lookup_tmp.loc[fd_ids_encoded, "sign_attested"]]
        query_toks_tmp = [json.loads(frags_lookup_tmp.loc[q, "sign_attested"]) for q in query_ids]
        bm25_fd_scores_sparse, _ = eh.bm25_score_matrix(fd_toks_tmp, query_toks_tmp)
        bm25_fd_scores_dense = bm25_fd_scores_sparse.toarray()
        join_pairs = eh.build_join_positives(frags)
        dev_joins = filter_join_pairs_by_split(join_pairs, frags, "dev")
        dev_ids_set = set(frags[(frags["main_split"] == "dev") & (~frags["is_bin"])]["fragment_id"])
        join_by_frag = defaultdict(set)
        for p in dev_joins:
            if p["fragment_id_a"] not in dev_ids_set or p["fragment_id_b"] not in dev_ids_set:
                continue
            join_by_frag[p["fragment_id_a"]].add(p["fragment_id_b"])
            join_by_frag[p["fragment_id_b"]].add(p["fragment_id_a"])
        join_by_frag = dict(join_by_frag)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tok = ht.Tokenizer.load()
        line_index = ht.build_decomposed_line_index()
        edge_info = ht.load_edge_info()
        with open("configs/biencoder_config.json", encoding="utf-8") as f:
            cfg = json.load(f)

    frags_lookup = frags.set_index("fragment_id")

    # ---- B2: complementarity & fusion (full_distractor scale) ----
    print("B2: complementarity & fusion...")
    both_hit = bm25_only = dense_only = neither = 0
    union_hits = 0
    rrf_hits_at1 = rrf_hits_at10 = 0
    for qi, qid in enumerate(query_ids):
        positives = join_by_frag.get(qid, set())
        if not positives:
            continue
        bm25_row = bm25_fd_scores_dense[qi]
        bm25_ranked = eh.top_k_ranking(bm25_row, fd_ids_encoded, exclude_id=qid)
        dense_row = dense_fd_line_scores[qid]
        dense_ranked = eh.top_k_ranking(dense_row, fd_ids_encoded, exclude_id=qid)

        bm25_top10 = set(bm25_ranked[:10])
        dense_top10 = set(dense_ranked[:10])
        bm25_hit = bool(positives & bm25_top10)
        dense_hit = bool(positives & dense_top10)
        if bm25_hit and dense_hit:
            both_hit += 1
        elif bm25_hit:
            bm25_only += 1
        elif dense_hit:
            dense_only += 1
        else:
            neither += 1
        if bm25_hit or dense_hit:
            union_hits += 1

        bm25_rank_map = {cid: i + 1 for i, cid in enumerate(bm25_ranked)}
        dense_rank_map = {cid: i + 1 for i, cid in enumerate(dense_ranked)}
        fused = rrf_fuse([bm25_rank_map, dense_rank_map], k=60)
        fused_ranked = sorted(fused.keys(), key=lambda c: -fused[c])
        rank = None
        for i, cid in enumerate(fused_ranked):
            if cid in positives:
                rank = i + 1
                break
        if rank == 1:
            rrf_hits_at1 += 1
        if rank is not None and rank <= 10:
            rrf_hits_at10 += 1

    n_q = len(query_ids)
    b2 = {
        "hit_set_overlap_at_k10": {"both_hit": both_hit, "bm25_only": bm25_only,
                                    "dense_only": dense_only, "neither": neither, "n": n_q},
        "union_recall_at_10": union_hits / n_q,
        "rrf_k": 60,
        "rrf_recall@1": rrf_hits_at1 / n_q,
        "rrf_recall@10": rrf_hits_at10 / n_q,
    }
    with open(OUT / "p4b_b2.json", "w", encoding="utf-8") as f:
        json.dump(b2, f, indent=2)
    print("B2:", json.dumps(b2, indent=2))

    # ---- B3: BM25 headroom curve (both scales) ----
    print("B3: BM25 headroom curve...")
    npz = np.load(OUT / "_p4b_state.npz", allow_pickle=True)
    bm25_fd_ranks = [int(r) if r >= 0 else None for r in npz["bm25_fd_ranks"]]
    # test_only ranks: recompute quickly (cheap, BM25 only)
    dev_real = frags[(frags["main_split"] == "dev") & (~frags["is_bin"])]
    test_only_ids = dev_real["fragment_id"].tolist()
    to_toks = [json.loads(s) for s in frags_lookup.loc[test_only_ids, "sign_attested"]]
    query_toks = [json.loads(frags_lookup.loc[q, "sign_attested"]) for q in query_ids]
    bm25_to_scores, _ = eh.bm25_score_matrix(to_toks, query_toks)
    bm25_to_ranks = []
    for qi, qid in enumerate(query_ids):
        ranked = eh.top_k_ranking(bm25_to_scores[qi], test_only_ids, exclude_id=qid)
        positives = join_by_frag.get(qid, set())
        rank = None
        for i, cid in enumerate(ranked):
            if cid in positives:
                rank = i + 1
                break
        bm25_to_ranks.append(rank)

    b3 = {"test_only": {}, "full_distractor": {}}
    for k in (10, 20, 50, 100, 200):
        b3["test_only"][f"recall@{k}"] = sum(1 for r in bm25_to_ranks if r and r <= k) / n_q
        b3["full_distractor"][f"recall@{k}"] = sum(1 for r in bm25_fd_ranks if r and r <= k) / n_q
    with open(OUT / "p4b_b3.json", "w", encoding="utf-8") as f:
        json.dump(b3, f, indent=2)
    print("B3:", json.dumps(b3, indent=2))

    # ---- B4: failure taxonomy (full_distractor, BM25 misses at k=10) ----
    print("B4: failure taxonomy...")
    misses, hits = [], []
    for qi, qid in enumerate(query_ids):
        positives = join_by_frag.get(qid, set())
        if not positives:
            continue
        row = bm25_fd_scores_dense[qi]
        ranked = eh.top_k_ranking(row, fd_ids_encoded, exclude_id=qid)
        top10 = set(ranked[:10])
        row_dict = dict(zip(fd_ids_encoded, row))
        best_pos_score = max((row_dict.get(p, 0.0) for p in positives), default=0.0)
        rec = {"qid": qid, "n_attested": int(frags_lookup.loc[qid, "n_attested_signs"]),
              "genre_band": str(frags_lookup.loc[qid, "genre_band"]),
              "bm25_score_to_true_partner": float(best_pos_score)}
        if positives & top10:
            hits.append(rec)
        else:
            misses.append(rec)

    dense_only_qids = set()
    for qid in query_ids:
        positives = join_by_frag.get(qid, set())
        if not positives:
            continue
        bm25_row = bm25_fd_scores_dense[query_ids.index(qid)]
        bm25_ranked = set(eh.top_k_ranking(bm25_row, fd_ids_encoded, exclude_id=qid)[:10])
        dense_ranked = set(eh.top_k_ranking(dense_fd_line_scores[qid], fd_ids_encoded, exclude_id=qid)[:10])
        if not (positives & bm25_ranked) and (positives & dense_ranked):
            dense_only_qids.add(qid)

    def summarize(recs, label):
        if not recs:
            return {"n": 0}
        return {"n": len(recs),
               "mean_n_attested": float(np.mean([r["n_attested"] for r in recs])),
               "mean_bm25_score_to_true_partner": float(np.mean([r["bm25_score_to_true_partner"] for r in recs])),
               "genre_band_dist": dict(sorted(
                   {g: sum(1 for r in recs if r["genre_band"] == g) for g in
                    set(r["genre_band"] for r in recs)}.items()))}

    b4 = {"bm25_hits_at10": summarize(hits, "hits"), "bm25_misses_at10": summarize(misses, "misses"),
         "n_misses_recovered_by_dense_only": len(dense_only_qids & {r["qid"] for r in misses}),
         "n_total_misses": len(misses)}
    with open(OUT / "p4b_b4.json", "w", encoding="utf-8") as f:
        json.dump(b4, f, indent=2, default=str)
    print("B4:", json.dumps(b4, indent=2, default=str))

    # ---- B5: synthetic autopsy ----
    print("B5: synthetic autopsy (loading model fresh for a cheap embed pass)...")
    model = HittiteEncoder(len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
                           cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id).to(device)
    ckpt = torch.load(Path("runs") / f"biencoder_{BEST_TAG}_{BEST_MIX}" / "checkpoint.pt",
                      map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    model.eval()

    synth_pairs = []
    with open(OUT / "fracture_dev_diagnostic.jsonl", encoding="utf-8") as f:
        for line in f:
            synth_pairs.append(json.loads(line))
    print(f"{len(synth_pairs)} synthetic pairs loaded.")

    def embed_token_lists(token_lists, batch_size=64):
        embs = []
        with torch.no_grad():
            for i in range(0, len(token_lists), batch_size):
                chunk = token_lists[i:i + batch_size]
                ids = [tok.encode(t)[:cfg["seq_len"]] for t in chunk]
                max_len = max(len(x) for x in ids)
                padded = pad_batch(ids, tok.pad_id, max_len).to(device)
                emb = model.mean_pool(padded).cpu().numpy()
                embs.append(emb)
        return np.concatenate(embs, axis=0)

    a_toks = [p["member_a_tokens"] for p in synth_pairs]
    b_toks = [p["member_b_tokens"] for p in synth_pairs]
    a_embs = embed_token_lists(a_toks)
    b_embs = embed_token_lists(b_toks)
    a_norm = a_embs / (np.linalg.norm(a_embs, axis=1, keepdims=True) + 1e-9)
    b_norm = b_embs / (np.linalg.norm(b_embs, axis=1, keepdims=True) + 1e-9)
    model_sim_synth = np.sum(a_norm * b_norm, axis=1)

    def jaccard(a, b):
        sa, sb = set(a), set(b)
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    lexical_sim_synth = np.array([jaccard(p["member_a_tokens"], p["member_b_tokens"]) for p in synth_pairs])
    corr_synth = float(np.corrcoef(model_sim_synth, lexical_sim_synth)[0, 1])

    # same correlation for real dev joins (query vs its true partner, mean_pool)
    real_pairs_qids, real_pairs_pids = [], []
    for qid, partners in join_by_frag.items():
        for pid in partners:
            real_pairs_qids.append(qid)
            real_pairs_pids.append(pid)
            break  # one partner per query to avoid double counting symmetric pairs
    q_toks_real = [json.loads(frags_lookup.loc[q, "sign_attested"]) for q in real_pairs_qids]
    p_toks_real = [json.loads(frags_lookup.loc[p, "sign_attested"]) for p in real_pairs_pids]
    q_embs_real = embed_token_lists(q_toks_real)
    p_embs_real = embed_token_lists(p_toks_real)
    q_norm_real = q_embs_real / (np.linalg.norm(q_embs_real, axis=1, keepdims=True) + 1e-9)
    p_norm_real = p_embs_real / (np.linalg.norm(p_embs_real, axis=1, keepdims=True) + 1e-9)
    model_sim_real = np.sum(q_norm_real * p_norm_real, axis=1)
    lexical_sim_real = np.array([jaccard(q, p) for q, p in zip(q_toks_real, p_toks_real)])
    corr_real = float(np.corrcoef(model_sim_real, lexical_sim_real)[0, 1])

    b5 = {"n_synthetic_pairs": len(synth_pairs), "corr_model_vs_lexical_synthetic": corr_synth,
         "n_real_pairs": len(real_pairs_qids), "corr_model_vs_lexical_real": corr_real}
    with open(OUT / "p4b_b5.json", "w", encoding="utf-8") as f:
        json.dump(b5, f, indent=2)
    print("B5:", json.dumps(b5, indent=2))

    print("B2-B5 complete.")


if __name__ == "__main__":
    main()
