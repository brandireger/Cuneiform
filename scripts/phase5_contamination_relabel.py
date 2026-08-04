#!/usr/bin/env python3
"""Contamination control: does the combiner gain survive relabeled signs?

    python scripts/phase5_contamination_relabel.py [--permutations 5]

Executes `reports/phase5_contamination_protocol.md` (PRE-REGISTERED
2026-08-04, committed before this run). Training-free; dev split only.

A bijective, character-length-preserving permutation of the sign vocabulary
preserves every overlap and co-occurrence pattern exactly while destroying
memorised Hittite surface content. If BM25 + frozen CANINE keeps its
+0.0462 under relabeling, the gain cannot be memorisation.

The combiner machinery is IMPORTED from `phase5_bm25_combiner`, not
reimplemented -- same fold assignment, same alpha grid, same paired
bootstrap. A second implementation is a second chance to get the comparison
wrong.

Correctness assertion, not an inspection: BM25 must be EXACTLY invariant
under a consistent bijection. If its 865 per-query records move, the
relabeling is not a bijection and every downstream number is void.
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

OUT = Path("Phase4/phase4_out/p5_contamination_relabel.json")

# --- pre-registered constants; do not adjust after seeing results ---------
N_PERMUTATIONS = 5
PERMUTATION_SEEDS = [20260804 + i for i in range(N_PERMUTATIONS)]
ORIGINAL_DELTA = 0.0462          # CANINE, from phase5_bm25_combiner_results.md
RETENTION_REJECT_MEMORISATION = 0.50
RETENTION_NOT_EXCLUDED = 0.20


def build_permutation(rows, seed):
    """Bijection on the sign vocabulary, permuting only WITHIN each
    character-length class so total sequence length -- and therefore
    truncation -- is unchanged. Singleton classes are necessarily fixed
    points; the realised relabeled fraction is measured, not assumed."""
    vocab = sorted({t for r in rows for t in r["tokens"]})
    by_len = {}
    for t in vocab:
        by_len.setdefault(len(t), []).append(t)
    rng = np.random.default_rng(seed)
    sigma = {}
    for _n, signs in sorted(by_len.items()):
        shuffled = list(signs)
        rng.shuffle(shuffled)
        sigma.update(dict(zip(signs, shuffled)))
    assert len(set(sigma.values())) == len(vocab), "sigma is not a bijection"
    assert all(len(k) == len(v) for k, v in sigma.items()), "sigma changed a length"
    return sigma


def relabel(rows, sigma):
    out = []
    for r in rows:
        toks = [sigma[t] for t in r["tokens"]]
        out.append({**r, "tokens": toks, "text": " ".join(toks)})
    return out


def relabeled_fraction(rows, sigma):
    total = moved = 0
    for r in rows:
        for t in r["tokens"]:
            total += 1
            moved += (sigma[t] != t)
    return moved / total if total else 0.0


def assert_bm25_invariant(rows, relabeled, base_records):
    """BM25 depends only on multiset structure, so a consistent bijection
    must leave every per-query record untouched."""
    bm25 = eh.bm25_score_matrix([r["tokens"] for r in relabeled],
                                [r["tokens"] for r in relabeled])[0].toarray()
    pq, _agg = _comb.run_subset(relabeled, bm25, list(range(len(relabeled))))
    got = _comb.correct_by_query(pq)
    if got != base_records:
        n_diff = sum(1 for q in base_records if got.get(q) != base_records[q])
        raise SystemExit(
            f"BM25 INVARIANCE FAILED: {n_diff} per-query records changed under "
            "relabeling. The permutation is not a consistent bijection; every "
            "downstream number would be void.")
    return bm25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--permutations", type=int, default=N_PERMUTATIONS)
    args = ap.parse_args()
    seeds = PERMUTATION_SEEDS[:args.permutations]

    print("Loading dev fragments (test never loaded)...")
    rows = _screen.load_dev_fragments()
    all_idx = list(range(len(rows)))
    fold_of, load = _comb.assign_folds(rows)
    print(f"dev fragments: {len(rows)}, fold query loads: {load}")

    bm25_orig = eh.bm25_score_matrix([r["tokens"] for r in rows],
                                     [r["tokens"] for r in rows])[0].toarray()
    pq_base, agg_base = _comb.run_subset(rows, bm25_orig, all_idx)
    base_correct = _comb.correct_by_query(pq_base)
    print(f"BM25 reference recall@1 {agg_base['recall@1']['mean']:.4f} "
          f"(n={agg_base['n']})")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    result = {
        "protocol": "reports/phase5_contamination_protocol.md "
                    "(PRE-REGISTERED 2026-08-04, committed before this run)",
        "training_free": True, "split": "dev only; test never loaded",
        "original_delta_canine": ORIGINAL_DELTA,
        "permutation_seeds": seeds,
        "bm25_reference_recall@1": agg_base["recall@1"]["mean"],
        "permutations": [],
    }

    per_query_deltas = {name: {} for name in (_comb.PRIMARY, _comb.SECONDARY)}

    for seed in seeds:
        print(f"\n== permutation seed {seed} ==")
        sigma = build_permutation(rows, seed)
        relabeled = relabel(rows, sigma)
        frac = relabeled_fraction(rows, sigma)
        print(f"  relabeled {100*frac:.2f}% of sign occurrences")

        bm25_r = assert_bm25_invariant(rows, relabeled, base_correct)
        print("  BM25 invariance PASSED (per-query records identical)")

        zb = _comb.znorm_rows(bm25_r)
        entry = {"seed": seed, "relabeled_fraction": frac,
                 "bm25_invariant": True, "arms": {}}
        for cand in _screen.CANDIDATES:
            name = cand["name"]
            if name not in (_comb.PRIMARY, _comb.SECONDARY):
                continue
            vecs = _screen.embed(relabeled, cand, device)
            zc = _comb.znorm_rows(_screen.cosine_matrix(vecs))
            _detail, held_out, _fit = _comb.linear_combiner(
                relabeled, zb, zc, fold_of, name, base_correct)
            corr = _comb.correct_by_query(held_out)
            cmp = _comb.compare(corr, base_correct)
            for q, v in corr.items():
                if q in base_correct:
                    per_query_deltas[name].setdefault(q, []).append(
                        v - base_correct[q])
            entry["arms"][name] = cmp
            print(f"  {name}: held-out {cmp['combiner_recall@1']:.4f} "
                  f"delta {cmp['delta']:+.4f} CI "
                  f"[{cmp['delta_ci95'][0]:+.4f}, {cmp['delta_ci95'][1]:+.4f}]")
        result["permutations"].append(entry)

    # --- the pre-registered statistic: mean per-query delta across seeds ---
    print("\n== pooled across permutations ==")
    result["pooled"] = {}
    for name, d in per_query_deltas.items():
        qs = sorted(d)
        mean_delta = np.array([np.mean(d[q]) for q in qs])
        lo, hi = _comb.paired_bootstrap(mean_delta)
        retention = float(mean_delta.mean() / ORIGINAL_DELTA)
        result["pooled"][name] = {
            "n_queries": len(qs),
            "mean_delta_across_permutations": float(mean_delta.mean()),
            "delta_ci95": [lo, hi],
            "ci_excludes_zero": bool(lo > 0.0 or hi < 0.0),
            "retention_vs_original": retention,
        }
        print(f"  {name}: mean delta {mean_delta.mean():+.4f} "
              f"CI [{lo:+.4f}, {hi:+.4f}]  retention {retention:.3f}")

    p = result["pooled"][_comb.PRIMARY]
    if p["retention_vs_original"] >= RETENTION_REJECT_MEMORISATION and p["ci_excludes_zero"]:
        verdict = "MEMORISATION_REJECTED"
    elif p["retention_vs_original"] <= RETENTION_NOT_EXCLUDED or not p["ci_excludes_zero"]:
        verdict = "MEMORISATION_NOT_EXCLUDED"
    else:
        verdict = "INCONCLUSIVE"
    result["decision"] = {
        "primary_candidate": _comb.PRIMARY,
        "retention": p["retention_vs_original"],
        "ci_excludes_zero": p["ci_excludes_zero"],
        "verdict": verdict,
        "note": ("The rule is one-sided by design: survival rejects "
                 "memorisation, but collapse is ambiguous between "
                 "contamination, legitimate transfer, and sensitivity to "
                 "natural-language character statistics. See the protocol."),
    }
    print(f"\n== PRE-REGISTERED VERDICT: {verdict} ==")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"written to {OUT}")


if __name__ == "__main__":
    main()
