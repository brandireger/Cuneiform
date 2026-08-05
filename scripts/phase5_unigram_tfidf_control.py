"""Post-hoc unigram TF-IDF decomposition of the Phase 5 bigram result.

This reproduces the historical dev-only setup deliberately.  It is an audit
artifact, not a promoted scorer; see the protocol for its limits.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import eval_harness as eh  # noqa: E402
import evidence_policy as ep  # noqa: E402

_screen = __import__("phase5_ladder_screen")
_comb = __import__("phase5_bm25_combiner")
_bigram = __import__("phase5_bigram_control")

OUT_DIR = Path("Phase4/phase4_out")
OUT = OUT_DIR / "p5_unigram_tfidf_control.json"
PER_QUERY = OUT_DIR / "p5_unigram_tfidf_control_per_query.jsonl"
MANIFEST = OUT_DIR / "p5_unigram_tfidf_control_manifest.json"
PROTOCOL = Path("reports/phase5_unigram_tfidf_control_protocol.md")
REGISTRY = Path("configs/evidence_registry.yaml")
POLICIES = Path("configs/evidence_policies.yaml")


def _cluster_summary(rows, candidate_correct, reference_correct, *, reps=1000):
    """Composition-macro result and composition-cluster bootstrap CIs."""
    cth_by_query = {r["fragment_id"]: int(r["cth"]) for r in rows}
    grouped = defaultdict(list)
    for query_id in sorted(set(candidate_correct) & set(reference_correct)):
        grouped[cth_by_query[query_id]].append(
            float(candidate_correct[query_id] - reference_correct[query_id]))

    composition_means = {cth: float(np.mean(values))
                         for cth, values in grouped.items()}
    compositions = sorted(grouped)
    rng = np.random.default_rng(eh.SEED)
    boot_micro = np.empty(reps)
    boot_macro = np.empty(reps)
    for i in range(reps):
        sampled = rng.choice(compositions, size=len(compositions), replace=True)
        cluster_values = [grouped[int(cth)] for cth in sampled]
        boot_micro[i] = np.mean([v for values in cluster_values for v in values])
        boot_macro[i] = np.mean([np.mean(values) for values in cluster_values])

    return {
        "n_compositions": len(compositions),
        "query_micro_delta": float(np.mean(
            [v for values in grouped.values() for v in values])),
        "query_micro_cluster_ci95": [float(x) for x in np.percentile(
            boot_micro, [2.5, 97.5])],
        "composition_macro_delta": float(np.mean(list(composition_means.values()))),
        "composition_macro_cluster_ci95": [float(x) for x in np.percentile(
            boot_macro, [2.5, 97.5])],
        "n_compositions_positive": sum(v > 0 for v in composition_means.values()),
        "n_compositions_negative": sum(v < 0 for v in composition_means.values()),
        "n_compositions_tied": sum(v == 0 for v in composition_means.values()),
        "per_composition": [
            {"cth": cth, "n_queries": len(grouped[cth]),
             "mean_delta": composition_means[cth]}
            for cth in compositions
        ],
    }


def _arm(rows, baseline_z, signal_z, fold_of, base_correct, label):
    detail, held_out, _fit = _comb.linear_combiner(
        rows, baseline_z, signal_z, fold_of, label, base_correct)
    correct = _comb.correct_by_query(held_out)
    return correct, {
        **_comb.compare(correct, base_correct),
        "per_fold": detail["per_fold"],
        "composition_cluster": _cluster_summary(rows, correct, base_correct),
    }


def main():
    rows = _screen.load_dev_fragments()
    tokens = [r["tokens"] for r in rows]
    all_idx = list(range(len(rows)))
    fold_of, fold_loads = _comb.assign_folds(rows)

    bm25 = eh.bm25_score_matrix(tokens, tokens)[0].toarray()
    base_pq, base_agg = _comb.run_subset(rows, bm25, all_idx)
    base_correct = _comb.correct_by_query(base_pq)
    zb = _comb.znorm_rows(bm25)

    unigram = eh.tfidf_score_matrix(tokens, tokens)[0].toarray()
    bigram = _bigram.bigram_similarity(rows)
    unigram_correct, unigram_result = _arm(
        rows, zb, _comb.znorm_rows(unigram), fold_of, base_correct,
        "unigram_tfidf")
    bigram_correct, bigram_result = _arm(
        rows, zb, _comb.znorm_rows(bigram), fold_of, base_correct,
        "unigram_plus_bigram_tfidf")

    bigram_vs_unigram = _comb.compare(bigram_correct, unigram_correct)
    bigram_vs_unigram["composition_cluster"] = _cluster_summary(
        rows, bigram_correct, unigram_correct)

    cth_by_query = {r["fragment_id"]: int(r["cth"]) for r in rows}
    per_query = []
    for query_id in sorted(base_correct):
        per_query.append({
            "query_id": query_id,
            "cth": cth_by_query[query_id],
            "bm25_correct_at_1": int(base_correct[query_id]),
            "bm25_plus_unigram_tfidf_correct_at_1": int(unigram_correct[query_id]),
            "bm25_plus_bigram_tfidf_correct_at_1": int(bigram_correct[query_id]),
        })

    result = {
        "status": "POST_HOC_REVIEWER_DECOMPOSITION_NOT_PREREGISTERED",
        "protocol": str(PROTOCOL),
        "split": "dev only; test never loaded",
        "statistics_universe": (
            "historical reproduction: 876 dev fragments; prohibited for "
            "promotion until full_non_test refit"),
        "language_scope": "LEGACY_LANGUAGE_BLIND_REPRODUCTION_ONLY",
        "n_dev_fragments": len(rows),
        "n_compositions": len({int(r["cth"]) for r in rows}),
        "fold_query_loads": fold_loads,
        "bm25_reference_recall_at_1": base_agg["recall@1"]["mean"],
        "arms": {
            "bm25_plus_unigram_tfidf": unigram_result,
            "bm25_plus_unigram_plus_bigram_tfidf": bigram_result,
            "bigram_arm_vs_unigram_arm": bigram_vs_unigram,
        },
        "interpretation": (
            "The original approximately +0.10 bigram-arm gain combines a "
            "unigram TF-IDF/cosine ensemble contribution with an additional "
            "sequence-context contribution. This audit does not identify a "
            "deployable effect."),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(PER_QUERY, "w", encoding="utf-8") as f:
        for row in per_query:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    registry = ep.load_registry(REGISTRY)
    policy = ep.load_policy("discovery_assisted", POLICIES)
    manifest = ep.build_manifest(
        task="phase5_unigram_tfidf_posthoc_decomposition",
        evidence_policy=policy.name,
        features_requested=[
            "token", "damage_state", "cth", "bm25_score",
            "tfidf_cosine_score"],
        registry=registry,
        policy=policy,
        dataset_manifest_path=Path("Phase1_pipeline/p4_out/decomposed_corpus.parquet"),
        split_manifest_path=Path("Phase1_pipeline/p2_out/splits.parquet"),
        config_path=PROTOCOL,
        seed=eh.SEED,
        declared_statistics_universe=result["statistics_universe"],
    )
    manifest["language_scope"] = result["language_scope"]
    manifest["governance_warning"] = (
        "Legacy language-blind rendering is reproduced only to audit the "
        "historical number; it is prohibited for a promoted scorer.")
    ep.write_manifest(manifest, MANIFEST)
    print(json.dumps(result["arms"], indent=2))
    print(f"written {OUT}\nwritten {PER_QUERY}\nwritten {MANIFEST}")


if __name__ == "__main__":
    main()
