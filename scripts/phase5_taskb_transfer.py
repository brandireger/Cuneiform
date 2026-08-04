#!/usr/bin/env python3
"""Does the bigram channel transfer to Task B, and what does language scope cost?

    python scripts/phase5_taskb_transfer.py [--scopes A,B] [--quick]

Executes `reports/phase5_taskb_transfer_protocol.md` (PRE-REGISTERED
2026-08-04, amended and authorized the same day; the pre-amendment draft was
NOT authorized to run). Dev queries only; the protected test split is closed
and is never loaded. No representation learning or gradient training; two
fusion weights per scope are fitted out of fold by grid search.

Structure, following the protocol section by section:

  §1  arms          bm25 / +unigram / +unigram+bigram, bigram separately weighted
  §2  weights       fitted ONCE on the pooled objective, then frozen everywhere
  §3  scopes        four, compared -- never one assumed
  §4  population    per-scope, with refusal reported as an outcome
  §5  matrix        joins / duplicates / pooled, stratified
  §5.1 bin rule     physical-join exception, joins-only, three prohibitions
  §5.2 tier C       overlap-exclusive; full rendering only as a labeled bound
  §6  inference     relation-aware clusters; Holm-Bonferroni on ONE family
  §7  checks        C1-C7

Nothing reimplements ranking, family exclusion, positives construction, folds,
channel construction or the cluster bootstrap. A second implementation of any
of those is how E2 happened, and C1 below guards a bug that already occurred
once in this exact code path.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_harness as eh  # noqa: E402
import evidence_policy as ep  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llv2  # noqa: E402
import language_scope as ls  # noqa: E402

_comb = __import__("phase5_bm25_combiner")
_uni = __import__("phase5_unigram_tfidf_control")
_fc = __import__("phase5_factorial_control")

OUT_DIR = Path("Phase4/phase4_out")
OUT = OUT_DIR / "p5_taskb_transfer.json"
PER_QUERY = OUT_DIR / "p5_taskb_transfer_per_query.jsonl"
MANIFEST = OUT_DIR / "p5_taskb_transfer_manifest.json"
PROTOCOL = Path("reports/phase5_taskb_transfer_protocol.md")

# --- pre-registered constants; do not adjust after seeing results ---------
FIXED_SCOPES = ["HITTITE_ONLY", "ALL_LANGUAGES_UNCONDITIONED"]
QUERY_RELATIVE_SCOPES = ["SAME_LANGUAGE_AS_QUERY", "CROSS_LANGUAGE_PARALLEL"]
PRIMARY_SCOPE = "HITTITE_ONLY"
BASE_SCOPE = "ALL_LANGUAGES_UNCONDITIONED"      # most permissive; base population
PRIMARY_CELLS = ["joins", "duplicates", "pooled"]
FAMILY_ALPHA = 0.05                              # Holm-Bonferroni family-wise
MIN_CONTENT_TOKENS = 4
KS = (1, 5, 10, 100)
UNRESOLVED = "QUERY_LANGUAGE_UNRESOLVED"


# ------------------------------------------------------------- §3/§4 loading

def _scope_for(name, query_language=None):
    if name in QUERY_RELATIVE_SCOPES:
        return ls.build_language_scope(name, query_language=query_language)
    return ls.build_language_scope(name)


def load_universe(scope_names, dev_query_languages=None):
    """Fragments with per-line tokens and a per-scope segmentation.

    One traversal (`iter_structured_attested`) supplies the line-grouped
    tokens; admission is then asked of `EffectiveLanguageIndex.line_decision`
    once per scope instance, so the ratified classifier decides every scope
    rather than a local copy of its rules.
    """
    frags, _splits, _doc = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    rows = [r for r in frags.itertuples(index=False)
            if r.main_split in ("train", "dev", "discovery")
            and r.fragment_id in edge_info]
    doc_ids = sorted({r.parent_doc for r in rows})
    _s, lang_index = llv2.hittite_only_projection(doc_ids)

    out = []
    for row in rows:
        li, tl, bl, by = edge_info[row.fragment_id]
        by_line = {}
        for tok, lidx, _wp in ht.iter_structured_attested(
                row.parent_doc, li, line_index, tl, bl, by):
            if lidx is None or tok.startswith("<"):
                continue
            by_line.setdefault(lidx, []).append(tok)
        # Damage proxy: the share of the editor's full reading that is NOT
        # epigraphically attested. Derived from the corpus renderings the
        # harness already carries, so it needs no damage oracle of its own.
        n_full = len(json.loads(row.sign_full)) if row.sign_full else 0
        damage = (1.0 - (row.n_attested_signs / n_full)) if n_full else None
        out.append({
            "fragment_id": row.fragment_id, "parent_doc": row.parent_doc,
            "cth": int(row.cth), "main_split": row.main_split,
            "is_bin": bool(row.is_bin), "damage_rate": damage,
            # (cth // 100) * 100 -- a coarse numeric CTH catalogue band, NOT a
            # philological genre and not a "century": CTH numbers are
            # catalogue positions. `site` is not a column here; it comes from
            # splits.parquet keyed by parent_doc.
            "genre_band": int(row.cth // 100 * 100),
            "line_idxs": sorted(li), "by_line": by_line,
        })

    # per-fragment resolved language, fail-closed (§3.3)
    for row in out:
        langs = set()
        for lidx in row["by_line"]:
            for wp in range(len(row["by_line"][lidx])):
                try:
                    lang, structural = lang_index.token_language(
                        row["parent_doc"], lidx, wp)
                except (KeyError, IndexError):
                    continue
                if not structural and lang:
                    langs.add(lang)
        row["languages"] = sorted(langs)
        row["language"] = langs.pop() if len(langs) == 1 else UNRESOLVED

    instances = [(n, None) for n in scope_names if n in FIXED_SCOPES]
    for name in scope_names:
        if name in QUERY_RELATIVE_SCOPES:
            instances += [(name, lg) for lg in (dev_query_languages or [])]

    refusals = defaultdict(lambda: defaultdict(int))
    for name, qlang in instances:
        scope = _scope_for(name, qlang)
        key = rendering_key(name, qlang)
        for row in out:
            admitted = []
            for lidx in row["line_idxs"]:
                n_source = len(line_index.get((row["parent_doc"], lidx), []))
                d = lang_index.line_decision(
                    scope, row["parent_doc"], lidx,
                    n_source_tokens=n_source, record=False)
                if d.in_scope:
                    if row["by_line"].get(lidx):
                        admitted.append(lidx)
                else:
                    refusals[key][getattr(d, "reason", "UNKNOWN")] += 1
            # admitted line INDICES are kept alongside the segments: the
            # Tier C overlap-exclusive path (§5.2) must intersect a scope's
            # admissions with a pair's exclusive lines, and matching segments
            # by content would collide whenever two lines are identical.
            row[f"{key}::lines"] = admitted
            row[key] = [list(row["by_line"][i]) for i in admitted]
    return out, lang_index, {k: dict(v) for k, v in refusals.items()}


def rendering_key(scope_name, query_language=None):
    return scope_name if query_language is None else f"{scope_name}::{query_language}"


def n_content(row, key):
    return sum(len(s) for s in row.get(key, []))


def scope_key_for(row, scope_name):
    """The rendering key this row uses under `scope_name`.

    Fixed scopes have one rendering; query-relative scopes have one per
    language, and a row whose language is unresolved has none -- it is refused
    by §3.3 rather than given a majority label."""
    if scope_name in FIXED_SCOPES:
        return rendering_key(scope_name)
    if row["language"] == UNRESOLVED:
        return None
    return rendering_key(scope_name, row["language"])


def scorable(rows, scope_name):
    """Rows this scope can actually serve.

    A row the scope empties is NOT scored as a failure: doing so would fold
    the scope's coverage loss into its accuracy number, and §4 requires those
    to be reported as two different things. What the scope refuses is counted
    and reported separately."""
    out = []
    for r in rows:
        key = scope_key_for(r, scope_name)
        if key is not None and n_content(r, key) >= MIN_CONTENT_TOKENS:
            out.append(r)
    return out


# -------------------------------------------------------------- §5 positives

def raw_join_fields():
    """fragment-id pair -> the raw join_pairs.jsonl row.

    `eval_harness.build_join_positives` keeps tier/join_type/parent_is_bin but
    DROPS `n_shared_lines` and `geometry`. Stratifying on shared-line count
    without this silently reports a constant -- which is exactly what the first
    run did, marking every pair `no_overlap=True`."""
    out = {}
    with open(Path("Phase1_pipeline/p2_out/join_pairs.jsonl"), encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            a = f"{p['parent_doc']}::{p['member_a']['siglum']}"
            b = f"{p['parent_doc']}::{p['member_b']['siglum']}"
            out[frozenset((a, b))] = p
    return out


def build_positives(rows, all_frags):
    """joins / duplicates / pooled over `rows`, plus join metadata per pair.

    Imported constructors, unchanged. Duplicates already exclude bins; that is
    asserted, not assumed (C6)."""
    ids = {r["fragment_id"] for r in rows}
    join_pairs = eh.build_join_positives(all_frags)
    join_pair_set = {frozenset((p["fragment_id_a"], p["fragment_id_b"]))
                     for p in join_pairs}

    joins, join_meta = {}, {}
    degenerate = []
    for p in join_pairs:
        a, b = p["fragment_id_a"], p["fragment_id_b"]
        if a == b:
            # Corpus data-quality artifact, not a join: two rows in
            # join_pairs.jsonl give both members the SAME siglum, so the pair
            # asserts that a fragment joins itself (KUB 28.89+::1,
            # KBo 22.130a+::1 -- both bin-parent, both discovery-side, which
            # is why they surface only under the §5.1 exception). Excluded and
            # counted, never silently kept: `run_retrieval` excludes the query
            # id from its own ranking, so a self-positive is unretrievable by
            # construction and would manufacture a guaranteed miss.
            degenerate.append(a)
            continue
        if a in ids and b in ids:
            joins.setdefault(a, set()).add(b)
            joins.setdefault(b, set()).add(a)
            join_meta[frozenset((a, b))] = p

    dups = {}
    for p in eh.build_duplicate_positives(all_frags, join_pair_set, split="dev"):
        a, b = p["fragment_id_a"], p["fragment_id_b"]
        if a in ids and b in ids:
            dups.setdefault(a, set()).add(b)
            dups.setdefault(b, set()).add(a)

    pooled = {q: set(v) for q, v in joins.items()}
    for q, v in dups.items():
        pooled.setdefault(q, set()).update(v)
    return ({"joins": joins, "duplicates": dups, "pooled": pooled},
            join_meta, sorted(set(degenerate)))


def join_components(join_meta):
    """Connected components of the physical join graph -> cluster id per
    fragment (§6). Union-find over the pairs actually in play."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for pair in join_meta:
        members = tuple(pair)
        if len(members) != 2:
            # A degenerate self-pair collapses under frozenset. These are
            # dropped in build_positives; this guard exists so the graph
            # builder cannot be what fails if one ever reaches it.
            find(members[0])
            continue
        union(*members)
    return {f: find(f) for f in parent}


