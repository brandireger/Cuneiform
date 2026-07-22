#!/usr/bin/env python3
"""
26_retrieve.py -- P5 D16: candidate generation per specs/P5_RERANK_SPEC.md.

Usage:
    python scripts/26_retrieve.py

BM25_sign, full_distractor universe, top-k=200 per query. H1 same-
family exclusions apply. Emitted ONCE, cached, hash-stamped (git
commit + corpus version + config), reused by every reranker (D17,
D18, D19) -- identical candidates for every scorer, no scorer-specific
retrieval.

SCOPE: candidates generated for (a) the 182 real dev-join queries
(primary -- G1/G2/G3), and (b) the 872 dev duplicate queries (G4's
no-regression check). Both draw from the SAME full_distractor
candidate universe and the SAME BM25 index.

D16b (seam-aware lexical ablation): a second BM25 index over EDGE
WINDOWS only (first/last N lines per fragment, N in {3,5}), max
edge-window-to-edge-window score per query-candidate pair. Reports
whether union(whole-fragment top-200, edge-window top-200) raises the
hard-set ceiling -- P5.0 already found the hard-set ceiling (0.696)
clears the 0.5 flag threshold, so D16b stays an ABLATION per spec (not
promoted to a requirement), but is still built and reported here.
"""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht

TOP_K = 200
EDGE_N_VALUES = (3, 5)


def get_git_commit():
    try:
        result = subprocess.run([r"C:\Program Files\Git\bin\git.exe", "rev-parse", "HEAD"],
                                 capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"N/A: {e}"


def build_query_sets(frags):
    join_pairs = eh.build_join_positives(frags)
    dev_ids_set = set(frags[(frags["main_split"] == "dev") & (~frags["is_bin"])]["fragment_id"])
    parent_split = dict(zip(frags["parent_doc"], frags["main_split"]))

    join_by_frag = defaultdict(set)
    for p in join_pairs:
        parent = p["fragment_id_a"].split("::")[0]
        if parent_split.get(parent) != "dev":
            continue
        if p["fragment_id_a"] not in dev_ids_set or p["fragment_id_b"] not in dev_ids_set:
            continue
        join_by_frag[p["fragment_id_a"]].add(p["fragment_id_b"])
        join_by_frag[p["fragment_id_b"]].add(p["fragment_id_a"])

    join_pair_set = {frozenset((p["fragment_id_a"], p["fragment_id_b"])) for p in join_pairs}
    dup_pairs = eh.build_duplicate_positives(frags, join_pair_set, split="dev")
    dup_by_frag = defaultdict(set)
    for p in dup_pairs:
        if p["fragment_id_a"] not in dev_ids_set or p["fragment_id_b"] not in dev_ids_set:
            continue
        dup_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        dup_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])

    return dict(join_by_frag), dict(dup_by_frag)


def build_edge_window_tokens(frags, line_index, edge_info, N):
    """fragment_id -> sign tokens from first N + last N lines only."""
    out = {}
    for row in frags.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        sorted_idxs = sorted(line_idxs)
        edge_idxs = sorted_idxs[:N] + sorted_idxs[-N:] if len(sorted_idxs) > 2 * N else sorted_idxs
        toks = []
        for idx in edge_idxs:
            for t, st in line_index.get((row.parent_doc, idx), []):
                if t not in ht.SPECIALS and st != "restored":
                    toks.append(t)
        out[row.fragment_id] = toks
    return out


