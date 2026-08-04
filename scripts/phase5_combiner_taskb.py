#!/usr/bin/env python3
"""Does the BM25 + frozen CANINE combiner help Task B, and where?

    python scripts/phase5_combiner_taskb.py

Executes `reports/phase5_combiner_taskb_protocol.md` (PRE-REGISTERED
2026-08-04, committed before this run). Training-free; dev split only.

The Task A combiner (+0.0462) says nothing about pairwise matching, which is
where the shipping system actually runs. AGENTS.md's standing decision
requires the full three-way matrix -- joins-only, duplicates-only, pooled --
for every model, so all three are reported here whatever they say.

Everything is imported rather than reimplemented: the fragment loader from
the screen, the fold assignment / alpha grid / paired bootstrap from the Task
A combiner, and the ranking from `eval_harness.run_retrieval`'s
`precomputed_scores` path.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_harness as eh  # noqa: E402

_screen = __import__("phase5_ladder_screen")
_comb = __import__("phase5_bm25_combiner")

OUT = Path("Phase4/phase4_out/p5_combiner_taskb.json")
KS = (1, 5, 10, 100)


def build_positives(rows):
    """joins / duplicates / pooled, restricted to the dev fragment set.

    Join membership is a property of the physical object, so a join pair is
    dev-side when its parent document is -- `build_join_positives` exposes
    only a test_side flag, so dev membership is derived from the fragment set
    itself rather than by reading that flag."""
    frags, _splits, _doc = eh.load_fragment_universe()
    ids = {r["fragment_id"] for r in rows}

    join_pairs = eh.build_join_positives(frags)
    join_pair_set = {frozenset((p["fragment_id_a"], p["fragment_id_b"]))
                     for p in join_pairs}
    joins = {}
    n_join_pairs = 0
    for p in join_pairs:
        a, b = p["fragment_id_a"], p["fragment_id_b"]
        if a in ids and b in ids:
            joins.setdefault(a, set()).add(b)
            joins.setdefault(b, set()).add(a)
            n_join_pairs += 1

    dups = {}
    n_dup_pairs = 0
    for p in eh.build_duplicate_positives(frags, join_pair_set, split="dev"):
        a, b = p["fragment_id_a"], p["fragment_id_b"]
        if a in ids and b in ids:
            dups.setdefault(a, set()).add(b)
            dups.setdefault(b, set()).add(a)
            n_dup_pairs += 1

    pooled = {}
    for src in (joins, dups):
        for q, s in src.items():
            pooled.setdefault(q, set()).update(s)

    return ({"joins": joins, "duplicates": dups, "pooled": pooled},
            {"n_join_pairs": n_join_pairs, "n_duplicate_pairs": n_dup_pairs,
             "n_join_queries": len(joins), "n_duplicate_queries": len(dups),
             "n_pooled_queries": len(pooled)})


def retrieve(rows, scores, positives, query_idx=None):
    ids = [r["fragment_id"] for r in rows]
    toks = [r["tokens"] for r in rows]
    qi = list(range(len(rows))) if query_idx is None else list(query_idx)
    return eh.run_retrieval(
        [ids[i] for i in qi], [toks[i] for i in qi], ids, toks,
        positives, ks=KS,
        precomputed_scores=np.asarray(scores)[qi, :])


def correct(per_query, k=1):
    return {r["query_id"]: r[f"recall@{k}"] for r in per_query}


def fit_and_evaluate(rows, zb, zc, fold_of, positives, base_correct):
    """Same fold discipline as Task A: alpha fit on queries from other folds,
    applied to this fold's. Ties resolve to the smallest alpha."""
    held_out, per_fold = {}, []
    for f in range(_comb.N_FOLDS):
        fit_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] != f]
        ev_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] == f]
        best_a, best_r = None, -1.0
        for a in _comb.ALPHA_GRID:
            _pq, agg = retrieve(rows, zb + a * zc, positives, fit_idx)
            r = agg["recall@1"]["mean"] or 0.0
            if r > best_r + 1e-12:
                best_a, best_r = a, r
        pq_ev, agg_ev = retrieve(rows, zb + best_a * zc, positives, ev_idx)
        held_out.update({r["query_id"]: r for r in pq_ev})
        per_fold.append({"fold": f, "alpha_selected": best_a,
                         "fit_recall@1": best_r,
                         "n_eval_queries": agg_ev["n"],
                         "held_out_recall@1": agg_ev["recall@1"]["mean"]})
    return held_out, per_fold