# ------------------------------------------------------------- §6 statistics

def cluster_bootstrap(deltas_by_cluster, reps=1000, seed=eh.SEED):
    """Resample CLUSTERS, not query rows. Returns (delta, [lo, hi])."""
    clusters = sorted(deltas_by_cluster)
    if not clusters:
        return None, [None, None]
    flat = [v for c in clusters for v in deltas_by_cluster[c]]
    rng = np.random.default_rng(seed)
    boot = np.empty(reps)
    for i in range(reps):
        picked = rng.choice(len(clusters), size=len(clusters), replace=True)
        vals = [v for j in picked for v in deltas_by_cluster[clusters[j]]]
        boot[i] = float(np.mean(vals)) if vals else 0.0
    return float(np.mean(flat)), [float(np.percentile(boot, 2.5)),
                                  float(np.percentile(boot, 97.5))]


def holm_bonferroni(pvalues, alpha=FAMILY_ALPHA):
    """Holm step-down. Returns {key: {'p','adjusted_threshold','reject'}}."""
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(ordered)
    out, still = {}, True
    for i, (key, p) in enumerate(ordered):
        thresh = alpha / (m - i)
        reject = still and p <= thresh
        if not reject:
            still = False
        out[key] = {"p": p, "adjusted_threshold": thresh, "reject": bool(reject)}
    return out