def main():
    OUT = Path("p4_out")
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    family_map = eh.build_family_map(frags)

    join_by_frag, dup_by_frag = build_query_sets(frags)
    join_qids = sorted(join_by_frag.keys())
    dup_qids = sorted(dup_by_frag.keys())
    print(f"join queries: {len(join_qids)}, dup queries: {len(dup_qids)}")

    full_distractor = frags[frags["main_split"] != "test"]
    cand_ids = full_distractor["fragment_id"].tolist()
    frags_lookup = frags.set_index("fragment_id")
    cand_toks = [json.loads(s) for s in full_distractor["sign_attested"]]

    all_qids = sorted(set(join_qids) | set(dup_qids))
    query_toks = [json.loads(frags_lookup.loc[q, "sign_attested"]) for q in all_qids]

    print(f"Scoring BM25 (whole-fragment), {len(all_qids)} queries x {len(cand_ids)} candidates...")
    scores, _ = eh.bm25_score_matrix(cand_toks, query_toks)
    cand_families = [eh.fragment_family(c, family_map) for c in cand_ids]

    candidates = {}
    for qi, qid in enumerate(all_qids):
        q_family = eh.fragment_family(qid, family_map)
        ranked = eh.top_k_ranking(scores[qi], cand_ids, exclude_id=qid,
                                  family_map=family_map, query_family=q_family,
                                  candidate_families=cand_families)
        candidates[qid] = ranked[:TOP_K]

    with open(OUT / "p5_candidates_whole.json", "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False)
    print(f"D16 whole-fragment candidates written for {len(candidates)} queries -> "
         "p4_out/p5_candidates_whole.json")

    # ---- D16b: seam-aware edge-window ablation ----
    print("D16b: building edge-window BM25 index...")
    d16b_results = {}
    edge_top200_by_N = {}
    for N in EDGE_N_VALUES:
        edge_toks_all = build_edge_window_tokens(frags, line_index, edge_info, N)
        edge_cand_ids = [c for c in cand_ids if c in edge_toks_all]
        edge_cand_toks = [edge_toks_all[c] for c in edge_cand_ids]
        edge_query_toks = [edge_toks_all.get(q, []) for q in join_qids]
        edge_scores, _ = eh.bm25_score_matrix(edge_cand_toks, edge_query_toks)

        edge_cand_families = [eh.fragment_family(c, family_map) for c in edge_cand_ids]
        union_hits_at200 = 0
        whole_only_ceiling_at200 = 0
        edge_top200_this_N = {}
        for qi, qid in enumerate(join_qids):
            q_family = eh.fragment_family(qid, family_map)
            edge_ranked = eh.top_k_ranking(edge_scores[qi], edge_cand_ids, exclude_id=qid,
                                           family_map=family_map, query_family=q_family,
                                           candidate_families=edge_cand_families)
            edge_top200 = edge_ranked[:TOP_K]
            edge_top200_this_N[qid] = edge_top200
            whole_top200 = set(candidates.get(qid, []))
            positives = join_by_frag.get(qid, set())
            if positives & whole_top200:
                whole_only_ceiling_at200 += 1
            if positives & (whole_top200 | set(edge_top200)):
                union_hits_at200 += 1
        edge_top200_by_N[N] = edge_top200_this_N
        d16b_results[f"N={N}"] = {
            "n_queries": len(join_qids),
            "whole_only_ceiling_at200": whole_only_ceiling_at200 / len(join_qids),
            "union_ceiling_at200": union_hits_at200 / len(join_qids),
            "delta": (union_hits_at200 - whole_only_ceiling_at200) / len(join_qids),
        }
        print(f"  N={N}: whole_only={whole_only_ceiling_at200}/{len(join_qids)}, "
             f"union={union_hits_at200}/{len(join_qids)}")

    with open(OUT / "p5_d16b_report.json", "w", encoding="utf-8") as f:
        json.dump(d16b_results, f, ensure_ascii=False, indent=2)

    # decide promotion: meaningful delta = arbitrary but stated threshold of >=0.02 (2 pts)
    best_N = max(EDGE_N_VALUES, key=lambda N: d16b_results[f"N={N}"]["delta"])
    best_delta = d16b_results[f"N={best_N}"]["delta"]
    promoted = best_delta >= 0.02
    print(f"D16b best delta: {best_delta:.3f} (N={best_N}) -> "
         f"{'PROMOTED to P5 candidate set' if promoted else 'stays ablation-only, whole-fragment candidates remain the P5 candidate set'}")

    if promoted:
        # rebuild the FINAL P5 candidate set as the union (whole-fragment top-200
        # UNION edge-window top-200 at the best N) for join queries specifically;
        # dup queries keep whole-fragment-only (D16b was scoped to joins, per spec).
        for qid in join_qids:
            whole = candidates.get(qid, [])
            edge = edge_top200_by_N[best_N].get(qid, [])
            seen = set(whole)
            merged = list(whole)
            for c in edge:
                if c not in seen:
                    merged.append(c)
                    seen.add(c)
            candidates[qid] = merged
        with open(OUT / "p5_candidates_whole.json", "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False)
        print(f"p5_candidates_whole.json REWRITTEN with the promoted union (N={best_N}) "
             "for join queries.")

    stamp = {
        "git_commit": get_git_commit(), "corpus_version": "TLHdig_0.2.0-beta",
        "top_k": TOP_K, "n_join_queries": len(join_qids), "n_dup_queries": len(dup_qids),
        "n_candidates_universe": len(cand_ids), "d16b_promoted": promoted,
        "d16b_best_delta": best_delta,
    }
    with open(OUT / "p5_d16_stamp.json", "w", encoding="utf-8") as f:
        json.dump(stamp, f, ensure_ascii=False, indent=2)

    with open(OUT / "p5_query_sets.json", "w", encoding="utf-8") as f:
        json.dump({"join_by_frag": {k: list(v) for k, v in join_by_frag.items()},
                  "dup_by_frag": {k: list(v) for k, v in dup_by_frag.items()}}, f, ensure_ascii=False)

    print("D16 done.")


if __name__ == "__main__":
    main()
