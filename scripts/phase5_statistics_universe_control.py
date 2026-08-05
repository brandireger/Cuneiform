#!/usr/bin/env python3
"""Does the classical gain survive a declared statistics universe?

    python scripts/phase5_statistics_universe_control.py

Executes `reports/phase5_statistics_universe_protocol.md` (PRE-REGISTERED
2026-08-04, committed before this run). Training-free; dev queries only; test
is never loaded.

Every arm in the Phase 5 classical-control line fit its BM25 IDF/avgdl and its
TF-IDF vocabularies on the same 876 dev fragments that were also the candidate
index -- a query-derived subset CLAUDE.md forbids for declared statistics. Two
threats were bundled in that: the small fitting set (T1) and the small
distractor pool (T2). This measures them separately, on one identical query
set, with the arm set held fixed at what was historically measured.

Three universes:

  U1  dev-fit,  dev index   -- historical reproduction (asserted, C1)
  U2  full-fit, dev index   -- T1 alone
  U3  full-fit, full index  -- T1 + T2

U2 is the full-universe score matrix restricted to its dev columns. That is
exact rather than approximate: a BM25/TF-IDF score of query i against document
j depends only on globally-fit quantities and on document j itself.

Nothing here reimplements ranking, folds, alpha fitting or the cluster
bootstrap -- `eval_harness.run_task_a`'s precomputed path, `phase5_bm25_combiner`
and `phase5_unigram_tfidf_control._cluster_summary` are imported. A second
ranking implementation is how E2 happened.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_harness as eh  # noqa: E402
import evidence_policy as ep  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
from effect_decision import practical_increment_verdict  # noqa: E402

_screen = __import__("phase5_ladder_screen")
_comb = __import__("phase5_bm25_combiner")
_uni = __import__("phase5_unigram_tfidf_control")

OUT_DIR = Path("Phase4/phase4_out")
OUT = OUT_DIR / "p5_statistics_universe.json"
PER_QUERY = OUT_DIR / "p5_statistics_universe_per_query.jsonl"
MANIFEST = OUT_DIR / "p5_statistics_universe_manifest.json"
PROTOCOL = Path("reports/phase5_statistics_universe_protocol.md")
REGISTRY = Path("configs/evidence_registry.yaml")
POLICIES = Path("configs/evidence_policies.yaml")

# --- pre-registered constants; do not adjust after seeing results ---------
CHAR_NGRAM_RANGE = (4, 6)
DECISION_MARGIN = 0.010
HISTORICAL = {                      # protocol check C1, +/- REPRO_TOL
    "bm25_plus_unigram_tfidf": 0.0520,
    "bm25_plus_bigram_tfidf": 0.1017,
}
REPRO_TOL = 0.0005
PRIMARY_ARM = "bm25_plus_bigram_tfidf"

_identity = lambda x: x             # noqa: E731 -- tokens are pre-tokenized


# ------------------------------------------------------------------ loading

def load_labeled_universe():
    """Fragments of the labeled non-test universe, rendered ATTESTED.

    Identical to `phase5_ladder_screen.load_dev_fragments` except that it
    admits `main_split in {train, dev}` and records which side each row came
    from. Bins carry main_split='discovery' and are therefore excluded, which
    keeps the labeled index and the unlabeled discovery pool distinct. Test is
    never selected.
    """
    frags, _splits, _doc = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    rows = []
    for row in frags.itertuples(index=False):
        if row.main_split not in ("train", "dev") or row.fragment_id not in edge_info:
            continue
        li, tl, bl, by = edge_info[row.fragment_id]
        toks = ht.build_structured_sequence_attested(
            row.parent_doc, li, line_index, tl, bl, by)
        content = [t for t in toks if not t.startswith("<")]
        if len(content) < 4:
            continue
        rows.append({
            "fragment_id": row.fragment_id, "parent_doc": row.parent_doc,
            "cth": row.cth, "tokens": content, "text": " ".join(content),
            "main_split": row.main_split,
        })
    return rows


# ------------------------------------------------------------------ scoring

def rectangular_task_a(query_rows, cand_rows, scores, query_idx):
    """Task A for a query subset against a candidate pool that need not be the
    query set. Delegates to `eval_harness.run_task_a`'s precomputed path, the
    same code `phase5_bm25_combiner.run_subset` uses; the only difference is
    that queries and candidates come from two lists rather than one."""
    qi = list(query_idx)
    return eh.run_task_a(
        [query_rows[i]["fragment_id"] for i in qi],
        [query_rows[i]["tokens"] for i in qi],
        [query_rows[i]["parent_doc"] for i in qi],
        [query_rows[i]["cth"] for i in qi],
        [r["fragment_id"] for r in cand_rows],
        [r["tokens"] for r in cand_rows],
        [r["parent_doc"] for r in cand_rows],
        [r["cth"] for r in cand_rows],
        precomputed_scores=np.asarray(scores)[qi, :])


def tfidf_cosine(index_docs, query_docs, **vec_kwargs):
    """Cosine similarity (n_queries x n_index) with the vectorizer FIT ON THE
    INDEX side only. Fitting on the index is what makes the statistics
    universe a declared choice rather than a side effect of the query set."""
    vec = TfidfVectorizer(lowercase=False, norm="l2", **vec_kwargs)
    D = vec.fit_transform(index_docs)
    Q = vec.transform(query_docs)
    return (Q @ D.T).toarray()


def build_signals(index_rows, query_rows):
    """The three fixed arms' similarity matrices, all fit on the index side."""
    bm25 = eh.bm25_score_matrix([r["tokens"] for r in index_rows],
                                [r["tokens"] for r in query_rows])[0].toarray()
    unigram = tfidf_cosine(
        [r["tokens"] for r in index_rows], [r["tokens"] for r in query_rows],
        tokenizer=_identity, preprocessor=_identity, token_pattern=None)
    bigram = tfidf_cosine(
        [eh.add_bigrams(r["tokens"]) for r in index_rows],
        [eh.add_bigrams(r["tokens"]) for r in query_rows],
        tokenizer=_identity, preprocessor=_identity, token_pattern=None)
    char = tfidf_cosine(
        [r["text"] for r in index_rows], [r["text"] for r in query_rows],
        analyzer="char", ngram_range=CHAR_NGRAM_RANGE, min_df=2)
    return {"bm25": bm25, "bm25_plus_unigram_tfidf": unigram,
            "bm25_plus_bigram_tfidf": bigram, "bm25_plus_char_ngram": char}