def bootstrap_p_value(deltas_by_cluster, reps=1000, seed=eh.SEED):
    """Two-sided cluster-bootstrap p for H0: mean delta = 0."""
    clusters = sorted(deltas_by_cluster)
    if not clusters:
        return 1.0
    rng = np.random.default_rng(seed)
    observed = float(np.mean([v for c in clusters for v in deltas_by_cluster[c]]))
    boot = np.empty(reps)
    for i in range(reps):
        picked = rng.choice(len(clusters), size=len(clusters), replace=True)
        vals = [v for j in picked for v in deltas_by_cluster[clusters[j]]]
        boot[i] = float(np.mean(vals)) if vals else 0.0
    centered = boot - observed
    p = float(np.mean(np.abs(centered) >= abs(observed)))
    return min(1.0, max(p, 1.0 / reps))


# --------------------------------------------------------------- retrieval

def retrieve(query_rows, cand_rows, scores, positives, family_map, query_idx=None):
    qi = list(range(len(query_rows))) if query_idx is None else list(query_idx)
    return eh.run_retrieval(
        [query_rows[i]["fragment_id"] for i in qi],
        [None] * len(qi),
        [r["fragment_id"] for r in cand_rows],
        [None] * len(cand_rows),
        positives, ks=KS, family_map=family_map,
        precomputed_scores=np.asarray(scores)[qi, :])


def correct_at1(per_query):
    return {r["query_id"]: r["recall@1"] for r in per_query}


# ------------------------------------------------------------- score matrices

def scope_matrix(cand_rows, query_rows, scope_name, channel, lang_groups):
    """(n_queries x n_candidates) for one (scope, channel).

    Fixed scopes render both sides identically. Query-relative scopes render
    per query-language group; `CROSS_LANGUAGE_PARALLEL` renders the QUERY under
    its own language and the INDEX under the different-language admission, the
    asymmetry §3.2 requires.
    """
    if scope_name in FIXED_SCOPES:
        key = rendering_key(scope_name)
        if channel == "bm25":
            return _fc.bm25_similarity(cand_rows, query_rows, key)
        return _fc.channel_similarity(cand_rows, query_rows, key, channel)

    M = np.zeros((len(query_rows), len(cand_rows)), dtype=np.float64)
    for lang, idxs in lang_groups.items():
        if lang == UNRESOLVED or not idxs:
            continue
        idx_key = rendering_key(scope_name, lang)
        q_key = rendering_key("SAME_LANGUAGE_AS_QUERY", lang)
        sub = [query_rows[i] for i in idxs]
        if channel == "bm25":
            block = _fc.bm25_similarity(cand_rows, sub, idx_key, query_rendering=q_key)
        else:
            block = _fc.channel_similarity(cand_rows, sub, idx_key, channel,
                                           query_rendering=q_key)
        M[np.asarray(idxs), :] = block
    return M


# ----------------------------------------------------------------- §2 fitting

def fit_frozen_weights(query_rows, cand_rows, zb, zu, zg, pooled_positives,
                       fold_of, family_map):
    """Fit (alpha_u, alpha_b) ONCE on the POOLED objective, out of fold.

    Returns the per-fold selections and the held-out per-query records for the
    two fitted arms. The weights are then frozen for every cell and stratum --
    check C5 asserts that nothing re-fits them."""
    ho_u, ho_ub, per_fold = {}, {}, []
    for f in range(_comb.N_FOLDS):
        fit_idx = [i for i, r in enumerate(query_rows) if fold_of[r["cth"]] != f]
        ev_idx = [i for i, r in enumerate(query_rows) if fold_of[r["cth"]] == f]

        best_u, best_ru = None, -1.0
        for au in _comb.ALPHA_GRID:
            _pq, agg = retrieve(query_rows, cand_rows, zb + au * zu,
                                pooled_positives, family_map, fit_idx)
            r = (agg["recall@1"]["mean"] or 0.0)
            if r > best_ru + 1e-12:
                best_u, best_ru = au, r

        best_pair, best_rp = None, -1.0
        for au in _comb.ALPHA_GRID:
            base = zb + au * zu
            for ab in _fc.SECOND_GRID:
                _pq, agg = retrieve(query_rows, cand_rows, base + ab * zg,
                                    pooled_positives, family_map, fit_idx)
                r = (agg["recall@1"]["mean"] or 0.0)
                if r > best_rp + 1e-12:
                    best_pair, best_rp = (au, ab), r

        pq_u, _ = retrieve(query_rows, cand_rows, zb + best_u * zu,
                           pooled_positives, family_map, ev_idx)
        pq_ub, _ = retrieve(query_rows, cand_rows,
                            zb + best_pair[0] * zu + best_pair[1] * zg,
                            pooled_positives, family_map, ev_idx)
        ho_u.update({r["query_id"]: r for r in pq_u})
        ho_ub.update({r["query_id"]: r for r in pq_ub})
        per_fold.append({"fold": f, "alpha_unigram_only": best_u,
                         "alpha_pair": list(best_pair),
                         "fit_recall@1_unigram": best_ru,
                         "fit_recall@1_pair": best_rp,
                         "n_fit": len(fit_idx), "n_eval": len(ev_idx)})
        print(f"    fold {f}: a_u={best_u} pair={best_pair} "
              f"fit_u={best_ru:.4f} fit_pair={best_rp:.4f}")
    return per_fold, ho_u, ho_ub


