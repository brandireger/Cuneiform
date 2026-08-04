#!/usr/bin/env python3
"""Does BM25 + a frozen pretrained candidate beat BM25 alone?

    python scripts/phase5_bm25_combiner.py [--skip-joint]

Executes `reports/phase5_bm25_combiner_protocol.md` (PRE-REGISTERED
2026-08-04, committed before this run). Training-free: no gradients are
computed anywhere in this file, and the only quantity fit is a scalar mixing
coefficient, by grid search, over embeddings the ratified withdrawn-rung
screen already produces.

The screen left the interesting question answered only by an ORACLE -- a
perfect per-query selector reaching 0.7214 against BM25's 0.6312 for CANINE.
This measures how much of that a real combiner recovers.

Three constraints carried over from the screen, all enforced here:

1. **One ranking implementation.** Every arm -- BM25, combiner, RRF -- goes
   through `eval_harness.run_task_a`'s `precomputed_scores` path, so
   leave-one-out exclusions and composition ranking are literally the same
   code. Reimplementing that ranking is the E2 pattern.
2. **One fragment loader.** `phase5_ladder_screen.load_dev_fragments` is
   imported, not copied, so this runs on exactly the screen's query set.
3. **alpha = 0 is in the grid**, so the combiner family strictly contains the
   BM25 baseline, and an identity control asserts it reproduces BM25's
   per-query records exactly before any number is reported.

Dev split only; test is never loaded.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import evidence_policy as ep  # noqa: E402
import eval_harness as eh  # noqa: E402

_screen = __import__("phase5_ladder_screen")

OUT_DIR = Path("Phase4/phase4_out")
OUT = OUT_DIR / "p5_bm25_combiner.json"
MANIFEST = OUT_DIR / "p5_bm25_combiner_manifest.json"
EMB_CACHE = OUT_DIR / "p5_combiner_embeddings.npz"

REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")
EVIDENCE_POLICY = "catalog_assisted"
SEMANTIC_FIELDS = ["token", "damage_state", "cth"]

# --- pre-registered constants; do not adjust after seeing results ---------
ALPHA_GRID = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0]
N_FOLDS = 5
RRF_K = 60
DECISION_MARGIN = 0.010
PRIMARY = "google/canine-s"
SECONDARY = "xlm-roberta-base"


# ------------------------------------------------------------------ scoring

def znorm_rows(M):
    """Per-query z-normalization across candidates. Strictly monotone within
    a row, so it cannot change either input's own ranking -- it only puts two
    incomparable scales into one additive space."""
    M = np.asarray(M, dtype=np.float64)
    mu = M.mean(axis=1, keepdims=True)
    sd = M.std(axis=1, keepdims=True)
    return (M - mu) / np.clip(sd, 1e-12, None)


INELIGIBLE = -1e18


def rrf_matrix(bm25, cos, parent_doc, k=RRF_K):
    """Reciprocal rank fusion, with ranks taken WITHIN each query's eligible
    pool.

    Ranking the full pool and letting `run_task_a` mask afterwards would not
    be equivalent: excluded candidates sit at different depths in the two
    lists, so removing them shifts ranks by different amounts in each, and
    RRF's sum of reciprocals is not invariant to that. Ineligible entries get
    a large negative constant; `run_task_a` applies the identical
    same-parent_doc mask, so their value is never read.
    """
    parent = np.asarray(parent_doc)
    out = np.full(bm25.shape, INELIGIBLE, dtype=np.float64)
    for i in range(bm25.shape[0]):
        idx = np.flatnonzero(parent != parent[i])
        if idx.size == 0:
            continue
        pos = np.arange(1, idx.size + 1)
        rb = np.empty(idx.size, dtype=np.int64)
        rb[np.argsort(-bm25[i, idx], kind="stable")] = pos
        rc = np.empty(idx.size, dtype=np.int64)
        rc[np.argsort(-cos[i, idx], kind="stable")] = pos
        out[i, idx] = 1.0 / (k + rb) + 1.0 / (k + rc)
    return out


def run_subset(rows, scores, query_idx):
    """Task A over a query subset against the FULL candidate pool."""
    ids = [r["fragment_id"] for r in rows]
    toks = [r["tokens"] for r in rows]
    parent = [r["parent_doc"] for r in rows]
    cth = [r["cth"] for r in rows]
    qi = list(query_idx)
    return eh.run_task_a(
        [ids[i] for i in qi], [toks[i] for i in qi],
        [parent[i] for i in qi], [cth[i] for i in qi],
        ids, toks, parent, cth,
        precomputed_scores=np.asarray(scores)[qi, :])


def records_by_query(per_query):
    return {r["query_id"]: r for r in per_query}


def correct_by_query(per_query_or_records, k=1):
    if isinstance(per_query_or_records, dict):
        return {q: r[f"recall@{k}"] for q, r in per_query_or_records.items()}
    return {r["query_id"]: r[f"recall@{k}"] for r in per_query_or_records}


# ------------------------------------------------------------------- folds

def assign_folds(rows, n_folds=N_FOLDS):
    """Composition-level folds, greedily balanced by QUERY count (not by
    composition count), deterministic. Only the query set is partitioned --
    the candidate pool stays whole, because a query must be able to retrieve
    its sibling witnesses. The only fitted quantity is alpha, and alpha for a
    fold never sees that fold's queries."""
    counts = {}
    for r in rows:
        counts[r["cth"]] = counts.get(r["cth"], 0) + 1
    load = [0] * n_folds
    fold_of = {}
    for cth in sorted(counts, key=lambda c: (-counts[c], str(c))):
        f = int(np.argmin(load))
        fold_of[cth] = f
        load[f] += counts[cth]
    return fold_of, load


