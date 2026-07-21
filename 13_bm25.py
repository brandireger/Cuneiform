#!/usr/bin/env python3
"""
13_bm25.py -- P3 Deliverable 2: classical retrieval baselines run
through eval_harness.py.

Usage:
    python 13_bm25.py

Three scorers: bm25_sign (artifact-only: sign unigrams+bigrams, no
editorial input beyond the transliteration itself), bm25_lemma
(editor-assisted: mrp lemma candidates -- explicitly labeled as such
in every table per the project's artifacts-vs-editors principle),
tfidf_cosine_sign (sanity triangulation, sign unigrams only).

Tokenizer (bm25_sign / tfidf_cosine_sign, documented here for P4
reuse): logogram/determinative words (is_sum/is_akk/is_det) -> ONE
token (whole surface, not sign-split -- logograms are semantically
atomic, unlike genuinely-decomposable syllabic spelling); syllabic
words -> hyphen-split signs as separate tokens; numerals -> <NUM>;
illegible 'x' stays its own token. bm25_sign additionally adds
adjacent-token bigrams across the whole fragment's token stream.

SCOPE DECISIONS (beyond eval_harness.py's docstring):
- 2x2 leakage ablation run on the POOLED task, test_only index, for
  all three scorers (spec: "every scorer, cheap").
- Length/genre stratification computed on the POOLED task, test_only
  index (the headline combination) rather than every sub-metric, to
  keep metrics.json readable -- full per-query data is in
  fragment_renderings.parquet if deeper slicing is needed later.
- Task A candidate pool = test-side real fragments only (LOO); a
  full_distractor variant isn't meaningful for composition ranking
  since discovery-pool/train/dev fragments don't carry a comparably
  eligible "this is a different witness of a KNOWN test composition"
  label the same way.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import eval_harness as eh

RESULTS = Path("results")
SEED = 20260722


def dedup_guard(frags):
    strs = frags["sign_attested"].tolist()
    counts = pd.Series(strs).value_counts()
    dup_groups = counts[counts > 1]
    return {"n_fragments": len(frags), "n_exact_dup_groups": int(len(dup_groups)),
            "n_fragments_in_dup_groups": int(dup_groups.sum())}


def get_index(frags, variant, rendering, tok_field):
    if variant == "test_only":
        sub = frags[frags["main_split"] == "test"]
    else:
        sub = frags  # full_distractor = everything
    col = f"{tok_field}_{rendering}"
    ids = sub["fragment_id"].tolist()
    toks = [json.loads(s) for s in sub[col]]
    return ids, toks


def apply_bigrams(token_lists, use_bigrams):
    if not use_bigrams:
        return token_lists
    return [eh.add_bigrams(t) for t in token_lists]


def run_task_b_suite(scorer_name, method, tok_field, use_bigrams, frags,
                      join_pairs, dup_pairs, line_index, reconstructed, family_map=None):
    out = {"index_variants": {}}
    test_join_pairs = [p for p in join_pairs if p["test_side"]]
    dup_by_frag = {}
    for p in dup_pairs:
        dup_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        dup_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
    join_by_frag = {}
    for p in test_join_pairs:
        join_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        join_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])

    frag_lookup = frags.set_index("fragment_id")

    for variant in ("test_only", "full_distractor"):
        cand_ids, cand_toks = get_index(frags, variant, "attested", tok_field)
        cand_toks = apply_bigrams(cand_toks, use_bigrams)
        cand_render_lookup = dict(zip(cand_ids, cand_toks))

        variant_out = {}

        # ---- JOINS tier A / B (regular rendering)
        for tier in ("A", "B"):
            tier_pairs = [p for p in test_join_pairs if p["tier"] == tier]
            pos = {}
            for p in tier_pairs:
                pos.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
                pos.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
            qids = [q for q in pos if q in frag_lookup.index]
            qtoks = apply_bigrams(
                [json.loads(s) for s in frag_lookup.loc[qids, f"{tok_field}_attested"]],
                use_bigrams)
            per_q, agg = eh.run_retrieval(qids, qtoks, cand_ids, cand_toks, pos, method=method,
                                           family_map=family_map)
            agg["by_join_type"] = {}
            for jt in set(p["join_type"] for p in tier_pairs):
                jt_pairs = [p for p in tier_pairs if p["join_type"] == jt]
                jt_pos = {}
                for p in jt_pairs:
                    jt_pos.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
                    jt_pos.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
                jt_qids = [q for q in jt_pos if q in frag_lookup.index]
                jt_qtoks = apply_bigrams(
                    [json.loads(s) for s in frag_lookup.loc[jt_qids, f"{tok_field}_attested"]],
                    use_bigrams)
                _, jt_agg = eh.run_retrieval(jt_qids, jt_qtoks, cand_ids, cand_toks, jt_pos,
                                              method=method, family_map=family_map)
                agg["by_join_type"][jt] = jt_agg
            variant_out[f"joins_tier_{tier}"] = agg
            if tier == "A":
                variant_out["_per_query_tierA"] = per_q  # kept for failures export

        # ---- JOINS tier C: full (contaminated, upper bound) + exclusive (honest)
        tier_c_pairs = [p for p in test_join_pairs if p["tier"] == "C"]
        pos_c_full = {}
        for p in tier_c_pairs:
            pos_c_full.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
            pos_c_full.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
        qids = [q for q in pos_c_full if q in frag_lookup.index]
        qtoks = apply_bigrams(
            [json.loads(s) for s in frag_lookup.loc[qids, f"{tok_field}_attested"]], use_bigrams)
        _, agg_full = eh.run_retrieval(qids, qtoks, cand_ids, cand_toks, pos_c_full,
                                        method=method, family_map=family_map)
        variant_out["joins_tier_C_full_UPPER_BOUND_contaminated"] = agg_full

        subs, eval_pairs = eh.tier_c_exclusive_tokens(join_pairs, line_index, reconstructed)
        if eval_pairs:
            excl_field = "sign" if tok_field == "sign" else "lemma"
            sub_ids = list(cand_ids)
            sub_toks = list(cand_toks)
            id_to_pos = {fid: i for i, fid in enumerate(sub_ids)}
            for fid, rend in subs.items():
                toks = rend[f"{excl_field}_attested"]
                toks = eh.add_bigrams(toks) if use_bigrams else toks
                if fid in id_to_pos:
                    sub_toks[id_to_pos[fid]] = toks
                else:
                    sub_ids.append(fid)
                    sub_toks.append(toks)
            pos_excl = {a: {b} for a, b in eval_pairs}
            pos_excl_rev = {b: {a} for a, b in eval_pairs}
            for k, v in pos_excl_rev.items():
                pos_excl.setdefault(k, set()).update(v)
            excl_qids = list(pos_excl.keys())
            excl_qtoks = [sub_toks[id_to_pos[q]] if q in id_to_pos else
                          (eh.add_bigrams(subs[q][f"{excl_field}_attested"]) if use_bigrams
                           else subs[q][f"{excl_field}_attested"])
                          for q in excl_qids]
            # NOTE: no family_map here deliberately -- tier-C pair members
            # share the same parent_doc/family by construction (that's the
            # positive being tested), so family-exclusion would remove the
            # intended answer, not a spurious near-duplicate.
            _, agg_excl = eh.run_retrieval(excl_qids, excl_qtoks, sub_ids, sub_toks, pos_excl, method=method)
            variant_out["joins_tier_C_exclusive_HONEST"] = agg_excl
        else:
            variant_out["joins_tier_C_exclusive_HONEST"] = {"n": 0, "note": "no testable tier-C pairs"}

        # ---- DUPLICATES
        qids = [q for q in dup_by_frag if q in frag_lookup.index]
        qtoks = apply_bigrams(
            [json.loads(s) for s in frag_lookup.loc[qids, f"{tok_field}_attested"]], use_bigrams)
        per_q_dup, agg_dup = eh.run_retrieval(qids, qtoks, cand_ids, cand_toks, dup_by_frag,
                                               method=method, family_map=family_map)
        variant_out["duplicates"] = agg_dup

        # ---- POOLED (union)
        pooled_pos = {k: set(v) for k, v in join_by_frag.items()}
        for k, v in dup_by_frag.items():
            pooled_pos.setdefault(k, set()).update(v)
        pqids = [q for q in pooled_pos if q in frag_lookup.index]
        pqtoks = apply_bigrams(
            [json.loads(s) for s in frag_lookup.loc[pqids, f"{tok_field}_attested"]], use_bigrams)
        per_q_pooled, agg_pooled = eh.run_retrieval(pqids, pqtoks, cand_ids, cand_toks, pooled_pos,
                                                     method=method, family_map=family_map)
        variant_out["pooled"] = agg_pooled

        # ---- stratification (pooled, this index variant)
        if variant == "test_only":
            n_signs = frag_lookup.loc[pqids, "n_attested_signs"].values
            edges = list(np.quantile(n_signs, [0.25, 0.5, 0.75]))
            strat_len = {}
            for r in per_q_pooled:
                band = eh.length_band(frag_lookup.loc[r["query_id"], "n_attested_signs"], edges)
                strat_len.setdefault(band, []).append(r)
            variant_out["stratified_length_band"] = {
                b: eh.aggregate_metrics(rs) for b, rs in strat_len.items()}

            strat_genre = {}
            for r in per_q_pooled:
                g = frag_lookup.loc[r["query_id"], "genre_band"]
                g = str(g) if pd.notna(g) else "unknown"
                strat_genre.setdefault(g, []).append(r)
            variant_out["stratified_genre_band"] = {
                g: eh.aggregate_metrics(rs) for g, rs in strat_genre.items()}

            variant_out["_failures_source"] = {
                "pooled": (per_q_pooled, pooled_pos), "duplicates": (per_q_dup, dup_by_frag),
            }

        out["index_variants"][variant] = variant_out

    return out, cand_render_lookup


def run_leakage_2x2(method, tok_field, use_bigrams, frags, join_pairs, dup_pairs, family_map=None):
    """FULL/FULL, FULL/ATTESTED, ATTESTED/FULL, ATTESTED/ATTESTED on
    the POOLED task, test_only index."""
    test_join_pairs = [p for p in join_pairs if p["test_side"]]
    join_by_frag, dup_by_frag = {}, {}
    for p in test_join_pairs:
        join_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        join_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
    for p in dup_pairs:
        dup_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        dup_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
    pooled_pos = {k: set(v) for k, v in join_by_frag.items()}
    for k, v in dup_by_frag.items():
        pooled_pos.setdefault(k, set()).update(v)

    test_frags = frags[frags["main_split"] == "test"].set_index("fragment_id")
    results = {}
    for q_render in ("full", "attested"):
        for c_render in ("full", "attested"):
            cand_ids = test_frags.index.tolist()
            cand_toks = apply_bigrams(
                [json.loads(s) for s in test_frags[f"{tok_field}_{c_render}"]], use_bigrams)
            qids = [q for q in pooled_pos if q in test_frags.index]
            qtoks = apply_bigrams(
                [json.loads(s) for s in test_frags.loc[qids, f"{tok_field}_{q_render}"]], use_bigrams)
            _, agg = eh.run_retrieval(qids, qtoks, cand_ids, cand_toks, pooled_pos,
                                       method=method, family_map=family_map)
            results[f"query_{q_render}_index_{c_render}"] = agg
    return results


def run_task_a_suite(method, tok_field, use_bigrams, frags, family_map=None):
    test_real = frags[(frags["main_split"] == "test") & (~frags["is_bin"])]
    qids = test_real["fragment_id"].tolist()
    qtoks = apply_bigrams([json.loads(s) for s in test_real[f"{tok_field}_attested"]], use_bigrams)
    q_parent = test_real["parent_doc"].tolist()
    q_cth = test_real["cth"].tolist()
    per_q, agg = eh.run_task_a(qids, qtoks, q_parent, q_cth, qids, qtoks, q_parent, q_cth,
                                method=method, family_map=family_map)
    return per_q, agg


def write_report(scorer_name, dedup, task_b, task_a, leakage, out_dir):
    lines = [f"# {scorer_name} -- P3 Baseline Report", "",
             f"## Exact-dedup guard",
             f"- {dedup['n_exact_dup_groups']} groups of identical ATTESTED renderings "
             f"({dedup['n_fragments_in_dup_groups']} / {dedup['n_fragments']} fragments affected)",
             "", "## Task B (test_only index)", ""]
    tv = task_b["index_variants"]["test_only"]
    for key in ("joins_tier_A", "joins_tier_B", "joins_tier_C_full_UPPER_BOUND_contaminated",
                "joins_tier_C_exclusive_HONEST", "duplicates", "pooled"):
        agg = tv.get(key, {})
        r1 = agg.get("recall@1", {})
        r10 = agg.get("recall@10", {})
        mrr = agg.get("mrr", {})
        lines.append(f"- **{key}**: n={agg.get('n')}, recall@1={r1.get('mean')} "
                     f"(CI {r1.get('ci')}), recall@10={r10.get('mean')} (CI {r10.get('ci')}), "
                     f"MRR={mrr.get('mean')} (CI {mrr.get('ci')})")
    lines += ["", "## Task B (full_distractor index) -- discovery pool as unlabeled "
              "distractors; metrics are CONSERVATIVE LOWER BOUNDS (discovery pool may "
              "contain unknown true positives scored as negatives)", ""]
    tv2 = task_b["index_variants"]["full_distractor"]
    for key in ("joins_tier_A", "joins_tier_B", "duplicates", "pooled"):
        agg = tv2.get(key, {})
        r1 = agg.get("recall@1", {})
        lines.append(f"- **{key}**: n={agg.get('n')}, recall@1={r1.get('mean')} (CI {r1.get('ci')})")

    lines += ["", "## Task A -- zero-shot composition assignment (leave-one-out)", ""]
    r1 = task_a.get("recall@1", {})
    r5 = task_a.get("recall@5", {})
    lines.append(f"- n={task_a.get('n')} (excluded single-witness: "
                 f"{task_a.get('n_excluded_single_witness')}), "
                 f"recall@1={r1.get('mean')} (CI {r1.get('ci')}), "
                 f"recall@5={r5.get('mean')} (CI {r5.get('ci')}), MRR={task_a.get('mrr', {}).get('mean')}")

    lines += ["", "## 2x2 leakage ablation (pooled, test_only)", "",
              "| query render | index render | recall@1 | MRR | n |", "|---|---|---|---|---|"]
    for combo, agg in leakage.items():
        qr, cr = combo.replace("query_", "").split("_index_")
        lines.append(f"| {qr} | {cr} | {agg['recall@1']['mean']} | {agg['mrr']['mean']} | {agg['n']} |")

    with open(out_dir / "report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    patched = "--patched" in sys.argv
    results_root = Path("results_p3_patched") if patched else RESULTS

    frags, splits, doc_table = eh.load_fragment_universe()
    join_pairs = eh.build_join_positives(frags)
    join_pair_set = {frozenset((p["fragment_id_a"], p["fragment_id_b"])) for p in join_pairs}
    dup_pairs = eh.build_duplicate_positives(frags, join_pair_set)
    family_map = eh.build_family_map(frags) if patched else None

    corpus = pd.read_parquet(eh.P2_OUT / "corpus.parquet")
    line_index = eh.build_line_index(corpus)
    del corpus
    reconstructed = eh.load_reconstructed()

    dedup = dedup_guard(frags)
    print("Dedup guard:", dedup)
    if patched:
        n_families = sum(1 for k, v in family_map.items() if k != v)
        print(f"H1 patch active: {n_families} doc_ids collapsed into a "
              f"docID-family (i.e. {n_families} sibling pairs found).")

    scorers = [
        ("bm25_sign", "bm25", "sign", True),
        ("bm25_lemma", "bm25", "lemma", False),
        ("tfidf_cosine_sign", "tfidf", "sign", False),
    ]

    summary = {"dedup_guard": dedup, "scorers": {}}
    if patched:
        eh._exclusion_log["count"] = 0
    for name, method, tok_field, use_bigrams in scorers:
        print(f"\n=== {name} ===")
        out_dir = results_root / name
        out_dir.mkdir(parents=True, exist_ok=True)

        task_b, cand_render_lookup = run_task_b_suite(
            name, method, tok_field, use_bigrams, frags, join_pairs, dup_pairs,
            line_index, reconstructed, family_map=family_map)
        per_q_tierA = task_b["index_variants"]["test_only"].pop("_per_query_tierA", [])
        fail_source = task_b["index_variants"]["test_only"].pop("_failures_source", {})

        per_q_a, task_a = run_task_a_suite(method, tok_field, use_bigrams, frags, family_map=family_map)
        leakage = run_leakage_2x2(method, tok_field, use_bigrams, frags, join_pairs, dup_pairs,
                                   family_map=family_map)

        with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump({"task_b": task_b, "task_a": task_a, "leakage_2x2": leakage,
                       "dedup_guard": dedup}, f, ensure_ascii=False, indent=2, default=str)

        failures_path = out_dir / "failures.jsonl"
        if failures_path.exists():
            failures_path.unlink()
        frag_render_lookup = dict(zip(frags["fragment_id"],
                                       [json.loads(s) for s in frags[f"{tok_field}_attested"]]))
        if "pooled" in fail_source:
            per_q_pooled, pooled_pos = fail_source["pooled"]
            eh.export_failures("task_b_pooled", per_q_pooled, frag_render_lookup,
                               frag_render_lookup, pooled_pos, failures_path)
        if per_q_tierA:
            tierA_pos = {}
            for p in join_pairs:
                if p["test_side"] and p["tier"] == "A":
                    tierA_pos.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
                    tierA_pos.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
            eh.export_failures("task_b_joins_tier_A", per_q_tierA, frag_render_lookup,
                               frag_render_lookup, tierA_pos, failures_path)
        eh.export_failures("task_a", per_q_a, frag_render_lookup, frag_render_lookup,
                           {}, failures_path)

        write_report(name, dedup, task_b, task_a, leakage, out_dir)

        summary["scorers"][name] = {
            "task_a_recall@1": task_a["recall@1"]["mean"],
            "task_b_pooled_test_only_recall@1":
                task_b["index_variants"]["test_only"]["pooled"]["recall@1"]["mean"],
            "task_b_tier_A_test_only_recall@1":
                task_b["index_variants"]["test_only"]["joins_tier_A"]["recall@1"]["mean"],
        }
        print(f"{name}: Task A recall@1={summary['scorers'][name]['task_a_recall@1']:.3f}, "
              f"Task B pooled recall@1={summary['scorers'][name]['task_b_pooled_test_only_recall@1']:.3f}")

    if patched:
        summary["h1_family_exclusion_count"] = eh._exclusion_log["count"]
        summary["h1_family_pairs"] = n_families

    with open(results_root / "p3_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    print("\nDone. Results in:", results_root.resolve())
    if patched:
        print(f"Total same-family candidate exclusions applied during ranking: "
              f"{eh._exclusion_log['count']}")


if __name__ == "__main__":
    main()