# -------------------------------------------------------------- §5 evaluation

def evaluate_cell(query_rows, cand_rows, scores_u, scores_ub, positives,
                  family_map, cluster_of, label):
    """One relation cell under frozen weights: both arms, paired delta with
    relation-aware cluster bootstrap."""
    pq_u, agg_u = retrieve(query_rows, cand_rows, scores_u, positives, family_map)
    pq_ub, agg_ub = retrieve(query_rows, cand_rows, scores_ub, positives, family_map)
    cu, cub = correct_at1(pq_u), correct_at1(pq_ub)
    common = sorted(set(cu) & set(cub))

    by_cluster = defaultdict(list)
    for q in common:
        by_cluster[cluster_of.get(q, q)].append(float(cub[q] - cu[q]))
    delta, ci = cluster_bootstrap(by_cluster)
    p = bootstrap_p_value(by_cluster)

    def block(agg, pq):
        return {
            **{f"recall@{k}": agg[f"recall@{k}"]["mean"] for k in KS},
            "mrr": agg["mrr"]["mean"], "n_scored": agg["n"],
            "mean_positives": (float(np.mean([r["n_positives"] for r in pq]))
                               if pq else None),
        }

    return {
        "label": label,
        "bm25_unigram": block(agg_u, pq_u),
        "bm25_unigram_bigram": block(agg_ub, pq_ub),
        "delta_recall@1": delta, "cluster_ci95": ci, "cluster_p": p,
        "n_clusters": len(by_cluster), "n_paired": len(common),
        "n_gained": int(sum(1 for q in common if cub[q] > cu[q])),
        "n_lost": int(sum(1 for q in common if cub[q] < cu[q])),
    }, cu, cub


# ---------------------------------------------------------------- §7 checks

def check_c1_family(positives, family_map):
    """C1: no positive may satisfy the ACTUAL exclusion predicate, which is
    same family AND different parent_doc.

    It is deliberately NOT asserted that a positive's endpoints never share a
    family: composite join members share a parent and therefore a family by
    construction (`fragment_family` strips '::N'), so that stronger assertion
    would flag every valid join. That mistake is on record -- the 2026-07-22
    bugfix in `top_k_ranking` -- and it drove joins tier-A/B recall@1 to 0.0.
    """
    offenders, same_family_ok = [], 0
    for q, pos in positives.items():
        qf = eh.fragment_family(q, family_map)
        qp = q.split("::")[0]
        for p in pos:
            pf = eh.fragment_family(p, family_map)
            pp = p.split("::")[0]
            if pf == qf:
                if pp != qp:
                    offenders.append([q, p])
                else:
                    same_family_ok += 1
    return {
        "n_positives_excluded_by_predicate": len(offenders),
        "examples": offenders[:5],
        "n_same_family_same_parent_kept": same_family_ok,
        "passed": not offenders,
        "predicate": "same family AND different parent_doc",
    }


def check_c4_partition(positives):
    overlap = []
    for q, joins in positives["joins"].items():
        both = joins & positives["duplicates"].get(q, set())
        if both:
            overlap.append([q, sorted(both)[:3]])
    return {"n_queries_with_overlap": len(overlap), "examples": overlap[:5],
            "passed": not overlap}


def check_c6_bin(bin_ids, positives, cand_ids_non_bin):
    """The bin exception's three prohibitions (§5.1)."""
    in_dups = sorted(bin_ids & set(positives["duplicates"]))
    dup_targets = {t for v in positives["duplicates"].values() for t in v}
    in_dup_targets = sorted(bin_ids & dup_targets)
    in_pooled = sorted(bin_ids & set(positives["pooled"]))
    in_index = sorted(bin_ids & set(cand_ids_non_bin))
    return {
        "n_bin_fragments": len(bin_ids),
        "prohibition_1_never_a_duplicate_positive": {
            "as_query": in_dups[:5], "as_target": in_dup_targets[:5],
            "passed": not in_dups and not in_dup_targets},
        "prohibition_2_never_in_non_bin_candidate_index": {
            "offenders": in_index[:5], "passed": not in_index},
        "prohibition_3_never_in_duplicates_or_pooled_cells": {
            "offenders": in_pooled[:5], "passed": not in_pooled},
        "passed": not (in_dups or in_dup_targets or in_index or in_pooled),
    }


# ------------------------------------------------------------------- §5.2

