#!/usr/bin/env python3
"""Does any richer lexical channel beat BM25 + unigram TF-IDF?

    python scripts/phase5_factorial_control.py

Executes `reports/phase5_factorial_control_protocol.md` (PRE-REGISTERED
2026-08-04, committed before this run). Training-free; dev queries only; test
is never loaded.

Step 1 (`reports/phase5_statistics_universe_results.md`) found the three
classical arms converge to within the declared 0.010 margin once statistics are
declared and the index is full. So this does not ask which representation wins.
It asks whether anything beats the cheapest one.

Two crossed factors. A **rendering** is the segment inside which an n-gram may
form -- flat (step 1's, where an n-gram can bridge a line break), per line, or
per line admitted by the ratified word-aware HITTITE_ONLY scope. A **channel**
is the similarity added to BM25. Every channel is computed per segment and
summed over a fragment's segments, so no feature can cross a segment boundary
by construction, and the rendering factor reduces to how a fragment is cut up.

Nothing here reimplements ranking, folds, the alpha search's tie rule or the
cluster bootstrap. `eval_harness.run_task_a`'s precomputed path,
`phase5_statistics_universe_control.rectangular_task_a`,
`phase5_bm25_combiner` and `phase5_unigram_tfidf_control._cluster_summary` are
imported. A second ranking implementation is how E2 happened.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_harness as eh  # noqa: E402
import evidence_policy as ep  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llv2  # noqa: E402
from effect_decision import practical_increment_verdict  # noqa: E402

_comb = __import__("phase5_bm25_combiner")
_uni = __import__("phase5_unigram_tfidf_control")
_su = __import__("phase5_statistics_universe_control")

OUT_DIR = Path("Phase4/phase4_out")
OUT = OUT_DIR / "p5_factorial_control.json"
PER_QUERY = OUT_DIR / "p5_factorial_control_per_query.jsonl"
MANIFEST = OUT_DIR / "p5_factorial_control_manifest.json"
PROTOCOL = Path("reports/phase5_factorial_control_protocol.md")
REGISTRY = Path("configs/evidence_registry.yaml")
POLICIES = Path("configs/evidence_policies.yaml")

# --- pre-registered constants; do not adjust after seeing results ---------
RENDERINGS = ["LEGACY", "BOUNDARY", "SCOPED"]
CHANNELS = ["unigram_tfidf", "bigram_only_tfidf", "unigram_plus_bigram_tfidf",
            "char_within_sign", "char_across_sign"]
CONDITIONAL_CHANNELS = ["bigram_only_tfidf", "char_within_sign",
                        "char_across_sign"]
SECOND_GRID = [0.0, 0.1, 0.2, 0.4, 0.75, 1.0, 1.5]
CHAR_NGRAM_RANGE = (4, 6)
CHAR_MIN_DF = 2                     # fragment-level, matching step 1
MIN_CONTENT_TOKENS = 4
DECISION_MARGIN = 0.010
BASE_CHANNEL = "unigram_tfidf"
PRIMARY_RENDERING = "SCOPED"

_identity = lambda x: x             # noqa: E731 -- tokens are pre-tokenized


# ----------------------------------------------------------------- loading

def load_segmented_universe():
    """Every labeled non-test fragment, rendered three ways.

    A rendering is a list of SEGMENTS (each a list of sign tokens):
    LEGACY   -- one segment, the flat token list (step 1's rendering)
    BOUNDARY -- one segment per line
    SCOPED   -- one segment per HITTITE_ONLY-admitted line

    Both language-blind renderings and the scoped one come from the single
    `iter_structured_attested` traversal, so the only thing that differs is
    which tokens are admitted and how they are grouped.
    """
    frags, _splits, _doc = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    rows = [r for r in frags.itertuples(index=False)
            if r.main_split in ("train", "dev") and r.fragment_id in edge_info]
    doc_ids = sorted({r.parent_doc for r in rows})
    scope, lang_index = llv2.hittite_only_projection(doc_ids)

    out = []
    refusal_reasons = {}
    for row in rows:
        li, tl, bl, by = edge_info[row.fragment_id]

        emptied = set()
        for idx in li:
            n_source = len(line_index.get((row.parent_doc, idx), []))
            decision = lang_index.line_decision(
                scope, row.parent_doc, idx, n_source_tokens=n_source,
                record=False)
            if not decision.in_scope:
                emptied.add(idx)
                reason = getattr(decision, "reason", "UNKNOWN")
                refusal_reasons[reason] = refusal_reasons.get(reason, 0) + 1

        by_line, by_line_scoped = {}, {}
        for tok, lidx, _wp in ht.iter_structured_attested(
                row.parent_doc, li, line_index, tl, bl, by):
            if lidx is None or tok.startswith("<"):
                continue
            by_line.setdefault(lidx, []).append(tok)
            if lidx not in emptied:
                by_line_scoped.setdefault(lidx, []).append(tok)

        boundary = [by_line[k] for k in sorted(by_line)]
        scoped = [by_line_scoped[k] for k in sorted(by_line_scoped)]
        flat = [t for seg in boundary for t in seg]
        out.append({
            "fragment_id": row.fragment_id, "parent_doc": row.parent_doc,
            "cth": row.cth, "main_split": row.main_split,
            "tokens": flat,
            "LEGACY": [flat] if flat else [],
            "BOUNDARY": boundary,
            "SCOPED": scoped,
        })
    return out, scope, lang_index, refusal_reasons


def n_content(row, rendering):
    return sum(len(seg) for seg in row[rendering])


# ---------------------------------------------------------------- channels

def _segment_docs(rows, rendering, channel):
    """(documents, owner_index) -- one document per SEGMENT, plus the index of
    the fragment each segment belongs to. Building features per segment and
    summing them per fragment is what structurally prevents a feature from
    crossing a segment boundary."""
    docs, owner = [], []
    for i, row in enumerate(rows):
        for seg in row[rendering]:
            if channel == "unigram_tfidf":
                docs.append(list(seg))
            elif channel == "bigram_only_tfidf":
                docs.append(eh.add_bigrams(seg)[len(seg):])
            elif channel == "unigram_plus_bigram_tfidf":
                docs.append(eh.add_bigrams(seg))
            else:                                   # character channels
                docs.append(" ".join(seg))
            owner.append(i)
    return docs, owner


def _sum_by_owner(X, owner, n_rows):
    """Sum segment feature rows into their owning fragment."""
    G = sp.csr_matrix(
        (np.ones(len(owner)), (np.asarray(owner), np.arange(len(owner)))),
        shape=(n_rows, len(owner)))
    return G @ X


def channel_similarity(index_rows, query_rows, rendering, channel,
                       query_rendering=None):
    """Cosine (n_queries x n_index) for one (rendering, channel).

    `query_rendering` defaults to `rendering` and exists for the one scope that
    needs an asymmetric pair: `CROSS_LANGUAGE_PARALLEL` admits only lines whose
    language DIFFERS from the query's, so it can render the index but not the
    query. Passing it here keeps that scope on this single count-then-weight
    implementation instead of a second copy. Default behaviour is unchanged.

    Counting happens per SEGMENT and weighting happens per FRAGMENT, and the
    order matters. Running a TF-IDF vectorizer directly over segments would
    make the rendering factor do two things at once: restrict which features
    can form (intended) AND move document frequency from a per-fragment to a
    per-line estimate (not intended). The smoke test caught exactly that --
    the supposedly segmentation-invariant unigram channel differed between
    LEGACY and BOUNDARY by up to 0.136 cosine.

    So: raw counts per segment, summed into fragments, and only then IDF
    weighting and L2 normalization, with the transformer FIT ON THE INDEX
    SIDE ONLY -- the declared statistics universe from step 1. Document
    frequency is therefore over index fragments in every rendering, and
    `min_df` for the character channels is applied at fragment level too,
    matching how step 1 applied it.
    """
    if channel in ("char_within_sign", "char_across_sign"):
        vec = CountVectorizer(
            analyzer="char_wb" if channel == "char_within_sign" else "char",
            ngram_range=CHAR_NGRAM_RANGE, lowercase=False)
        min_df = CHAR_MIN_DF
    else:
        vec = CountVectorizer(tokenizer=_identity, preprocessor=_identity,
                              lowercase=False, token_pattern=None)
        min_df = 1

    idx_docs, idx_owner = _segment_docs(index_rows, rendering, channel)
    q_docs, q_owner = _segment_docs(
        query_rows, query_rendering or rendering, channel)
    Dc = _sum_by_owner(vec.fit_transform(idx_docs), idx_owner, len(index_rows))
    Qc = _sum_by_owner(vec.transform(q_docs), q_owner, len(query_rows))

    if min_df > 1:
        keep = np.flatnonzero(
            np.asarray((Dc > 0).sum(axis=0)).ravel() >= min_df)
        Dc, Qc = Dc[:, keep], Qc[:, keep]

    tfidf = TfidfTransformer(norm="l2")
    D = tfidf.fit_transform(Dc)
    Q = tfidf.transform(Qc)
    return (Q @ D.T).toarray()


def bm25_similarity(index_rows, query_rows, rendering, query_rendering=None):
    """BM25 over the rendering's admitted tokens. BM25 is a bag of tokens, so
    segmentation cannot affect it -- check C1 asserts exactly that.

    `query_rendering` mirrors `channel_similarity`'s parameter, for the
    asymmetric CROSS_LANGUAGE_PARALLEL pair."""
    def toks(rows, key):
        return [[t for seg in r[key] for t in seg] for r in rows]
    return eh.bm25_score_matrix(
        toks(index_rows, rendering),
        toks(query_rows, query_rendering or rendering))[0].toarray()


# -------------------------------------------------------------------- arms

def fit_one(query_rows, cand_rows, zb, zc, fit_idx):
    best_a, best_r = None, -1.0
    for a in _comb.ALPHA_GRID:
        _pq, agg = _su.rectangular_task_a(query_rows, cand_rows, zb + a * zc, fit_idx)
        r = agg["recall@1"]["mean"] or 0.0
        if r > best_r + 1e-12:
            best_a, best_r = a, r
    return (best_a,), best_r


def fit_two(query_rows, cand_rows, zb, zu, zx, fit_idx):
    """Joint grid over both weights. Ties resolve to the smallest pair, and
    both grids contain 0, so the family contains BM25 and BM25+unigram."""
    best, best_r = None, -1.0
    for au in _comb.ALPHA_GRID:
        base = zb + au * zu
        for ax in SECOND_GRID:
            _pq, agg = _su.rectangular_task_a(
                query_rows, cand_rows, base + ax * zx, fit_idx)
            r = agg["recall@1"]["mean"] or 0.0
            if r > best_r + 1e-12:
                best, best_r = (au, ax), r
    return best, best_r


def run_arm(query_rows, cand_rows, fold_of, label, zb, zc, zx=None):
    held_out, per_fold = {}, []
    for f in range(_comb.N_FOLDS):
        fit_idx = [i for i, r in enumerate(query_rows) if fold_of[r["cth"]] != f]
        ev_idx = [i for i, r in enumerate(query_rows) if fold_of[r["cth"]] == f]
        if zx is None:
            weights, fit_r = fit_one(query_rows, cand_rows, zb, zc, fit_idx)
            scores = zb + weights[0] * zc
        else:
            weights, fit_r = fit_two(query_rows, cand_rows, zb, zc, zx, fit_idx)
            scores = zb + weights[0] * zc + weights[1] * zx
        pq_ev, agg_ev = _su.rectangular_task_a(query_rows, cand_rows, scores, ev_idx)
        held_out.update(_comb.correct_by_query(pq_ev))
        per_fold.append({"fold": f, "weights": list(weights),
                         "fit_recall@1": fit_r,
                         "held_out_recall@1": agg_ev["recall@1"]["mean"]})
    print(f"    {label:52s} weights={[d['weights'] for d in per_fold]}")
    return held_out, per_fold


def summarize(query_rows, candidate_correct, reference_correct, per_fold):
    cmp_q = _comb.compare(candidate_correct, reference_correct)
    cluster = _uni._cluster_summary(query_rows, candidate_correct, reference_correct)
    return {**cmp_q, "per_fold": per_fold, "composition_cluster": cluster}


# -------------------------------------------------------------------- main

def main():
    print("Loading and segmenting the labeled non-test universe "
          "(test never loaded)...")
    universe, scope, lang_index, refusals = load_segmented_universe()
    print(f"  {len(universe)} fragments; HITTITE_ONLY line refusals: {refusals}")

    # --- pre-registered population: defined under ALL THREE renderings -----
    def defined(row):
        return all(n_content(row, r) >= MIN_CONTENT_TOKENS for r in RENDERINGS)

    excluded = [r for r in universe if not defined(r)]
    cand_rows = [r for r in universe if defined(r)]
    query_rows = [r for r in cand_rows if r["main_split"] == "dev"]
    dev_excluded = [r for r in excluded if r["main_split"] == "dev"]
    print(f"  population: {len(cand_rows)} candidates, {len(query_rows)} dev "
          f"queries (excluded {len(excluded)}, of which {len(dev_excluded)} dev)")

    query_cths = {r["cth"] for r in query_rows}
    train_cths = {r["cth"] for r in cand_rows if r["main_split"] == "train"}
    if query_cths & train_cths:
        raise SystemExit("C3 FAILED: dev query compositions overlap the train "
                         "index; cleanroom rule 2 requires split purity.")
    print(f"  C3 PASSED: {len(train_cths)} train vs {len(query_cths)} dev "
          "compositions, disjoint")

    fold_of, fold_loads = _comb.assign_folds(query_rows)
    print(f"  fold query loads: {fold_loads}")

    # --- C4: segmentation actually removes cross-segment features ---------
    multi = [r for r in cand_rows if len(r["BOUNDARY"]) > 1][:200]
    for row in multi:
        flat = len(eh.add_bigrams(row["tokens"])) - len(row["tokens"])
        per_seg = sum(len(eh.add_bigrams(s)) - len(s) for s in row["BOUNDARY"])
        if per_seg != flat - (len(row["BOUNDARY"]) - 1):
            raise SystemExit(
                f"C4 FAILED on {row['fragment_id']}: per-segment bigram count "
                f"{per_seg} does not equal flat {flat} minus "
                f"{len(row['BOUNDARY']) - 1} segment joins.")
    print(f"  C4 PASSED: cross-segment bigrams removed exactly on {len(multi)} "
          "multi-segment fragments")

    result = {
        "protocol": f"{PROTOCOL} (PRE-REGISTERED 2026-08-04, committed before "
                    "this run)",
        "training_free": True,
        "split": "dev queries only; test never loaded",
        "statistics_universe": (
            "declared labeled non-test universe (main_split in {train, dev}; "
            "bins excluded as main_split='discovery'; test never read); "
            "vectorizers fit on the index side only"),
        "language_scope": scope.manifest_entry(),
        "language_dataset_sha256": lang_index.source_sha256,
        "char_ngram_range": list(CHAR_NGRAM_RANGE),
        "second_weight_grid": SECOND_GRID,
        "decision_margin": DECISION_MARGIN,
        "population": {
            "n_candidates": len(cand_rows), "n_dev_queries": len(query_rows),
            "n_excluded_total": len(excluded),
            "n_excluded_dev": len(dev_excluded),
            "rule": (">=4 content tokens under all three renderings; the "
                     "excluded material is reported, not discarded"),
            "hittite_only_line_refusals": refusals,
            "excluded_dev_fragment_ids": [r["fragment_id"] for r in dev_excluded],
        },
        "fold_query_loads": fold_loads,
        "renderings": {},
    }

    correctness = {}
    for rendering in RENDERINGS:
        print(f"\n=== rendering {rendering} ===")
        bm25 = bm25_similarity(cand_rows, query_rows, rendering)
        all_idx = list(range(len(query_rows)))
        pq_base, agg_base = _su.rectangular_task_a(
            query_rows, cand_rows, bm25, all_idx)
        base_correct = _comb.correct_by_query(pq_base)
        zb = _comb.znorm_rows(bm25)
        pq_z, _ = _su.rectangular_task_a(query_rows, cand_rows, zb, all_idx)
        if _comb.correct_by_query(pq_z) != base_correct:
            raise SystemExit(f"C2 IDENTITY CONTROL FAILED in {rendering}.")
        print(f"  BM25 recall@1 {agg_base['recall@1']['mean']:.4f} "
              f"(n={agg_base['n']}); C2 PASSED")

        block = {
            "bm25_reference": {
                "recall@1": agg_base["recall@1"]["mean"],
                "recall@1_ci": agg_base["recall@1"]["ci"],
                "mrr": agg_base["mrr"]["mean"], "n": agg_base["n"],
            },
            "identity_control_passed": True,
            "n_content_tokens": sum(n_content(r, rendering) for r in cand_rows),
            "marginal": {}, "conditional": {},
        }
        correctness[rendering] = {"bm25": base_correct}

        z = {}
        for channel in CHANNELS:
            z[channel] = _comb.znorm_rows(
                channel_similarity(cand_rows, query_rows, rendering, channel))
        print(f"  {len(CHANNELS)} channel similarities built")

        for channel in CHANNELS:
            held, per_fold = run_arm(query_rows, cand_rows, fold_of,
                                     f"marginal {channel}", zb, z[channel])
            block["marginal"][channel] = summarize(
                query_rows, held, base_correct, per_fold)
            correctness[rendering][channel] = held
            cc = block["marginal"][channel]["composition_cluster"]
            print(f"      delta {block['marginal'][channel]['delta']:+.4f} "
                  f"clusterCI "
                  f"{[round(x, 4) for x in cc['query_micro_cluster_ci95']]}")

        base_held = correctness[rendering][BASE_CHANNEL]
        for channel in CONDITIONAL_CHANNELS:
            held, per_fold = run_arm(
                query_rows, cand_rows, fold_of, f"conditional {channel}",
                zb, z[BASE_CHANNEL], z[channel])
            block["conditional"][channel] = summarize(
                query_rows, held, base_held, per_fold)
            correctness[rendering][f"cond_{channel}"] = held
            cc = block["conditional"][channel]["composition_cluster"]
            d = block["conditional"][channel]["delta"]
            print(f"      increment over BM25+unigram {d:+.4f} clusterCI "
                  f"{[round(x, 4) for x in cc['query_micro_cluster_ci95']]}")

        result["renderings"][rendering] = block

    # --- C1: segmentation is inert for bag-of-token channels --------------
    c1 = {
        "bm25": (correctness["LEGACY"]["bm25"] == correctness["BOUNDARY"]["bm25"]),
        BASE_CHANNEL: (correctness["LEGACY"][BASE_CHANNEL]
                       == correctness["BOUNDARY"][BASE_CHANNEL]),
    }
    result["checks"] = {"C1_segmentation_inert_for_bags": c1,
                        "C1_passed": all(c1.values()),
                        "C2_identity_control_passed": True,
                        "C3_split_purity_passed": True,
                        "C4_cross_segment_features_removed": True}
    print(f"\nC1 segmentation-inert check: {c1}")

    # --- the pre-registered rule ------------------------------------------
    verdicts = {}
    for channel in CONDITIONAL_CHANNELS:
        entry = result["renderings"][PRIMARY_RENDERING]["conditional"][channel]
        cc = entry["composition_cluster"]
        verdicts[channel] = {
            "delta": cc["query_micro_delta"],
            "cluster_ci95": cc["query_micro_cluster_ci95"],
            "verdict": practical_increment_verdict(
                cc["query_micro_delta"], cc["query_micro_cluster_ci95"],
                DECISION_MARGIN,
                positive_label="MATERIAL_INCREMENT_OVER_UNIGRAM",
                below_margin_label="BELOW_MARGIN"),
        }
    labels = {v["verdict"] for v in verdicts.values()}
    if labels == {"BELOW_MARGIN"}:
        overall = "NO_CHANNEL_BEATS_UNIGRAM"
    elif "MATERIAL_INCREMENT_OVER_UNIGRAM" in labels:
        overall = "CHANNEL_ADDS"
    else:
        overall = "INCONCLUSIVE"

    result["decision"] = {
        "primary_statistic": (
            "conditional increment over BM25 + unigram_tfidf under the "
            f"{PRIMARY_RENDERING} rendering, composition-cluster interval"),
        "per_channel": verdicts,
        "verdict": overall,
        "multiple_comparison_note": (
            "Three simultaneous comparisons. A CHANNEL_ADDS verdict is a "
            "candidate for confirmation, not an established effect."),
    }
    if not c1["bm25"] or not c1[BASE_CHANNEL]:
        result["decision"]["verdict"] = "VOID_C1_FAILED"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cth_by_query = {r["fragment_id"]: r["cth"] for r in query_rows}
    with open(PER_QUERY, "w", encoding="utf-8") as f:
        for qid in sorted(correctness["LEGACY"]["bm25"]):
            rec = {"query_id": qid, "cth": cth_by_query[qid]}
            for rendering, arms in correctness.items():
                for arm, corr in arms.items():
                    if qid in corr:
                        rec[f"{rendering}::{arm}"] = int(corr[qid])
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    registry = ep.load_registry(REGISTRY)
    policy = ep.load_policy("discovery_assisted", POLICIES)
    manifest = ep.build_manifest(
        task="phase5_factorial_lexical_channel_control",
        evidence_policy=policy.name,
        features_requested=["token", "damage_state", "cth", "bm25_score",
                            "tfidf_cosine_score", "line_lang"],
        registry=registry, policy=policy,
        dataset_manifest_path=Path("Phase1_pipeline/p4_out/decomposed_corpus.parquet"),
        split_manifest_path=Path("Phase1_pipeline/p2_out/splits.parquet"),
        config_path=PROTOCOL,
        seed=eh.SEED,
        declared_statistics_universe=result["statistics_universe"],
    )
    manifest.update(scope.manifest_entry())
    manifest["language_dataset_sha256"] = lang_index.source_sha256
    ep.write_manifest(manifest, MANIFEST)

    print(f"\n== PRE-REGISTERED VERDICT: {result['decision']['verdict']} ==")
    for channel, v in verdicts.items():
        print(f"   {channel:26s} {v['delta']:+.4f} "
              f"{[round(x, 4) for x in v['cluster_ci95']]} -> {v['verdict']}")
    print(f"written {OUT}\nwritten {PER_QUERY}\nwritten {MANIFEST}")


if __name__ == "__main__":
    main()
