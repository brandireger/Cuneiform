#!/usr/bin/env python3
"""
eval_harness.py -- P3 Deliverable 1: reusable evaluation harness.

PHASE 2 STATUS: this is a carried-forward Phase 1 harness. It renders
legacy lemma fields and does not itself enforce the Phase 2 evidence
policy. New scoring/training code may reuse audited utilities from this
module only after validating requested semantic fields through
lib/evidence_policy.py and emitting the required run manifest.

Not a numbered pipeline script (per spec: "a reusable module, not a
script") -- imported by 13_bm25.py and 14_tyndall.py. Python can't
import a digit-prefixed module name, which is the other reason this
one breaks the numbering convention.

SCOPE DECISIONS (spec left these underspecified; documented here and
in p3_report.md rather than guessed silently):

- Candidate/fragment universe = edges.parquet's 22,757 fragments:
  standalone docs as whole fragments (fragment_id == doc_id) +
  composite-doc join members as sub-fragments
  (fragment_id == f"{parent_doc}::{siglum}"). This is THE index for
  every retrieval task.
- JOINS positives: p2_out/join_pairs.jsonl (member-level; a query
  member's positive is specifically its co-member(s) of the same
  parent composite doc). Test-side = parent_doc's main_split=='test'.
- DUPLICATES positives: spec anchors this to the P2.5 234,263-pair
  DOC-level universe ("same-CTH pairs among ... docs"). To keep a
  single consistent fragment-level candidate index, duplicates are
  recomputed here at FRAGMENT level: same-CTH pairs among fragments,
  EXCLUDING any pair that is already a join pair (joins and
  duplicates are a partition per CLAUDE.md Task B, not overlapping).
  Both the P2.5 doc-level reference count and the actual fragment-
  level count used here are reported side by side for transparency.
- POOLED: union of JOINS and DUPLICATES positive sets per query,
  scored against the single fragment index above.

P4 H1 PATCH (2026-07): docID-family normalization. A handful of
corpus docIDs are catalogued TWICE -- once for the whole tablet, once
for a side/column sub-edition of the SAME physical object (e.g.
"KUB 7.58" and "KUB 7.58 Vs. I" -- confirmed byte-identical ATTESTED
content in P3's failure analysis). Exhaustively found via regex sweep
over all 21,583 doc_ids: exactly 5 such family pairs exist (see
h1_patch_report.md). Same-family candidates are excluded from ranking
entirely (neither positive nor negative -- they're not independent
objects, scoring against them either way would be meaningless), via
`family_key()`/`build_family_map()` below, applied inside
`top_k_ranking()`. Composite-member "::N" suffixes are NOT collapsed
into their parent's family (different members are genuinely different
physical fragments) -- family normalization operates on the parent_doc
part only. This does NOT touch the 98 exact-dedup groups from
unrelated objects with coincidentally-identical (near-empty/degenerate)
content -- those stay in ranking as real formulaic collisions, per spec.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

import contracts

P2_OUT = Path("p2_out")
P25_OUT = Path("p25_out")
P3_OUT = Path("p3_out")
SEED = 20260722
BOOTSTRAP_REPS = 1000
RESTORED = "restored"


# ---------------------------------------------------------------- rendering

def _word_is_attested_bearing(states):
    return any(s != RESTORED for s in states)


def _sign_tokens_for_word(signs, states, is_sum, is_akk, is_det, is_num, mode):
    """bm25_sign tokenizer for one word. mode: 'full' or 'attested'.
    Logogram/determinative words -> ONE token (whole surface, hyphen-
    joined, not sign-split); syllabic words -> hyphen-split signs as
    separate tokens; numerals -> <NUM>; 'x' stays 'x'."""
    if not signs:
        return []
    if mode == "attested" and not _word_is_attested_bearing(states):
        return []
    if is_num:
        return ["<NUM>"]
    if is_sum or is_akk or is_det:
        return ["-".join(signs)]
    # syllabic: per-sign tokens
    if mode == "full":
        return list(signs)
    return [s for s, st in zip(signs, states) if st != RESTORED]


def build_line_index(corpus: pd.DataFrame):
    """Group corpus word-rows by (doc_id, line_index_in_doc), sorted by
    word_index_in_line, once -- reused for every fragment lookup."""
    idx = defaultdict(list)
    cols = ["doc_id", "line_index_in_doc", "word_index_in_line", "signs",
            "sign_damage_states", "is_sum", "is_akk", "is_det", "is_num",
            "mrp_lemma_candidates", "trans"]
    sub = corpus[cols].sort_values(["doc_id", "line_index_in_doc", "word_index_in_line"])
    for row in sub.itertuples(index=False):
        idx[(row.doc_id, row.line_index_in_doc)].append(row)
    return idx


def render_fragment(doc_id, line_idxs, line_index):
    """Returns dict with sign/lemma token lists, full+attested, plus
    attested_sign_count, for one fragment (doc_id + its line set)."""
    sign_full, sign_attested = [], []
    lemma_full, lemma_attested = [], []
    n_attested_signs = 0
    for idx in sorted(line_idxs):
        words = line_index.get((doc_id, idx), [])
        for w in words:
            signs = json.loads(w.signs)
            states = json.loads(w.sign_damage_states)
            n_attested_signs += sum(1 for s in states if s != RESTORED)

            sign_full.extend(_sign_tokens_for_word(
                signs, states, w.is_sum, w.is_akk, w.is_det, w.is_num, "full"))
            sign_attested.extend(_sign_tokens_for_word(
                signs, states, w.is_sum, w.is_akk, w.is_det, w.is_num, "attested"))

            lemmas = json.loads(w.mrp_lemma_candidates) if pd.notna(w.mrp_lemma_candidates) else []
            lemmas = [t for t in lemmas if t]  # drop empty-string entries
            if pd.notna(w.trans) and w.trans:
                fallback = [w.trans]
            elif signs:
                fallback = ["-".join(signs)]
            else:
                fallback = []
            toks = lemmas if lemmas else fallback
            lemma_full.extend(toks)
            if _word_is_attested_bearing(states):
                lemma_attested.extend(toks)

    return {
        "sign_full": sign_full, "sign_attested": sign_attested,
        "lemma_full": lemma_full, "lemma_attested": lemma_attested,
        "n_attested_signs": n_attested_signs,
    }


def render_fragment_ideogram_only(doc_id, line_idxs, line_index):
    """Tyndall (2012)'s second tokenization: ideograms only (Sumero-/
    Akkadograms -- word-signs -- excluding determinatives, which are
    unpronounced classifiers, not word-signs themselves)."""
    full, attested = [], []
    for idx in sorted(line_idxs):
        for w in line_index.get((doc_id, idx), []):
            if not (w.is_sum or w.is_akk):
                continue
            signs = json.loads(w.signs)
            states = json.loads(w.sign_damage_states)
            if not signs:
                continue
            tok = "-".join(signs)
            full.append(tok)
            if _word_is_attested_bearing(states):
                attested.append(tok)
    return {"full": full, "attested": attested}


def add_bigrams(tokens):
    if len(tokens) < 2:
        return list(tokens)
    bigrams = [f"{a}␟{b}" for a, b in zip(tokens, tokens[1:])]
    return list(tokens) + bigrams


# ---------------------------------------------------------------- universe

def load_fragment_universe():
    """Returns (fragments_df, line_index, splits, doc_table). fragments_df
    has one row per edges.parquet fragment with rendered token lists."""
    P3_OUT.mkdir(exist_ok=True)
    cache_path = P3_OUT / "fragment_renderings.parquet"

    edges = pd.read_parquet(P2_OUT / "edges.parquet")
    splits = pd.read_parquet(P2_OUT / "splits.parquet")
    doc_table = pd.read_parquet(P2_OUT / "doc_table.parquet")

    if cache_path.exists():
        frags = pd.read_parquet(cache_path)
    else:
        corpus = pd.read_parquet(P2_OUT / "corpus.parquet")
        line_index = build_line_index(corpus)
        del corpus

        rows = []
        for e in edges.itertuples(index=False):
            line_idxs = [pl["line_index_in_doc"] for pl in json.loads(e.lines)]
            r = render_fragment(e.parent_doc, line_idxs, line_index)
            rows.append({
                "fragment_id": e.fragment_id, "parent_doc": e.parent_doc,
                "siglum": e.siglum, "cth": e.cth, "n_lines": e.n_lines,
                "sign_full": json.dumps(r["sign_full"], ensure_ascii=False),
                "sign_attested": json.dumps(r["sign_attested"], ensure_ascii=False),
                "lemma_full": json.dumps(r["lemma_full"], ensure_ascii=False),
                "lemma_attested": json.dumps(r["lemma_attested"], ensure_ascii=False),
                "n_attested_signs": r["n_attested_signs"],
            })
        frags = pd.DataFrame(rows)
        frags.to_parquet(cache_path, index=False)

    # CAVEAT DISCOVERED IN P3 (not fixable here -- P3 must not alter
    # frozen P2.5 outputs): splits.parquet has 28 doc_id values that
    # appear MORE THAN ONCE with different CTH assignments -- some are
    # literal duplicate files cross-filed under two CTH folders in the
    # source zip (e.g. "KUB 4.1.xml" exists under both CTH 552_XML/
    # and CTH 422_XML/), others are DIFFERENT files whose <docID> text
    # happens to collide (e.g. "Bo 3964.xml" and the composite
    # "KBo 59.207+.xml" both report docID "Bo 3964"). A naive merge on
    # doc_id fans these out into ambiguous duplicate fragment rows --
    # some pairs straddle train/test, a real cleanroom risk. Safe fix:
    # exclude ambiguous doc_ids from the fragment universe entirely
    # (never silently pick one side), reported here and in p3_report.md.
    dup_doc_ids = set(splits.loc[splits.duplicated("doc_id", keep=False), "doc_id"])
    if dup_doc_ids:
        n_before = len(frags)
        frags = frags[~frags["parent_doc"].isin(dup_doc_ids)].copy()
        print(f"[eval_harness] Excluded {n_before - len(frags)} fragments "
              f"belonging to {len(dup_doc_ids)} ambiguous (duplicate) "
              f"doc_ids from the fragment universe -- see docstring/"
              f"p3_report.md 'Corpus caveat' section.")
    meta = splits[~splits["doc_id"].isin(dup_doc_ids)][
        ["doc_id", "main_split", "site_split", "is_bin"]].rename(
        columns={"doc_id": "parent_doc"})
    frags = frags.merge(meta, on="parent_doc", how="left")
    frags["genre_band"] = (frags["cth"] // 100 * 100).astype("Int64")
    return frags, splits, doc_table


# ---------------------------------------------------------------- positives

def build_join_positives(frags: pd.DataFrame):
    """Returns list of dicts: fragment_id_a, fragment_id_b, tier,
    join_type, parent_is_bin, test_side (bool)."""
    parent_split = dict(zip(frags["parent_doc"], frags["main_split"]))
    pairs = []
    with open(P2_OUT / "join_pairs.jsonl", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            fid_a = f"{p['parent_doc']}::{p['member_a']['siglum']}"
            fid_b = f"{p['parent_doc']}::{p['member_b']['siglum']}"
            test_side = parent_split.get(p["parent_doc"]) == "test"
            pairs.append({
                "fragment_id_a": fid_a, "fragment_id_b": fid_b,
                "tier": p["tier"], "join_type": p["join_type"],
                "parent_is_bin": p["parent_is_bin"],
                "exclusive_untestable": p.get("exclusive_untestable"),
                "test_side": test_side,
            })
    return pairs


def load_reconstructed():
    rec = {}
    with open(P2_OUT / "unjoin_reconstructed.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            rec[d["doc_id"]] = d
    return rec


def tier_c_exclusive_tokens(join_pairs, line_index, reconstructed, rendering="attested"):
    """For every testable tier-C pair (test_side, tier=='C', not
    exclusive_untestable), render member_a/member_b using ONLY their
    lines exclusive of the pair's shared overlap (reuses
    render_fragment's word tokenizer on a restricted line set).
    Returns dict fragment_id -> {sign, lemma} token lists, keyed by
    the pair's normal fragment_id (so it can be substituted directly
    into the candidate index in place of the contaminated full
    rendering) -- plus the list of (query_fid, positive_fid) pairs."""
    substitutions = {}
    eval_pairs = []
    for p in join_pairs:
        if p["tier"] != "C" or not p["test_side"] or p.get("exclusive_untestable"):
            continue
        parent = p["fragment_id_a"].split("::")[0]
        rec = reconstructed.get(parent)
        if rec is None:
            continue
        sig_a = p["fragment_id_a"].split("::")[1]
        sig_b = p["fragment_id_b"].split("::")[1]
        lines_a = rec["member_lines"].get(sig_a, [])
        lines_b = rec["member_lines"].get(sig_b, [])
        excl_a = [e["line_idx"] for e in lines_a if sig_b not in e["shared_with"]]
        excl_b = [e["line_idx"] for e in lines_b if sig_a not in e["shared_with"]]
        if not excl_a or not excl_b:
            continue
        r_a = render_fragment(parent, excl_a, line_index)
        r_b = render_fragment(parent, excl_b, line_index)
        substitutions[p["fragment_id_a"]] = r_a
        substitutions[p["fragment_id_b"]] = r_b
        eval_pairs.append((p["fragment_id_a"], p["fragment_id_b"]))
    return substitutions, eval_pairs


def build_duplicate_positives(frags: pd.DataFrame, join_pair_set, split="test"):
    """Fragment-level same-CTH pairs, real (non-bin) only, restricted
    to `split` ('test' for P3 harness use; 'train' for P4 D15's
    training positives), excluding pairs that are already join pairs.
    join_pair_set: set of frozenset({fid_a, fid_b}) from
    build_join_positives."""
    test_real = frags[(frags["main_split"] == split) & (~frags["is_bin"])]
    pairs = []
    for cth, grp in test_real.groupby("cth"):
        ids = grp["fragment_id"].tolist()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                key = frozenset((ids[i], ids[j]))
                if key in join_pair_set:
                    continue
                pairs.append({"fragment_id_a": ids[i], "fragment_id_b": ids[j], "cth": cth})
    return pairs


# ---------------------------------------------------------------- metrics

def recall_and_rank(ranked_ids, positive_set, ks=(1, 5, 10, 100)):
    """ranked_ids: candidate fragment_ids sorted best-first (query
    excluded). Returns dict k->hit(0/1) and reciprocal rank."""
    rank = None
    for i, fid in enumerate(ranked_ids):
        if fid in positive_set:
            rank = i + 1
            break
    out = {f"recall@{k}": (1 if (rank is not None and rank <= k) else 0) for k in ks}
    out["rr"] = (1.0 / rank) if rank is not None else 0.0
    out["rank"] = rank
    return out


def bootstrap_ci(values, reps=BOOTSTRAP_REPS, seed=SEED):
    if len(values) == 0:
        return (None, None)
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    means = np.empty(reps)
    n = len(arr)
    for i in range(reps):
        sample = arr[rng.integers(0, n, n)]
        means[i] = sample.mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def length_band(n_attested_signs, quartile_edges):
    for i, edge in enumerate(quartile_edges):
        if n_attested_signs <= edge:
            return f"Q{i+1}"
    return f"Q{len(quartile_edges)+1}"


def aggregate_metrics(per_query_rows, ks=(1, 5, 10, 100)):
    """per_query_rows: list of dicts with recall@k/rr/n. Returns dict
    with mean + CI + n for each metric."""
    n = len(per_query_rows)
    out = {"n": n}
    if n == 0:
        for k in ks:
            out[f"recall@{k}"] = {"mean": None, "ci": [None, None]}
        out["mrr"] = {"mean": None, "ci": [None, None]}
        return out
    for k in ks:
        vals = [r[f"recall@{k}"] for r in per_query_rows]
        lo, hi = bootstrap_ci(vals)
        out[f"recall@{k}"] = {"mean": float(np.mean(vals)), "ci": [lo, hi]}
    vals = [r["rr"] for r in per_query_rows]
    lo, hi = bootstrap_ci(vals)
    out["mrr"] = {"mean": float(np.mean(vals)), "ci": [lo, hi]}
    return out


# ---------------------------------------------------------------- scoring

_identity = lambda x: x  # noqa: E731 -- tokens are pre-tokenized lists


class FixedBM25Scorer:
    """BM25 pair scorer with statistics fit once over a declared universe.

    The legacy ``bm25_score_matrix`` helper fits on its candidate index for
    each call. Tracers need to score perturbed documents without allowing the
    perturbation to refit IDF or average document length. This class separates
    the reference-statistics fit from pair scoring and stamps its provenance.
    """

    def __init__(self, reference_tokens, *, universe_name,
                 content_hash=None, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.vectorizer = CountVectorizer(
            tokenizer=_identity, preprocessor=_identity,
            lowercase=False, token_pattern=None)
        tf = self.vectorizer.fit_transform(reference_tokens).tocsr()
        self.n_documents = tf.shape[0]
        if self.n_documents == 0:
            raise ValueError("FixedBM25Scorer requires a non-empty reference universe")
        doc_len = np.asarray(tf.sum(axis=1)).ravel()
        self.avgdl = float(doc_len.mean())
        df = np.asarray((tf > 0).sum(axis=0)).ravel()
        self.idf = np.log(
            (self.n_documents - df + 0.5) / (df + 0.5) + 1.0)
        self.idf = np.clip(self.idf, 0.0, None)
        self.provenance = contracts.stamp_stats(
            {"avgdl": self.avgdl, "vocabulary_size": len(self.idf)},
            universe_name=universe_name,
            n=self.n_documents,
            content_hash=content_hash,
        )

    @property
    def vocabulary(self):
        return tuple(self.vectorizer.vocabulary_.keys())

    def assert_provenance(self, *, expected_universe, expected_n):
        contracts.assert_stats_provenance(
            self.provenance,
            expected_universe=expected_universe,
            expected_n=expected_n,
        )

    def score_pairs(self, query_tokens, document_tokens):
        if len(query_tokens) != len(document_tokens):
            raise ValueError(
                "FixedBM25Scorer.score_pairs requires equally sized query "
                "and document collections")
        tf = self.vectorizer.transform(document_tokens).tocsr()
        doc_len = np.asarray(tf.sum(axis=1)).ravel()
        length_norm = self.k1 * (
            1 - self.b + self.b * (doc_len / self.avgdl))
        row_norm = np.repeat(length_norm, np.diff(tf.indptr))
        tf_data = tf.data.astype(float)
        weighted_data = (
            self.idf[tf.indices] * tf_data * (self.k1 + 1)
            / (tf_data + row_norm)
        )
        weighted = sp.csr_matrix(
            (weighted_data, tf.indices, tf.indptr), shape=tf.shape)

        query_tf = self.vectorizer.transform(query_tokens)
        query_tf.data[:] = 1.0
        return np.asarray(query_tf.multiply(weighted).sum(axis=1)).ravel()

    def score(self, query_tokens, document_tokens):
        return float(self.score_pairs([query_tokens], [document_tokens])[0])


def bm25_score_matrix(index_tokens, query_tokens, k1=1.5, b=0.75):
    """Returns (scores, vectorizer). scores: sparse (n_queries x n_docs),
    higher = more relevant. Query side uses binary term presence
    (standard BM25 practice); doc side uses full BM25 term weighting,
    vectorized over the sparse term-frequency matrix's nonzero entries
    only (not a python loop over doc-term pairs)."""
    vec = CountVectorizer(tokenizer=_identity, preprocessor=_identity,
                           lowercase=False, token_pattern=None)
    TF = vec.fit_transform(index_tokens).tocsr()
    n_docs = TF.shape[0]
    doc_len = np.asarray(TF.sum(axis=1)).ravel()
    avgdl = doc_len.mean() if n_docs else 1.0
    df = np.asarray((TF > 0).sum(axis=0)).ravel()
    idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
    idf = np.clip(idf, 0.0, None)

    L = k1 * (1 - b + b * (doc_len / avgdl if avgdl else 1.0))
    row_L = np.repeat(L, np.diff(TF.indptr))
    tf_data = TF.data.astype(float)
    weighted_data = idf[TF.indices] * tf_data * (k1 + 1) / (tf_data + row_L)
    W = sp.csr_matrix((weighted_data, TF.indices, TF.indptr), shape=TF.shape)

    QTF = vec.transform(query_tokens)
    QTF.data[:] = 1.0  # binary query-term presence

    scores = QTF @ W.T  # (n_queries x n_docs)
    return scores.tocsr(), vec


def tfidf_score_matrix(index_tokens, query_tokens):
    """Returns (scores, vectorizer). Cosine similarity via sklearn
    TfidfVectorizer (L2-normalized rows -> dot product == cosine)."""
    vec = TfidfVectorizer(tokenizer=_identity, preprocessor=_identity,
                           lowercase=False, token_pattern=None)
    D = vec.fit_transform(index_tokens)
    Q = vec.transform(query_tokens)
    scores = Q @ D.T
    return scores.tocsr(), vec


# ---------------------------------------------------------------- H1: docID-family normalization

FAMILY_SUFFIX_RE = re.compile(
    r"^(.*?)(\+)?\s+(Vs\.?\??|Rs\.?\??|obv\.?\??|rev\.?\??)(\s*[IVX]+\.?)?$",
    re.IGNORECASE)


def build_family_map(frags: pd.DataFrame):
    """doc_id -> family_key. Strips a trailing side/column suffix only
    when the base form ALSO exists as an independent doc_id in the
    corpus (i.e. it's a real catalogued sibling, not just a fragment
    whose own line_label-derived name happens to look suffix-like)."""
    all_ids = set(frags["parent_doc"].unique())
    fam = {}
    for did in all_ids:
        m = FAMILY_SUFFIX_RE.match(did)
        base = m.group(1).strip() if m else None
        fam[did] = base if (base and base in all_ids and base != did) else did
    return fam


def fragment_family(fragment_id, family_map):
    parent = fragment_id.split("::")[0]
    return family_map.get(parent, parent)


# ---------------------------------------------------------------- task runner

_exclusion_log = {"count": 0}


def top_k_ranking(scores_row, candidate_ids, exclude_id, family_map=None,
                   query_family=None, candidate_families=None, k=100):
    """scores_row: 1 x n_docs sparse row. Returns candidate_ids sorted
    best-first (score desc, ties broken by candidate_id for
    determinism), excluding exclude_id AND (H1 patch) every candidate
    in the same docID-family as the query -- logged via
    _exclusion_log for h1_patch_report.md. Family args are optional so
    non-H1 callers (e.g. determinism re-checks against pre-patch
    numbers) still work unchanged.

    BUGFIX (2026-07-22, found during P5 D16 candidate generation):
    family exclusion must NEVER fire between two composite-doc
    SIBLINGS (same parent_doc, different '::N' member) -- those are
    genuinely distinct physical fragments and, for the JOINS task, a
    query's own true positive partner IS such a sibling by
    construction. `fragment_family()` strips the '::N' suffix before
    lookup, so two siblings always compared equal under the OLD
    check, silently excluding every join query's true partner whenever
    family_map was supplied. Confirmed against results_p3_patched/
    (already-accepted P3/H1 artifacts): patched joins tier-A/B
    recall@1 read exactly 0.0 (vs the real unpatched 0.059/0.5) --
    this bug, not a genuine regression. The module's own docstring
    already stated the intended behavior ("Composite-member '::N'
    suffixes are NOT collapsed into their parent's family") -- this
    fixes the implementation to match that stated intent; it does not
    change what H1 was designed to do. results_p3_patched/ and
    h1_patch_report.md are P3-phase frozen artifacts and are NOT
    silently regenerated here -- flagged to the architect session
    instead; this fix applies going forward (P5 and later)."""
    row = scores_row.toarray().ravel() if sp.issparse(scores_row) else np.asarray(scores_row)
    order = np.argsort(-row, kind="stable")
    if query_family is not None and candidate_families is not None:
        query_parent = exclude_id.split("::")[0]
        ranked = []
        for i in order:
            cid = candidate_ids[i]
            if cid == exclude_id:
                continue
            cand_parent = cid.split("::")[0]
            if candidate_families[i] == query_family and cand_parent != query_parent:
                _exclusion_log["count"] += 1
                continue
            ranked.append(cid)
        return ranked
    return [candidate_ids[i] for i in order if candidate_ids[i] != exclude_id]


def run_retrieval(query_ids, query_tokens, candidate_ids, candidate_tokens,
                   positives_by_query, method="bm25", ks=(1, 5, 10, 100),
                   family_map=None):
    """Core Task B runner for one (scorer, index_variant, rendering)
    combination. positives_by_query: dict query_id -> set(candidate_id).
    Returns (per_query_rows, aggregate_metrics). Pass family_map (from
    build_family_map) to apply the H1 same-family exclusion."""
    if method == "bm25":
        scores, _ = bm25_score_matrix(candidate_tokens, query_tokens)
    else:
        scores, _ = tfidf_score_matrix(candidate_tokens, query_tokens)

    cand_families = ([fragment_family(c, family_map) for c in candidate_ids]
                      if family_map is not None else None)

    per_query = []
    for qi, qid in enumerate(query_ids):
        positives = positives_by_query.get(qid, set())
        if not positives:
            continue
        q_fam = fragment_family(qid, family_map) if family_map is not None else None
        ranked = top_k_ranking(scores[qi], candidate_ids, exclude_id=qid,
                                family_map=family_map, query_family=q_fam,
                                candidate_families=cand_families)
        m = recall_and_rank(ranked, positives, ks=ks)
        m["query_id"] = qid
        m["n_positives"] = len(positives)
        m["top1"] = ranked[0] if ranked else None
        per_query.append(m)
    agg = aggregate_metrics(per_query, ks=ks)
    return per_query, agg


def run_task_a(query_ids, query_tokens, query_parent_doc, query_cth,
               candidate_ids, candidate_tokens, candidate_parent_doc, candidate_cth,
               method="bm25", ks=(1, 5, 10), family_map=None):
    """Zero-shot composition assignment, leave-one-out. A query's
    candidate pool excludes ALL fragments sharing its parent_doc (not
    just itself) -- otherwise a sibling join-member of the same
    physical object would trivially "prove" the composition. With
    family_map (H1 patch), also excludes fragments from a docID-family
    sibling parent_doc (e.g. "KUB 7.58 Vs. I" when the query is from
    "KUB 7.58") for the same reason -- they're not independent
    evidence either. Ranks COMPOSITIONS by the best-scoring candidate
    fragment belonging to that composition. Compositions with zero
    eligible same-CTH candidates after this exclusion (single-witness
    on test side) are counted and excluded from the metric, never
    silently dropped."""
    if method == "bm25":
        scores, _ = bm25_score_matrix(candidate_tokens, query_tokens)
    else:
        scores, _ = tfidf_score_matrix(candidate_tokens, query_tokens)

    cand_cth_arr = np.asarray(candidate_cth)
    cand_parent_arr = np.asarray(candidate_parent_doc)
    if family_map is not None:
        cand_family_arr = np.asarray([family_map.get(p, p) for p in candidate_parent_doc])

    per_query = []
    n_excluded_single_witness = 0
    for qi, qid in enumerate(query_ids):
        q_parent = query_parent_doc[qi]
        q_cth = query_cth[qi]
        row = scores[qi].toarray().ravel()
        if family_map is not None:
            q_family = family_map.get(q_parent, q_parent)
            mask = cand_family_arr != q_family
        else:
            mask = cand_parent_arr != q_parent
        if not mask.any() or q_cth not in set(cand_cth_arr[mask]):
            n_excluded_single_witness += 1
            continue
        elig_scores = row[mask]
        elig_cth = cand_cth_arr[mask]
        # best score per candidate composition
        order = np.argsort(-elig_scores, kind="stable")
        seen = {}
        ranked_cth = []
        for i in order:
            c = elig_cth[i]
            if c not in seen:
                seen[c] = True
                ranked_cth.append(c)
        rank = None
        for i, c in enumerate(ranked_cth):
            if c == q_cth:
                rank = i + 1
                break
        m = {f"recall@{k}": (1 if (rank is not None and rank <= k) else 0) for k in ks}
        m["rr"] = (1.0 / rank) if rank else 0.0
        m["rank"] = rank
        m["query_id"] = qid
        per_query.append(m)

    agg = aggregate_metrics(per_query, ks=ks)
    agg["n_excluded_single_witness"] = n_excluded_single_witness
    return per_query, agg


def export_failures(task_name, per_query, candidate_render_lookup, query_render_lookup,
                     positives_by_query, out_path, n=20):
    """top-20 highest-scored false top-1 predictions + 20 worst-ranked
    (deepest-buried) true positives, with ATTESTED renderings for
    error-analysis reading."""
    false_top1 = [r for r in per_query if r.get("top1") is not None
                  and r["top1"] not in positives_by_query.get(r["query_id"], set())]
    false_top1_sorted = sorted(false_top1, key=lambda r: -(r.get("rank") or 10**9))[:n]

    has_positive = [r for r in per_query if r.get("rank")]
    worst_true = sorted(has_positive, key=lambda r: -r["rank"])[:n]

    def render(fid, lookup):
        toks = lookup.get(fid, [])
        return " ".join(toks[:40])

    records = []
    for r in false_top1_sorted:
        records.append({
            "task": task_name, "kind": "false_top1", "query_id": r["query_id"],
            "predicted": r.get("top1"), "query_rendering": render(r["query_id"], query_render_lookup),
            "predicted_rendering": render(r.get("top1"), candidate_render_lookup),
        })
    for r in worst_true:
        records.append({
            "task": task_name, "kind": "worst_true_positive", "query_id": r["query_id"],
            "rank": r["rank"], "query_rendering": render(r["query_id"], query_render_lookup),
        })
    with open(out_path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return records