# -------------------------------------------------------------- statistics

def aggregate_records(records):
    """Pooled recall@1/@5/MRR over held-out per-query records, through the
    harness's own aggregator so the CI construction matches every other
    reported number in the project."""
    agg = eh.aggregate_metrics(list(records.values()), ks=(1, 5, 10))
    return {"recall@1": agg["recall@1"]["mean"], "recall@1_ci": agg["recall@1"]["ci"],
            "recall@5": agg["recall@5"]["mean"], "mrr": agg["mrr"]["mean"],
            "n": agg["n"]}


def paired_bootstrap(delta, reps=eh.BOOTSTRAP_REPS, seed=eh.SEED):
    """CI on the mean per-query difference. Resamples QUERIES, keeping each
    query's (combiner, baseline) pair together -- the arms are correlated and
    an unpaired interval would be far too wide."""
    arr = np.asarray(delta, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(arr)
    means = np.empty(reps)
    for i in range(reps):
        means[i] = arr[rng.integers(0, n, n)].mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def compare(combined_correct, base_correct):
    common = sorted(set(combined_correct) & set(base_correct))
    d = np.array([combined_correct[q] - base_correct[q] for q in common], float)
    lo, hi = paired_bootstrap(d)
    return {
        "n_paired": len(common),
        "combiner_recall@1": float(np.mean([combined_correct[q] for q in common])),
        "bm25_recall@1": float(np.mean([base_correct[q] for q in common])),
        "delta": float(d.mean()),
        "delta_ci95": [lo, hi],
        "ci_excludes_zero": bool(lo > 0.0 or hi < 0.0),
        "n_gained": int((d > 0).sum()),
        "n_lost": int((d < 0).sum()),
    }


# ------------------------------------------------------------------ arms

def fit_alpha(rows, zb, zc, fit_idx):
    """Grid search on the FIT queries only. Ties resolve to the smallest
    alpha, so a tie favours BM25 alone."""
    best_a, best_r = None, -1.0
    curve = []
    for a in ALPHA_GRID:
        _pq, agg = run_subset(rows, zb + a * zc, fit_idx)
        r = agg["recall@1"]["mean"] or 0.0
        curve.append({"alpha": a, "fit_recall@1": r})
        if r > best_r + 1e-12:
            best_a, best_r = a, r
    return best_a, best_r, curve


def linear_combiner(rows, zb, zc, fold_of, label, base_correct):
    held_out, fit_set, per_fold = {}, {}, []
    for f in range(N_FOLDS):
        fit_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] != f]
        ev_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] == f]
        a, fit_r, curve = fit_alpha(rows, zb, zc, fit_idx)
        pq_ev, agg_ev = run_subset(rows, zb + a * zc, ev_idx)
        pq_fit, _ = run_subset(rows, zb + a * zc, fit_idx)
        held_out.update(records_by_query(pq_ev))
        fit_set.update(correct_by_query(pq_fit))
        # per-fold delta against BM25 on this fold's own queries, so a pooled
        # gain cannot be an average hiding one fold doing all the work.
        fold_c = correct_by_query(pq_ev)
        fold_d = [fold_c[q] - base_correct[q] for q in fold_c if q in base_correct]
        per_fold.append({
            "fold": f, "n_fit_queries": len(fit_idx), "n_eval_queries": len(ev_idx),
            "alpha_selected": a, "fit_recall@1": fit_r,
            "held_out_recall@1": agg_ev["recall@1"]["mean"],
            "held_out_delta_vs_bm25": float(np.mean(fold_d)) if fold_d else None,
            "alpha_curve": curve,
        })
        print(f"    fold {f}: alpha*={a:<5} fit={fit_r:.4f} "
              f"held-out={agg_ev['recall@1']['mean']:.4f} "
              f"(delta {np.mean(fold_d):+.4f}, n={agg_ev['n']})")
    pooled = aggregate_records(held_out)
    return ({"label": label, "per_fold": per_fold,
             "held_out_pooled": pooled,
             "alpha_constant_across_folds": len(
                 {d["alpha_selected"] for d in per_fold}) == 1},
            held_out, fit_set)