def cell_result(held_out, base_per_query, label):
    base_c = {r["query_id"]: r for r in base_per_query}
    common = sorted(set(held_out) & set(base_c))
    out = {"label": label, "n_paired": len(common)}
    for k in (1, 10):
        d = np.array([held_out[q][f"recall@{k}"] - base_c[q][f"recall@{k}"]
                      for q in common], float)
        lo, hi = _comb.paired_bootstrap(d) if len(d) else (None, None)
        out[f"recall@{k}"] = {
            "combiner": float(np.mean([held_out[q][f"recall@{k}"] for q in common]))
            if common else None,
            "bm25": float(np.mean([base_c[q][f"recall@{k}"] for q in common]))
            if common else None,
            "delta": float(d.mean()) if len(d) else None,
            "delta_ci95": [lo, hi],
            "ci_excludes_zero": bool(lo is not None and (lo > 0.0 or hi < 0.0)),
            "n_gained": int((d > 0).sum()), "n_lost": int((d < 0).sum()),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signal", default="canine", choices=["canine", "char"],
                    help="which side signal to combine with BM25. 'char' is "
                         "the classical character n-gram control, added after "
                         "it beat CANINE on Task A by 2.5x "
                         "(reports/phase5_char_ngram_control_results.md)")
    args = ap.parse_args()

    print("Loading dev fragments (test never loaded)...")
    rows = _screen.load_dev_fragments()
    fold_of, load = _comb.assign_folds(rows)
    print(f"dev fragments: {len(rows)}, fold query loads: {load}")

    positives, counts = build_positives(rows)
    print("positives:", json.dumps(counts))

    bm25 = eh.bm25_score_matrix([r["tokens"] for r in rows],
                                [r["tokens"] for r in rows])[0].toarray()
    zb = _comb.znorm_rows(bm25)

    if args.signal == "char":
        # (4,6) was selected in all five Task A folds; fixed here rather than
        # refitted, so the Task B run tests transfer of a settled
        # configuration instead of searching a second time.
        _ngram = __import__("phase5_char_ngram_control")
        signal_name = "char_ngram_tfidf_4_6"
        zc = _comb.znorm_rows(_ngram.char_similarity(rows, (4, 6)))
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        cand = next(c for c in _screen.CANDIDATES if c["name"] == _comb.PRIMARY)
        cache = Path("Phase4/phase4_out/p5_combiner_embeddings.npz")
        if cache.exists() and np.load(cache)[_comb.PRIMARY].shape[0] == len(rows):
            print(f"  reusing cached {_comb.PRIMARY} embeddings")
            vecs = np.load(cache)[_comb.PRIMARY]
        else:
            vecs = _screen.embed(rows, cand, device)
        signal_name = _comb.PRIMARY
        zc = _comb.znorm_rows(_screen.cosine_matrix(vecs))

    result = {
        "protocol": "reports/phase5_combiner_taskb_protocol.md "
                    "(PRE-REGISTERED 2026-08-04, committed before this run)",
        "training_free": True,
        "split": "dev only; dev-only candidate index; test never loaded",
        "candidate": signal_name,
        "n_dev_fragments": len(rows), "positive_counts": counts,
        "cells": {},
    }
    out_path = (OUT if args.signal == "canine"
                else OUT.with_name("p5_combiner_taskb_char.json"))

    for label in ("joins", "duplicates", "pooled"):
        pos = positives[label]
        if not pos:
            print(f"\n== {label}: NO POSITIVES in the dev fragment set ==")
            result["cells"][label] = {"label": label, "n_paired": 0,
                                      "note": "no positives"}
            continue
        print(f"\n== {label} ==")
        pq_base, agg_base = retrieve(rows, bm25, pos)
        print(f"  BM25 recall@1 {agg_base['recall@1']['mean']:.4f} "
              f"recall@10 {agg_base['recall@10']['mean']:.4f} (n={agg_base['n']})")
        held_out, per_fold = fit_and_evaluate(rows, zb, zc, fold_of, pos,
                                              correct(pq_base))
        cell = cell_result(held_out, pq_base, label)
        cell["per_fold"] = per_fold
        cell["bm25_full"] = {"recall@1": agg_base["recall@1"]["mean"],
                             "recall@10": agg_base["recall@10"]["mean"],
                             "mrr": agg_base["mrr"]["mean"], "n": agg_base["n"]}
        result["cells"][label] = cell
        for k in (1, 10):
            c = cell[f"recall@{k}"]
            print(f"  recall@{k}: combiner {c['combiner']:.4f} vs BM25 "
                  f"{c['bm25']:.4f}  delta {c['delta']:+.4f} "
                  f"CI [{c['delta_ci95'][0]:+.4f}, {c['delta_ci95'][1]:+.4f}] "
                  f"(+{c['n_gained']}/-{c['n_lost']})")
        print(f"  alphas by fold: {[d['alpha_selected'] for d in per_fold]}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nwritten to {out_path}")


if __name__ == "__main__":
    main()