def tier_c_exclusive_segments(rows_by_id, join_meta, reconstructed, scope_name):
    """Dev generalization of `eval_harness.tier_c_exclusive_tokens`.

    Same logic -- exclusive line sets from `unjoin_reconstructed.jsonl` --
    rendered through THIS run's segmented, scope-aware path rather than the
    flat `render_fragment`. Returns (substituted_segments, eval_pairs,
    counts). The frozen P3 helper is left untouched.
    """
    subs, eval_pairs = {}, []
    counts = {"considered": 0, "exclusive_untestable": 0,
              "no_reconstruction": 0, "empty_exclusive": 0, "usable": 0,
              "fragment_in_multiple_pairs": 0}
    seen = set()
    for pair, p in join_meta.items():
        if p["tier"] != "C":
            continue
        counts["considered"] += 1
        if p.get("exclusive_untestable"):
            counts["exclusive_untestable"] += 1
            continue
        a, b = p["fragment_id_a"], p["fragment_id_b"]
        parent = a.split("::")[0]
        rec = reconstructed.get(parent)
        if rec is None:
            counts["no_reconstruction"] += 1
            continue
        sig_a, sig_b = a.split("::")[1], b.split("::")[1]
        lines_a = rec["member_lines"].get(sig_a, [])
        lines_b = rec["member_lines"].get(sig_b, [])
        excl_a = {e["line_idx"] for e in lines_a if sig_b not in e["shared_with"]}
        excl_b = {e["line_idx"] for e in lines_b if sig_a not in e["shared_with"]}
        if not excl_a or not excl_b:
            counts["empty_exclusive"] += 1
            continue
        staged, ok = {}, True
        for fid, keep in ((a, excl_a), (b, excl_b)):
            row = rows_by_id.get(fid)
            if row is None:
                ok = False
                break
            # intersect the pair's exclusive lines with the lines this scope
            # admits, by line INDEX -- never by content, which would collide
            # between two identical lines.
            key = scope_key_for(row, scope_name)
            if key is None:
                ok = False
                break
            admitted = [i for i in row.get(f"{key}::lines", []) if i in keep]
            if not admitted:
                ok = False
                break
            staged[fid] = [list(row["by_line"][i]) for i in admitted]
        if not ok:
            counts["empty_exclusive"] += 1
            continue
        for fid, segs in staged.items():
            if fid in seen:
                counts["fragment_in_multiple_pairs"] += 1
            seen.add(fid)
            subs[fid] = segs
        eval_pairs.append((a, b))
        counts["usable"] += 1
    return subs, eval_pairs, counts


# --------------------------------------------------------------------- main

def stratify_joins(join_meta, frag_by_id, site_of, raw_fields):
    """query_id -> {stratum_name: value}, from the join pair it belongs to."""
    out = defaultdict(dict)
    for pair, p in join_meta.items():
        raw = raw_fields.get(pair, {})
        for fid in pair:
            row = frag_by_id.get(fid)
            if row is None:
                continue
            # n_shared_lines lives only on the raw row (see raw_join_fields).
            n_shared = raw.get("n_shared_lines")
            dmg = row.get("damage_rate")
            out[fid] = {
                "join_type": p.get("join_type") or "unspecified",
                "tier": p["tier"],
                "no_overlap": bool((n_shared or 0) == 0),
                "shared_line_band": ("0" if not n_shared else
                                     "1-2" if n_shared <= 2 else
                                     "3-9" if n_shared <= 9 else "10+"),
                "parent_is_bin": bool(p["parent_is_bin"]),
                "geometry": raw.get("geometry") or "unspecified",
                "language": row["language"],
                "genre_band": row["genre_band"],
                "site": site_of.get(row["parent_doc"], "unknown"),
                "length_band": ("short" if n_content(row, BASE_SCOPE) < 30 else
                                "medium" if n_content(row, BASE_SCOPE) < 120
                                else "long"),
                "damage_band": ("unknown" if dmg is None else
                                "low" if dmg < 0.15 else
                                "medium" if dmg < 0.40 else "high"),
            }
    return out


