#!/usr/bin/env python3
"""Does a classical character n-gram model do what CANINE was doing?

    python scripts/phase5_char_ngram_control.py

Executes `reports/phase5_char_ngram_control_protocol.md` (PRE-REGISTERED
2026-08-04, committed before this run). Training-free; no pretrained weights
are used except to answer question (b); dev split only.

The contamination control found the combiner's +0.0462 survives destroying
the Hittite language entirely (retention 1.016). So CANINE is not
contributing knowledge of Hittite -- it is contributing generic
character-sequence similarity. This asks whether TF-IDF over character
n-grams contributes the same thing, and, decisively, whether CANINE adds
anything BEYOND it.

All fold, alpha and bootstrap machinery is imported from
`phase5_bm25_combiner`; ranking goes through `eval_harness.run_task_a`'s
precomputed path, as everywhere else in this line of work.
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_harness as eh  # noqa: E402

_screen = __import__("phase5_ladder_screen")
_comb = __import__("phase5_bm25_combiner")

OUT = Path("Phase4/phase4_out/p5_char_ngram_control.json")

# --- pre-registered constants; do not adjust after seeing results ---------
NGRAM_GRID = [(2, 3), (2, 4), (3, 5), (4, 6)]
CANINE_DELTA = 0.0462          # from phase5_bm25_combiner_results.md
INCREMENT_MARGIN = 0.010


def char_similarity(rows, ngram_range):
    """Cosine similarity over character n-gram TF-IDF of the same rendered
    text CANINE was given. analyzer='char', not 'char_wb': n-grams must span
    the spaces between signs, since cross-sign sequence is the fuzzy-matching
    signal at issue."""
    vec = TfidfVectorizer(analyzer="char", ngram_range=ngram_range,
                          lowercase=False, min_df=2, norm="l2")
    X = vec.fit_transform([r["text"] for r in rows])
    return (X @ X.T).toarray()          # rows are L2-normalized -> cosine


def fit_two_param(rows, zb, z1, z2, fold_of, base_correct, grid1, label):
    """alpha (and, for the single-signal arms, the n-gram range) fit on the
    fit folds only; applied to the held-out fold. Ties to the smallest."""
    held_out, per_fold = {}, []
    for f in range(_comb.N_FOLDS):
        fit_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] != f]
        ev_idx = [i for i, r in enumerate(rows) if fold_of[r["cth"]] == f]
        best, best_r = None, -1.0
        for key in grid1:
            base = zb if z1 is None else zb + key[1] * z1[key[0]]
            for a in _comb.ALPHA_GRID:
                scores = base if z2 is None else base + a * z2
                _pq, agg = _comb.run_subset(rows, scores, fit_idx)
                r = agg["recall@1"]["mean"] or 0.0
                if r > best_r + 1e-12:
                    best, best_r = (key, a), r
                if z2 is None:
                    break
        (key, a) = best
        base = zb if z1 is None else zb + key[1] * z1[key[0]]
        scores = base if z2 is None else base + a * z2
        pq_ev, agg_ev = _comb.run_subset(rows, scores, ev_idx)
        held_out.update(_comb.correct_by_query(pq_ev))
        per_fold.append({"fold": f, "selected": [list(key[0]) if key[0] else None,
                                                 key[1], a],
                         "fit_recall@1": best_r,
                         "held_out_recall@1": agg_ev["recall@1"]["mean"]})
        print(f"    fold {f}: {label} selected={key}, alpha={a} "
              f"fit={best_r:.4f} held-out={agg_ev['recall@1']['mean']:.4f}")
    return held_out, per_fold


def main():
    print("Loading dev fragments (test never loaded)...")
    rows = _screen.load_dev_fragments()
    all_idx = list(range(len(rows)))
    fold_of, load = _comb.assign_folds(rows)
    print(f"dev fragments: {len(rows)}, fold query loads: {load}")

    bm25 = eh.bm25_score_matrix([r["tokens"] for r in rows],
                                [r["tokens"] for r in rows])[0].toarray()
    pq_base, agg_base = _comb.run_subset(rows, bm25, all_idx)
    base_correct = _comb.correct_by_query(pq_base)
    zb = _comb.znorm_rows(bm25)
    print(f"BM25 reference recall@1 {agg_base['recall@1']['mean']:.4f} "
          f"(n={agg_base['n']})")

    print("\nBuilding character n-gram similarities...")
    zchar = {}
    for ng in NGRAM_GRID:
        zchar[ng] = _comb.znorm_rows(char_similarity(rows, ng))
        print(f"  char{ng} built")

    result = {
        "protocol": "reports/phase5_char_ngram_control_protocol.md "
                    "(PRE-REGISTERED 2026-08-04, committed before this run)",
        "training_free": True, "split": "dev only; test never loaded",
        "ngram_grid": [list(g) for g in NGRAM_GRID],
        "canine_delta_reference": CANINE_DELTA,
        "bm25_reference_recall@1": agg_base["recall@1"]["mean"],
        "arms": {},
    }

    # --- (a) recovery: BM25 + char n-gram vs BM25 -------------------------
    print("\n== (a) BM25 + char n-gram vs BM25 ==")
    grid_char = [(ng, a) for ng in NGRAM_GRID for a in _comb.ALPHA_GRID]
    ho_char, pf_char = fit_two_param(rows, zb, zchar, None, fold_of,
                                     base_correct, grid_char, "char")
    cmp_char = _comb.compare(ho_char, base_correct)
    retention = cmp_char["delta"] / CANINE_DELTA
    print(f"  R = {cmp_char['delta']:+.4f} CI {[round(x, 4) for x in cmp_char['delta_ci95']]} "
          f"| retention vs CANINE {retention:.3f}")
    result["arms"]["bm25_plus_char"] = {**cmp_char, "per_fold": pf_char,
                                        "retention_vs_canine": retention}

    # --- (b) increment: + CANINE on top of BM25 + char n-gram -------------
    print("\n== (b) BM25 + char + CANINE vs BM25 + char  [PRIMARY] ==")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cache = Path("Phase4/phase4_out/p5_combiner_embeddings.npz")
    if cache.exists() and np.load(cache)[_comb.PRIMARY].shape[0] == len(rows):
        print(f"  reusing cached {_comb.PRIMARY} embeddings")
        vecs = np.load(cache)[_comb.PRIMARY]
    else:
        cand = next(c for c in _screen.CANDIDATES if c["name"] == _comb.PRIMARY)
        vecs = _screen.embed(rows, cand, device)
    zcan = _comb.znorm_rows(_screen.cosine_matrix(vecs))

    ho_both, pf_both = fit_two_param(rows, zb, zchar, zcan, fold_of,
                                     base_correct, grid_char, "char+canine")
    cmp_incr = _comb.compare(ho_both, ho_char)          # vs BM25 + char
    cmp_both_vs_bm25 = _comb.compare(ho_both, base_correct)
    print(f"  I = {cmp_incr['delta']:+.4f} CI "
          f"{[round(x, 4) for x in cmp_incr['delta_ci95']]} "
          f"(+{cmp_incr['n_gained']}/-{cmp_incr['n_lost']})")
    print(f"  (BM25+char+CANINE vs BM25 alone: {cmp_both_vs_bm25['delta']:+.4f})")
    result["arms"]["bm25_plus_char_plus_canine"] = {
        "vs_bm25_plus_char": cmp_incr, "vs_bm25_alone": cmp_both_vs_bm25,
        "per_fold": pf_both}

    # --- the pre-registered rule -----------------------------------------
    if not cmp_incr["ci_excludes_zero"]:
        verdict = "CANINE_REDUNDANT"
    elif cmp_incr["delta"] >= INCREMENT_MARGIN:
        verdict = "CANINE_ADDS_BEYOND_CLASSICAL"
    else:
        verdict = "INCONCLUSIVE"
    result["decision"] = {
        "primary_statistic": "I = held-out recall@1 delta of "
                             "BM25+char+CANINE over BM25+char",
        "I": cmp_incr["delta"], "I_ci95": cmp_incr["delta_ci95"],
        "I_ci_excludes_zero": cmp_incr["ci_excludes_zero"],
        "R": cmp_char["delta"], "retention_vs_canine": retention,
        "verdict": verdict,
    }
    print(f"\n== PRE-REGISTERED VERDICT: {verdict} ==")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"written to {OUT}")


if __name__ == "__main__":
    main()