def joint_combiner(rows, zb, zc1, zc2, fold_of):
    held_out, per_fold = {}, []
    for f in range(N_FOLDS):
        fit_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] != f]
        ev_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] == f]
        best, best_r = (0.0, 0.0), -1.0
        for a1 in ALPHA_GRID:
            for a2 in ALPHA_GRID:
                _pq, agg = run_subset(rows, zb + a1 * zc1 + a2 * zc2, fit_idx)
                r = agg["recall@1"]["mean"] or 0.0
                if r > best_r + 1e-12:
                    best, best_r = (a1, a2), r
        a1, a2 = best
        pq_ev, agg_ev = run_subset(rows, zb + a1 * zc1 + a2 * zc2, ev_idx)
        held_out.update(records_by_query(pq_ev))
        per_fold.append({"fold": f, "alpha_canine": a1, "alpha_xlmr": a2,
                         "fit_recall@1": best_r,
                         "held_out_recall@1": agg_ev["recall@1"]["mean"]})
        print(f"    fold {f}: a_canine={a1:<5} a_xlmr={a2:<5} "
              f"fit={best_r:.4f} held-out={agg_ev['recall@1']['mean']:.4f}")
    return {"label": "joint_canine_xlmr", "per_fold": per_fold}, held_out


def rrf(rows, bm25, cos, all_idx):
    scores = rrf_matrix(bm25, cos, [r["parent_doc"] for r in rows])
    pq, agg = run_subset(rows, scores, all_idx)
    return correct_by_query(pq), agg


# ------------------------------------------------------------------- main