def descriptive_strata(cu, cub, strata, cluster_of):
    """Per-stratum readouts under the FROZEN weights. Descriptive only."""
    out = {}
    keys = sorted({k for v in strata.values() for k in v})
    for key in keys:
        buckets = defaultdict(lambda: defaultdict(list))
        for q in set(cu) & set(cub):
            if q not in strata:
                continue
            val = str(strata[q].get(key))
            buckets[val][cluster_of.get(q, q)].append(float(cub[q] - cu[q]))
        out[key] = {}
        for val, by_cluster in sorted(buckets.items()):
            n = sum(len(v) for v in by_cluster.values())
            delta, ci = cluster_bootstrap(by_cluster)
            out[key][val] = {
                "n_queries": n, "n_clusters": len(by_cluster),
                "delta_recall@1": delta, "cluster_ci95": ci,
                "recall@1_unigram": float(np.mean(
                    [cu[q] for q in set(cu) & set(cub)
                     if q in strata and str(strata[q].get(key)) == val])),
                "recall@1_unigram_bigram": float(np.mean(
                    [cub[q] for q in set(cu) & set(cub)
                     if q in strata and str(strata[q].get(key)) == val])),
            }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scopes", default=",".join(FIXED_SCOPES),
                    help="comma-separated scope names to run")
    args = ap.parse_args()
    scope_names = [s.strip() for s in args.scopes.split(",") if s.strip()]
    if any(s in QUERY_RELATIVE_SCOPES for s in scope_names):
        # CROSS renders its QUERIES under SAME, so SAME instances are always
        # built when either query-relative scope is requested.
        for s in QUERY_RELATIVE_SCOPES:
            if s not in scope_names:
                scope_names.append(s)

    import pandas as pd
    site_of = dict(zip(*[pd.read_parquet("Phase1_pipeline/p2_out/splits.parquet")[c]
                         for c in ("doc_id", "site")]))

    print("Loading (protected test split is never selected)...")
    frags, _splits, _doc = eh.load_fragment_universe()
    universe, lang_index, refusals = load_universe(scope_names)
    dev_langs = sorted({r["language"] for r in universe
                        if r["main_split"] == "dev"} - {UNRESOLVED})
    if any(s in QUERY_RELATIVE_SCOPES for s in scope_names):
        print(f"  rebuilding for dev query languages: {dev_langs}")
        universe, lang_index, refusals = load_universe(scope_names, dev_langs)
    by_id = {r["fragment_id"]: r for r in universe}

    # --- §4 base population, most permissive scope -------------------------
    base_ok = [r for r in universe
               if n_content(r, BASE_SCOPE) >= MIN_CONTENT_TOKENS]
    labeled = [r for r in base_ok if r["main_split"] in ("train", "dev")]
    dev_rows = [r for r in labeled if r["main_split"] == "dev"]
    print(f"  labeled index {len(labeled)}, dev queries {len(dev_rows)}, "
          f"query languages {dev_langs}")

    positives, join_meta, degenerate = build_positives(dev_rows, frags)
    if degenerate:
        print(f"  corpus data quality: {len(degenerate)} degenerate self-join "
              f"pair(s) excluded: {degenerate}")
    family_map = eh.build_family_map(frags)
    _fold_of, fold_loads = _comb.assign_folds(dev_rows)

    # --- §7 checks that do not depend on a scope ---------------------------
    c1 = {cell: check_c1_family(positives[cell], family_map)
          for cell in PRIMARY_CELLS}
    c4 = check_c4_partition(positives)
    print(f"  C1 {[(k, v['passed']) for k, v in c1.items()]}  C4 {c4['passed']}")
    if not all(v["passed"] for v in c1.values()) or not c4["passed"]:
        raise SystemExit("C1/C4 FAILED -- see output; run is void.")

    query_cths = {r["cth"] for r in dev_rows}
    train_cths = {r["cth"] for r in labeled if r["main_split"] == "train"}
    if query_cths & train_cths:
        raise SystemExit("C3 FAILED: dev query CTHs overlap the train index.")

    # --- §5.1 bin exception population -------------------------------------
    bin_join_pairs = [p for p in eh.build_join_positives(frags)
                      if p["parent_is_bin"]]
    bin_ids = set()
    for p in bin_join_pairs:
        for fid in (p["fragment_id_a"], p["fragment_id_b"]):
            row = by_id.get(fid)
            if (row is not None and row["main_split"] == "discovery"
                    and n_content(row, BASE_SCOPE) >= MIN_CONTENT_TOKENS):
                bin_ids.add(fid)
    bin_rows = [by_id[f] for f in sorted(bin_ids)]
    c6 = check_c6_bin(bin_ids, positives, {r["fragment_id"] for r in labeled})
    print(f"  C6 bin exception: {len(bin_ids)} fragments, passed={c6['passed']}")
    if not c6["passed"]:
        raise SystemExit("C6 FAILED -- the bin exception leaked; run is void.")

    reconstructed = eh.load_reconstructed()
    raw_fields = raw_join_fields()

    # §4 common population: the queries EVERY run scope can serve. Cross-scope
    # absolute numbers are otherwise on different query sets and are not
    # comparable -- the sensitivity analysis exists to make that visible.
    common_ids = None
    for name in scope_names:
        ids = {r["fragment_id"] for r in scorable(dev_rows, name)}
        common_ids = ids if common_ids is None else (common_ids & ids)
    common_ids = common_ids or set()
    print(f"  common population across {scope_names}: {len(common_ids)} queries")

    result = {
        "protocol": f"{PROTOCOL} (PRE-REGISTERED and amended 2026-08-04, "
                    "committed before this run)",
        "training_statement": ("no representation learning or gradient "
                               "training; fusion weights fitted out of fold"),
        "split": "dev queries only; protected test split closed and never loaded",
        "scopes_run": scope_names,
        "dev_query_languages": dev_langs,
        "population": {
            "base_scope": BASE_SCOPE, "n_labeled_index": len(labeled),
            "n_dev_queries": len(dev_rows),
            "n_bin_exception_fragments": len(bin_ids),
            "n_join_pairs_dev": len(join_meta),
            "n_bin_parent_join_pairs": len(bin_join_pairs),
        },
        "corpus_data_quality": {
            "degenerate_self_join_pairs_excluded": degenerate,
            "note": ("join_pairs.jsonl rows whose two members carry the SAME "
                     "siglum, asserting that a fragment joins itself. Excluded "
                     "from positives and counted. Both known cases are "
                     "bin-parent and discovery-side, so they reach an "
                     "evaluation only through the §5.1 exception."),
        },
        "fold_query_loads": fold_loads,
        "refusals_by_rendering": refusals,
        "checks": {"C1_same_family_different_parent": c1,
                   "C3_split_purity_passed": True,
                   "C4_joins_duplicates_partition": c4,
                   "C6_bin_exception": c6},
        "scopes": {},
    }

    per_query_out = defaultdict(dict)
    for scope_name in [s for s in scope_names
                       if s in FIXED_SCOPES or s == "SAME_LANGUAGE_AS_QUERY"
                       or s == "CROSS_LANGUAGE_PARALLEL"]:
        print(f"\n=== scope {scope_name} ===")
        # §4: the scope's own scorable index and query set. What it refuses is
        # counted, not scored as failure.
        s_index = scorable(labeled, scope_name)
        s_queries = scorable(dev_rows, scope_name)
        s_pos, s_meta, _deg = build_positives(s_queries, frags)
        base_rel = sum(len(v) for v in positives["pooled"].values()) // 2
        scope_rel = sum(len(v) for v in s_pos["pooled"].values()) // 2
        coverage = {
            "n_dev_queries_base": len(dev_rows),
            "n_dev_queries_scorable": len(s_queries),
            "queries_lost": len(dev_rows) - len(s_queries),
            "n_index_base": len(labeled),
            "n_index_scorable": len(s_index),
            "candidates_lost": len(labeled) - len(s_index),
            "positive_relations_base": base_rel,
            "positive_relations_scorable": scope_rel,
            "positive_relations_lost": base_rel - scope_rel,
            "eligible_candidate_set_size": len(s_index) - 1,
        }
        print(f"  coverage: queries {len(s_queries)}/{len(dev_rows)}, "
              f"index {len(s_index)}/{len(labeled)}, "
              f"relations {scope_rel}/{base_rel}")

        lang_groups = defaultdict(list)
        for i, r in enumerate(s_queries):
            lang_groups[r["language"]].append(i)

        # §6 resampling units: joins cluster by physical join component,
        # duplicates and pooled by composition. A join component nests inside
        # one composition, so clustering pooled by CTH never splits one.
        s_fold_of, _ = _comb.assign_folds(s_queries)
        s_cluster_join = {f: f"joincomp::{c}"
                          for f, c in join_components(s_meta).items()}
        s_cluster_dup = {r["fragment_id"]: f"cth::{r['cth']}" for r in s_queries}
        s_clusters = {"joins": s_cluster_join, "duplicates": s_cluster_dup,
                      "pooled": s_cluster_dup}

        bm25 = scope_matrix(s_index, s_queries, scope_name, "bm25", lang_groups)
        zb = _comb.znorm_rows(bm25)
        pq_z, _ = retrieve(s_queries, s_index, zb, s_pos["pooled"], family_map)
        pq_r, _ = retrieve(s_queries, s_index, bm25, s_pos["pooled"], family_map)
        c2 = correct_at1(pq_z) == correct_at1(pq_r)
        print(f"  C2 identity control passed={c2}")
        if not c2:
            raise SystemExit(f"C2 FAILED in {scope_name}; run is void.")

        zu = _comb.znorm_rows(scope_matrix(
            s_index, s_queries, scope_name, "unigram_tfidf", lang_groups))
        zg = _comb.znorm_rows(scope_matrix(
            s_index, s_queries, scope_name, "bigram_only_tfidf", lang_groups))

        print("  fitting frozen weights on the POOLED objective ...")
        per_fold, _ho_u, _ho_ub = fit_frozen_weights(
            s_queries, s_index, zb, zu, zg, s_pos["pooled"], s_fold_of,
            family_map)
        au = float(np.mean([d["alpha_pair"][0] for d in per_fold]))
        ab = float(np.mean([d["alpha_pair"][1] for d in per_fold]))
        # Frozen weights are the modal fold selection, so a single declared
        # pair travels to every cell and stratum (C5).
        pairs = [tuple(d["alpha_pair"]) for d in per_fold]
        frozen = max(set(pairs), key=pairs.count)
        frozen_u = max(set(d["alpha_unigram_only"] for d in per_fold),
                       key=[d["alpha_unigram_only"] for d in per_fold].count)
        print(f"  frozen weights: unigram-only a_u={frozen_u}, pair={frozen} "
              f"(fold means a_u={au:.3f} a_b={ab:.3f})")

        scores_u = zb + frozen_u * zu
        scores_ub = zb + frozen[0] * zu + frozen[1] * zg

        block = {
            "per_fold_weight_selection": per_fold,
            "frozen_weights": {"alpha_unigram_only": frozen_u,
                               "alpha_pair": list(frozen)},
            "coverage": coverage,
            "cells": {}, "strata": {},
        }

        strata = stratify_joins(s_meta, by_id, site_of, raw_fields)
        for cell in PRIMARY_CELLS:
            clusters = s_clusters[cell]
            res, cu, cub = evaluate_cell(
                s_queries, s_index, scores_u, scores_ub, s_pos[cell],
                family_map, clusters, cell)
            block["cells"][cell] = res
            print(f"  {cell:11s} d={res['delta_recall@1']:+.4f} "
                  f"CI [{res['cluster_ci95'][0]:+.4f},{res['cluster_ci95'][1]:+.4f}] "
                  f"p={res['cluster_p']:.4f} n={res['n_paired']} "
                  f"clusters={res['n_clusters']}")
            for q in set(cu) & set(cub):
                per_query_out[q][f"{scope_name}::{cell}::unigram"] = int(cu[q])
                per_query_out[q][f"{scope_name}::{cell}::unigram_bigram"] = int(cub[q])
            if cell == "joins":
                block["strata"]["joins"] = descriptive_strata(
                    cu, cub, strata, clusters)
            # §4 sensitivity: same frozen system, restricted to the queries
            # every scope can serve, so scopes become comparable.
            cu_c = {q: v for q, v in cu.items() if q in common_ids}
            cub_c = {q: v for q, v in cub.items() if q in common_ids}
            if cu_c:
                by_cl = defaultdict(list)
                for q in cu_c:
                    by_cl[clusters.get(q, q)].append(float(cub_c[q] - cu_c[q]))
                d_c, ci_c = cluster_bootstrap(by_cl)
                block.setdefault("common_population", {})[cell] = {
                    "n_queries": len(cu_c), "n_clusters": len(by_cl),
                    "recall@1_unigram": float(np.mean(list(cu_c.values()))),
                    "recall@1_unigram_bigram": float(np.mean(list(cub_c.values()))),
                    "delta_recall@1": d_c, "cluster_ci95": ci_c,
                }

        # --- §5.1 joins-only, second row: index augmented with bin joins ---
        aug_index = s_index + scorable(bin_rows, scope_name)
        aug_queries = s_queries + scorable(bin_rows, scope_name)
        aug_pos, aug_meta, aug_deg = build_positives(aug_queries, frags)
        block["degenerate_self_join_pairs_excluded"] = aug_deg
        aug_clusters = join_components(aug_meta)
        bm25_a = scope_matrix(aug_index, aug_queries, scope_name, "bm25", lang_groups)
        zb_a = _comb.znorm_rows(bm25_a)
        zu_a = _comb.znorm_rows(scope_matrix(
            aug_index, aug_queries, scope_name, "unigram_tfidf", lang_groups))
        zg_a = _comb.znorm_rows(scope_matrix(
            aug_index, aug_queries, scope_name, "bigram_only_tfidf", lang_groups))
        res_a, cu_a, cub_a = evaluate_cell(
            aug_queries, aug_index,
            zb_a + frozen_u * zu_a,
            zb_a + frozen[0] * zu_a + frozen[1] * zg_a,
            aug_pos["joins"], family_map, aug_clusters,
            "joins_with_bin_exception")
        block["cells"]["joins_with_bin_exception"] = res_a
        print(f"  joins+bin   d={res_a['delta_recall@1']:+.4f} "
              f"n={res_a['n_paired']} clusters={res_a['n_clusters']}")

        # --- §5.2 Tier C, overlap-exclusive --------------------------------
        subs, tc_pairs, tc_counts = tier_c_exclusive_segments(
            by_id, s_meta, reconstructed, scope_name)
        block["tier_c"] = {"counts": tc_counts,
                           "n_eval_pairs": len(tc_pairs)}
        if tc_pairs:
            tc_key = "__TIERC__"
            tc_index = []
            for r in s_index:
                rr = dict(r)
                rr[tc_key] = subs.get(r["fragment_id"],
                                      r[scope_key_for(r, scope_name)])
                tc_index.append(rr)
            tc_by_id = {r["fragment_id"]: r for r in tc_index}
            tc_queries = [tc_by_id[f] for f, _ in tc_pairs if f in tc_by_id]
            tc_pos = {}
            for a, b in tc_pairs:
                tc_pos.setdefault(a, set()).add(b)
                tc_pos.setdefault(b, set()).add(a)
            bm_t = _fc.bm25_similarity(tc_index, tc_queries, tc_key)
            zb_t = _comb.znorm_rows(bm_t)
            zu_t = _comb.znorm_rows(_fc.channel_similarity(
                tc_index, tc_queries, tc_key, "unigram_tfidf"))
            zg_t = _comb.znorm_rows(_fc.channel_similarity(
                tc_index, tc_queries, tc_key, "bigram_only_tfidf"))
            res_t, _cu, _cub = evaluate_cell(
                tc_queries, tc_index, zb_t + frozen_u * zu_t,
                zb_t + frozen[0] * zu_t + frozen[1] * zg_t,
                tc_pos, family_map, s_cluster_join,
                "tier_c_overlap_exclusive")
            block["tier_c"]["overlap_exclusive"] = res_t
            print(f"  tierC excl  n_pairs={len(tc_pairs)} "
                  f"d={res_t['delta_recall@1']}")
        block["tier_c"]["note"] = (
            "Full-rendering Tier C numbers appear only under "
            "strata.joins.tier['C'], which is a CONTAMINATED UPPER BOUND: "
            "those pairs share editor-aligned lines.")

        result["scopes"][scope_name] = block

    # --- §6 Holm-Bonferroni on the one declared family ---------------------
    if PRIMARY_SCOPE in result["scopes"]:
        pvals = {c: result["scopes"][PRIMARY_SCOPE]["cells"][c]["cluster_p"]
                 for c in PRIMARY_CELLS}
        result["primary_family"] = {
            "scope": PRIMARY_SCOPE, "cells": PRIMARY_CELLS,
            "family_wise_alpha": FAMILY_ALPHA,
            "holm_bonferroni": holm_bonferroni(pvals),
            "note": ("Everything outside this family -- other scopes, all "
                     "strata, the bin-exception row, Tier C, and the "
                     "cross-task arm -- is DESCRIPTIVE and carries no "
                     "confirmatory claim."),
        }
        print(f"\n== PRIMARY FAMILY ({PRIMARY_SCOPE}) ==")
        for c, v in result["primary_family"]["holm_bonferroni"].items():
            print(f"   {c:11s} p={v['p']:.4f} thresh={v['adjusted_threshold']:.4f} "
                  f"reject_H0={v['reject']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(PER_QUERY, "w", encoding="utf-8") as f:
        for q in sorted(per_query_out):
            f.write(json.dumps({"query_id": q, **per_query_out[q]},
                               ensure_ascii=False) + "\n")

    registry = ep.load_registry(Path("configs/evidence_registry.yaml"))
    policy = ep.load_policy("discovery_assisted",
                            Path("configs/evidence_policies.yaml"))
    manifest = ep.build_manifest(
        task="phase5_taskb_transfer_and_language_scope",
        evidence_policy=policy.name,
        features_requested=["token", "damage_state", "cth", "bm25_score",
                            "tfidf_cosine_score", "line_lang"],
        registry=registry, policy=policy,
        dataset_manifest_path=Path("Phase1_pipeline/p4_out/decomposed_corpus.parquet"),
        split_manifest_path=Path("Phase1_pipeline/p2_out/splits.parquet"),
        config_path=PROTOCOL, seed=eh.SEED,
        declared_statistics_universe=(
            "labeled non-test universe (train+dev); vectorizers fit on the "
            "index side; protected test never loaded"),
    )
    manifest["language_dataset_sha256"] = lang_index.source_sha256
    manifest["scopes_run"] = scope_names
    ep.write_manifest(manifest, MANIFEST)
    print(f"\nwritten {OUT}\nwritten {PER_QUERY}\nwritten {MANIFEST}")


if __name__ == "__main__":
    main()