# ------------------------------------------------------------------- folds

def fit_alpha(query_rows, cand_rows, zb, zc, fit_idx):
    """Grid search on the FIT queries only; ties resolve to the smallest alpha,
    so a tie favours BM25 alone. Same grid and tie rule as the combiner."""
    best_a, best_r = None, -1.0
    for a in _comb.ALPHA_GRID:
        _pq, agg = rectangular_task_a(query_rows, cand_rows, zb + a * zc, fit_idx)
        r = agg["recall@1"]["mean"] or 0.0
        if r > best_r + 1e-12:
            best_a, best_r = a, r
    return best_a, best_r


def run_arm(query_rows, cand_rows, zb, zc, fold_of, label):
    """Fold-fitted linear combiner; returns held-out per-query correctness."""
    held_out, per_fold = {}, []
    for f in range(_comb.N_FOLDS):
        fit_idx = [i for i, r in enumerate(query_rows) if fold_of[r["cth"]] != f]
        ev_idx = [i for i, r in enumerate(query_rows) if fold_of[r["cth"]] == f]
        a, fit_r = fit_alpha(query_rows, cand_rows, zb, zc, fit_idx)
        pq_ev, agg_ev = rectangular_task_a(query_rows, cand_rows, zb + a * zc, ev_idx)
        held_out.update(_comb.correct_by_query(pq_ev))
        per_fold.append({"fold": f, "alpha_selected": a, "fit_recall@1": fit_r,
                         "held_out_recall@1": agg_ev["recall@1"]["mean"],
                         "n_eval_queries": len(ev_idx)})
        print(f"    fold {f}: {label} alpha*={a:<5} fit={fit_r:.4f} "
              f"held-out={agg_ev['recall@1']['mean']:.4f}")
    return held_out, per_fold


def evaluate_universe(name, query_rows, cand_rows, signals, fold_of):
    """One universe: BM25 reference, identity control, then every fixed arm."""
    print(f"\n=== {name}: {len(query_rows)} queries x {len(cand_rows)} candidates ===")
    bm25 = signals["bm25"]
    all_idx = list(range(len(query_rows)))
    pq_base, agg_base = rectangular_task_a(query_rows, cand_rows, bm25, all_idx)
    base_correct = _comb.correct_by_query(pq_base)
    print(f"  BM25 reference recall@1 {agg_base['recall@1']['mean']:.4f} "
          f"(n={agg_base['n']})")

    zb = _comb.znorm_rows(bm25)
    pq_z, _ = rectangular_task_a(query_rows, cand_rows, zb, all_idx)
    if _comb.correct_by_query(pq_z) != base_correct:
        raise SystemExit(
            f"IDENTITY CONTROL FAILED in {name}: z-normalized BM25 does not "
            "reproduce BM25's per-query records. Every downstream number in "
            "this universe would be void.")
    print("  identity control PASSED (C3)")

    out = {
        "n_queries": len(query_rows), "n_candidates": len(cand_rows),
        "n_candidate_compositions": len({r["cth"] for r in cand_rows}),
        "bm25_reference": {
            "recall@1": agg_base["recall@1"]["mean"],
            "recall@1_ci": agg_base["recall@1"]["ci"],
            "recall@5": agg_base["recall@5"]["mean"],
            "mrr": agg_base["mrr"]["mean"], "n": agg_base["n"],
        },
        "identity_control_passed": True,
        "arms": {},
    }
    correctness = {"bm25": base_correct}
    for arm in ("bm25_plus_unigram_tfidf", "bm25_plus_bigram_tfidf",
                "bm25_plus_char_ngram"):
        print(f"  == {arm} ==")
        zc = _comb.znorm_rows(signals[arm])
        held_out, per_fold = run_arm(query_rows, cand_rows, zb, zc, fold_of, arm)
        cmp_q = _comb.compare(held_out, base_correct)
        cluster = _uni._cluster_summary(query_rows, held_out, base_correct)
        print(f"    delta {cmp_q['delta']:+.4f} query-CI "
              f"{[round(x, 4) for x in cmp_q['delta_ci95']]} | cluster-CI "
              f"{[round(x, 4) for x in cluster['query_micro_cluster_ci95']]}")
        out["arms"][arm] = {**cmp_q, "per_fold": per_fold,
                            "composition_cluster": cluster}
        correctness[arm] = held_out
    return out, correctness