def embeddings(rows, device, use_cache=True):
    names = [PRIMARY, SECONDARY]
    if use_cache and EMB_CACHE.exists():
        z = np.load(EMB_CACHE)
        if all(n in z for n in names) and z[names[0]].shape[0] == len(rows):
            print(f"  reusing cached embeddings from {EMB_CACHE}")
            return {n: z[n] for n in names}
    out = {}
    for cand in _screen.CANDIDATES:
        if cand["name"] not in names:
            continue
        print(f"  embedding {cand['name']} (frozen, no grads) ...")
        out[cand["name"]] = _screen.embed(rows, cand, device)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(EMB_CACHE, **out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-joint", action="store_true",
                    help="skip the declared secondary joint fit (no decision weight)")
    args = ap.parse_args()

    print("Loading dev fragments (test never loaded)...")
    rows = _screen.load_dev_fragments()
    all_idx = list(range(len(rows)))
    fold_of, load = assign_folds(rows)
    n_comps = len({r["cth"] for r in rows})
    print(f"dev fragments: {len(rows)}, compositions: {n_comps}, "
          f"fold query loads: {load}")

    print("\n== BM25 reference ==")
    bm25_sparse, _ = eh.bm25_score_matrix([r["tokens"] for r in rows],
                                          [r["tokens"] for r in rows])
    bm25 = bm25_sparse.toarray()
    pq_base, agg_base = run_subset(rows, bm25, all_idx)
    base_correct = correct_by_query(pq_base)
    print(f"  recall@1 {agg_base['recall@1']['mean']:.4f} (n={agg_base['n']})")

    # --- identity control: the combiner family must contain the baseline ---
    zb = znorm_rows(bm25)
    pq_z, agg_z = run_subset(rows, zb, all_idx)
    if correct_by_query(pq_z) != base_correct:
        raise SystemExit(
            "IDENTITY CONTROL FAILED: z-normalized BM25 does not reproduce "
            "BM25's per-query records. Row normalization must be monotone "
            "within a query; every downstream number would be void.")
    print(f"  identity control PASSED (alpha=0 reproduces BM25 exactly, "
          f"n={agg_z['n']})")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n== Frozen embeddings (device {device}) ==")
    vecs = embeddings(rows, device)
    zc = {n: znorm_rows(_screen.cosine_matrix(v)) for n, v in vecs.items()}

    result = {
        "protocol": "reports/phase5_bm25_combiner_protocol.md "
                    "(PRE-REGISTERED 2026-08-04, committed before this run)",
        "training_free": True,
        "split": "dev only; test never loaded",
        "n_dev_fragments": len(rows), "n_compositions": n_comps,
        "n_folds": N_FOLDS, "alpha_grid": ALPHA_GRID, "rrf_k": RRF_K,
        "decision_margin": DECISION_MARGIN,
        "fold_query_loads": load,
        "bm25_reference": {
            "recall@1": agg_base["recall@1"]["mean"],
            "recall@1_ci": agg_base["recall@1"]["ci"],
            "recall@5": agg_base["recall@5"]["mean"],
            "mrr": agg_base["mrr"]["mean"], "n": agg_base["n"],
        },
        "identity_control_passed": True,
        "arms": {},
    }

    for name in (PRIMARY, SECONDARY):
        print(f"\n== Linear combiner: BM25 + {name} ==")
        detail, held_out, fit_set = linear_combiner(
            rows, zb, zc[name], fold_of, name, base_correct)
        cmp_ho = compare(correct_by_query(held_out), base_correct)
        cmp_fit = compare(fit_set, base_correct)
        print(f"  HELD-OUT  recall@1 {cmp_ho['combiner_recall@1']:.4f} vs BM25 "
              f"{cmp_ho['bm25_recall@1']:.4f}  delta {cmp_ho['delta']:+.4f} "
              f"CI {cmp_ho['delta_ci95']}")
        print(f"  fit-set   recall@1 {cmp_fit['combiner_recall@1']:.4f} "
              f"(transfer gap {cmp_fit['delta'] - cmp_ho['delta']:+.4f}"
              f"{'; UNINFORMATIVE, alpha constant across folds' if detail['alpha_constant_across_folds'] else ''})")

        rrf_correct, rrf_agg = rrf(rows, bm25, _screen.cosine_matrix(vecs[name]), all_idx)
        cmp_rrf = compare(rrf_correct, base_correct)
        print(f"  RRF (k={RRF_K}, unfitted) recall@1 "
              f"{cmp_rrf['combiner_recall@1']:.4f} delta {cmp_rrf['delta']:+.4f} "
              f"CI {cmp_rrf['delta_ci95']}")

        result["arms"][name] = {
            "linear": {**detail, "held_out_vs_bm25": cmp_ho,
                       "fit_set_vs_bm25": cmp_fit,
                       "transfer_gap": cmp_fit["delta"] - cmp_ho["delta"]},
            "rrf": {**cmp_rrf, "recall@5": rrf_agg["recall@5"]["mean"],
                    "mrr": rrf_agg["mrr"]["mean"]},
        }

    if not args.skip_joint:
        print("\n== Joint combiner: BM25 + CANINE + XLM-R (secondary, "
              "no decision weight) ==")
        detail, held_out = joint_combiner(rows, zb, zc[PRIMARY], zc[SECONDARY], fold_of)
        detail["held_out_pooled"] = aggregate_records(held_out)
        cmp_j = compare(correct_by_query(held_out), base_correct)
        print(f"  HELD-OUT recall@1 {cmp_j['combiner_recall@1']:.4f} "
              f"delta {cmp_j['delta']:+.4f} CI {cmp_j['delta_ci95']}")
        result["arms"]["joint_canine_xlmr"] = {
            "linear": {**detail, "held_out_vs_bm25": cmp_j}}

    # --- the pre-registered rule, applied to the primary only -------------
    primary = result["arms"][PRIMARY]["linear"]["held_out_vs_bm25"]
    realizable = (primary["ci_excludes_zero"] and primary["delta"] > 0
                  and primary["delta"] >= DECISION_MARGIN)
    result["decision"] = {
        "primary_candidate": PRIMARY,
        "clause_1_ci_excludes_zero": primary["ci_excludes_zero"],
        "clause_2_delta_at_least_margin": bool(primary["delta"] >= DECISION_MARGIN),
        "verdict": "REALIZABLE" if realizable else "NOT_REALIZABLE",
    }
    print(f"\n== PRE-REGISTERED VERDICT: {result['decision']['verdict']} ==")
    print(f"   clause 1 (CI excludes zero): {primary['ci_excludes_zero']}")
    print(f"   clause 2 (delta >= {DECISION_MARGIN}): "
          f"{primary['delta']:.4f} -> {primary['delta'] >= DECISION_MARGIN}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(EVIDENCE_POLICY, POLICIES_PATH)
    ep.write_manifest(ep.build_manifest(
        task="bm25_frozen_candidate_combiner",
        evidence_policy=policy.name,
        features_requested=SEMANTIC_FIELDS,
        registry=registry, policy=policy,
        split_manifest_path=Path("Phase1_pipeline/p2_out/splits.parquet"),
        config_path=Path("reports/phase5_bm25_combiner_protocol.md"),
        seed=eh.SEED,
        declared_statistics_universe=(
            "dev split, real compositions only (bins excluded via "
            "main_split='discovery'); BM25 statistics fit on the dev "
            "candidate index, matching the screen's reference"),
    ), MANIFEST)
    print(f"\nwritten to {OUT}\nmanifest {MANIFEST}")


if __name__ == "__main__":
    main()