# -------------------------------------------------------------------- main

def main():
    print("Loading labeled non-test universe (test never loaded)...")
    universe = load_labeled_universe()
    query_rows = [r for r in universe if r["main_split"] == "dev"]
    dev_ids = {r["fragment_id"] for r in query_rows}
    dev_cols = [i for i, r in enumerate(universe) if r["fragment_id"] in dev_ids]
    # U1 and U2 must differ ONLY in where the statistics were fit. If the dev
    # columns came out in a different order than the U1 candidate list, stable
    # argsort would break ties differently and the two universes would differ
    # for a second, unintended reason.
    assert [universe[i]["fragment_id"] for i in dev_cols] == \
        [r["fragment_id"] for r in query_rows], \
        "dev column order does not match the U1 candidate order"
    n_train = len(universe) - len(query_rows)
    print(f"  labeled universe: {len(universe)} fragments "
          f"({n_train} train + {len(query_rows)} dev), "
          f"{len({r['cth'] for r in universe})} compositions")

    # --- C2: widening the index adds distractors, never gold ---------------
    query_cths = {r["cth"] for r in query_rows}
    train_cths = {r["cth"] for r in universe if r["main_split"] == "train"}
    overlap = sorted(query_cths & train_cths)
    if overlap:
        raise SystemExit(
            f"C2 FAILED: {len(overlap)} composition(s) appear on both the dev "
            f"query side and the train index side ({overlap[:5]}). Cleanroom "
            "rule 2 requires composition-level split purity; U2 and U3 would "
            "be leaky, not merely harder.")
    print(f"  C2 PASSED: {len(train_cths)} train compositions are disjoint "
          f"from {len(query_cths)} dev query compositions")

    fold_of, fold_loads = _comb.assign_folds(query_rows)
    print(f"  fold query loads: {fold_loads}")

    print("\nBuilding dev-fit signals (U1) ...")
    dev_signals = build_signals(query_rows, query_rows)
    print("Building full-universe-fit signals (U2/U3) ...")
    full_signals = build_signals(universe, query_rows)
    dev_col_signals = {k: v[:, dev_cols] for k, v in full_signals.items()}

    universes = {}
    correctness = {}
    universes["U1_dev_fit_dev_index"], correctness["U1_dev_fit_dev_index"] = \
        evaluate_universe("U1_dev_fit_dev_index", query_rows, query_rows,
                          dev_signals, fold_of)
    dev_rows_ordered = [universe[i] for i in dev_cols]
    universes["U2_full_fit_dev_index"], correctness["U2_full_fit_dev_index"] = \
        evaluate_universe("U2_full_fit_dev_index", query_rows, dev_rows_ordered,
                          dev_col_signals, fold_of)
    universes["U3_full_fit_full_index"], correctness["U3_full_fit_full_index"] = \
        evaluate_universe("U3_full_fit_full_index", query_rows, universe,
                          full_signals, fold_of)

    # --- C1: the historical numbers must reproduce under U1 ----------------
    repro = {}
    void = []
    for arm, expected in HISTORICAL.items():
        got = universes["U1_dev_fit_dev_index"]["arms"][arm]["delta"]
        ok = abs(got - expected) <= REPRO_TOL
        repro[arm] = {"expected": expected, "observed": got,
                      "abs_diff": abs(got - expected), "within_tolerance": ok}
        print(f"  C1 {arm}: expected {expected:+.4f}, observed {got:+.4f} -> "
              f"{'OK' if ok else 'FAIL'}")
        if not ok:
            void.append(arm)

    # --- attributions (descriptive; no decision weight) --------------------
    attributions = {}
    for arm in ("bm25_plus_unigram_tfidf", "bm25_plus_bigram_tfidf",
                "bm25_plus_char_ngram"):
        d1 = universes["U1_dev_fit_dev_index"]["arms"][arm]["delta"]
        d2 = universes["U2_full_fit_dev_index"]["arms"][arm]["delta"]
        d3 = universes["U3_full_fit_full_index"]["arms"][arm]["delta"]
        attributions[arm] = {
            "delta_U1": d1, "delta_U2": d2, "delta_U3": d3,
            "T1_statistics_universe_effect": d2 - d1,
            "T2_distractor_effect": d3 - d2,
            "note": "descriptive decomposition; three universes on one query "
                    "set do not license a significance claim on a difference "
                    "of deltas",
        }

    # --- the pre-registered rule ------------------------------------------
    primary = universes["U3_full_fit_full_index"]["arms"][PRIMARY_ARM]
    cluster_ci = primary["composition_cluster"]["query_micro_cluster_ci95"]
    delta = primary["composition_cluster"]["query_micro_delta"]
    verdict = practical_increment_verdict(
        delta, cluster_ci, DECISION_MARGIN,
        positive_label="SURVIVES_DECLARED_UNIVERSE",
        below_margin_label="COLLAPSES_UNDER_DECLARED_UNIVERSE")

    result = {
        "protocol": f"{PROTOCOL} (PRE-REGISTERED 2026-08-04, committed before "
                    "this run)",
        "training_free": True,
        "split": "dev queries only; test never loaded",
        "statistics_universe": (
            "U1 reproduces the historical dev-fit universe; U2/U3 fit over the "
            "declared labeled non-test universe (main_split in {train, dev}; "
            "bins excluded as main_split='discovery'; test never read)"),
        "language_scope": "LEGACY_LANGUAGE_BLIND_REPRODUCTION_ONLY",
        "char_ngram_range": list(CHAR_NGRAM_RANGE),
        "decision_margin": DECISION_MARGIN,
        "n_labeled_universe": len(universe), "n_train_index": n_train,
        "n_dev_queries": len(query_rows), "fold_query_loads": fold_loads,
        "checks": {
            "C1_reproduction": repro,
            "C1_passed": not void,
            "C2_no_composition_overlap_passed": True,
            "C3_identity_control_passed": True,
        },
        "universes": universes,
        "attributions": attributions,
        "decision": {
            "primary_statistic": (
                f"held-out recall@1 delta of {PRIMARY_ARM} over BM25 in "
                "U3_full_fit_full_index, composition-cluster interval"),
            "delta": delta, "cluster_ci95": cluster_ci,
            "query_micro_delta": primary["delta"],
            "query_micro_ci95": primary["delta_ci95"],
            "verdict": "VOID_REPRODUCTION_FAILED" if void else verdict,
            "void_arms": void,
        },
    }

    cth_by_query = {r["fragment_id"]: r["cth"] for r in query_rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PER_QUERY, "w", encoding="utf-8") as f:
        for qid in sorted(correctness["U1_dev_fit_dev_index"]["bm25"]):
            rec = {"query_id": qid, "cth": cth_by_query[qid]}
            for uname, arms in correctness.items():
                for arm, corr in arms.items():
                    if qid in corr:
                        rec[f"{uname}::{arm}"] = int(corr[qid])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    registry = ep.load_registry(REGISTRY)
    policy = ep.load_policy("discovery_assisted", POLICIES)
    manifest = ep.build_manifest(
        task="phase5_statistics_universe_and_distractor_control",
        evidence_policy=policy.name,
        features_requested=["token", "damage_state", "cth", "bm25_score",
                            "tfidf_cosine_score"],
        registry=registry, policy=policy,
        dataset_manifest_path=Path("Phase1_pipeline/p4_out/decomposed_corpus.parquet"),
        split_manifest_path=Path("Phase1_pipeline/p2_out/splits.parquet"),
        config_path=PROTOCOL,
        seed=eh.SEED,
        declared_statistics_universe=result["statistics_universe"],
    )
    manifest["language_scope"] = result["language_scope"]
    manifest["governance_warning"] = (
        "Legacy language-blind rendering is held fixed so that the universe is "
        "the only variable that moves; it is prohibited for a promoted scorer.")
    ep.write_manifest(manifest, MANIFEST)

    print(f"\n== PRE-REGISTERED VERDICT: {result['decision']['verdict']} ==")
    print(f"   {PRIMARY_ARM} in U3: {delta:+.4f}, cluster CI "
          f"{[round(x, 4) for x in cluster_ci]}")
    print(f"written {OUT}\nwritten {PER_QUERY}\nwritten {MANIFEST}")


if __name__ == "__main__":
    main()
