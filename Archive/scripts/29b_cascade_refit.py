#!/usr/bin/env python3
"""
29b_cascade_refit.py -- P5C_AMENDMENT_1.md A1/A2: BM25 full-universe refit.

Identical to scripts/29_cascade.py in every respect EXCEPT the reference
corpus used to fit BM25's IDF/avgdl for the whole-fragment and edge-window
(N=3) features. 29_cascade.py fit these over `all_cand_ids_union` (the
union of candidates appearing in ANY of the 1,054 queries' D16/D16b lists,
15,153 fragments) -- a query-derived subset. Per P5C_AMENDMENT_1.md A1,
this refit fits IDF/avgdl over the FULL non-test universe (21,920
fragments, the same reference P4B's B1 measurement used), matching the
project-wide convention that corpus statistics must be a property of the
corpus, not the evaluation queries. Candidate LISTS themselves
(p4_out/p5_candidates_whole.json, D16/D16b union top-200) are untouched --
only the BM25 scoring statistics change.

Everything downstream (train-pair selection via SEED, hard-negative
mining via train-only BM25, the SeamFeaturizer forward passes, the
logistic-regression combiner architecture) is bit-for-bit the same
code path as 29_cascade.py, so this run differs from the original ONLY
in the two BM25 feature columns' values.

Usage:
    python scripts/29b_cascade_refit.py

Writes: p4_out/p5_ablation_grid_v2.json, p4_out/p5_gates_v2.json,
p4_out/p5_train_features_v2.json. Original v1 files (p5_ablation_grid.json,
p5_gates.json, p5_train_features.json) are left untouched.
"""
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder
from fracture_engine import (stream_pairs, get_fragment_tokens, compute_calibration,
                             eligible_fragments, SEED as FRACTURE_SEED)

SEED = 20260722
EDGE_N = 3
BOUNDARY_WINDOW = 32
BOUNDARY_SEQ_LEN = 64
MAX_OFFSET = 3
D14_CKPT = Path("runs") / "pretrain_base" / "checkpoint.pt"
N_SYNTHETIC_TRAIN = 600
N_HARD_NEG_PER_POS = 3


def wilson_ci(hits, n, z=1.96):
    if n == 0:
        return (None, None)
    p = hits / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def recall_at_ks_wilson(ranks, n_queries, ks=(1, 10)):
    out = {}
    for k in ks:
        hits = sum(1 for r in ranks if r is not None and r <= k)
        lo, hi = wilson_ci(hits, n_queries)
        out[f"recall@{k}"] = {"mean": hits / n_queries if n_queries else None,
                              "ci_wilson": [lo, hi], "hits": hits, "n": n_queries}
    return out


def tokens_to_lines(flat_tokens):
    lines, cur = [], []
    idx = 0
    for t in flat_tokens:
        if t == "<LINE>":
            lines.append((idx, cur))
            cur = []
            idx += 1
        else:
            cur.append(t)
    lines.append((idx, cur))
    return lines


class FixedVocabBM25:
    def __init__(self, reference_token_lists, k1=1.5, b=0.75):
        from sklearn.feature_extraction.text import CountVectorizer
        self.k1, self.b = k1, b
        vec = CountVectorizer(tokenizer=lambda x: x, preprocessor=lambda x: x,
                              lowercase=False, token_pattern=None)
        TF = vec.fit_transform(reference_token_lists).tocsr()
        n_docs = TF.shape[0]
        doc_len = np.asarray(TF.sum(axis=1)).ravel()
        self.avgdl = doc_len.mean() if n_docs else 1.0
        df = np.asarray((TF > 0).sum(axis=0)).ravel()
        idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
        self.idf = np.clip(idf, 0.0, None)
        self.vocab = vec.vocabulary_

    def score(self, query_tokens, doc_tokens):
        from collections import Counter
        doc_tf = Counter(doc_tokens)
        doc_len = len(doc_tokens)
        L = self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl if self.avgdl else 1.0))
        score = 0.0
        for qt in set(query_tokens):
            vi = self.vocab.get(qt)
            if vi is None:
                continue
            tf = doc_tf.get(qt, 0)
            if tf == 0:
                continue
            idf = self.idf[vi]
            score += idf * tf * (self.k1 + 1) / (tf + L)
        return score


def build_edge_window_tokens(frags, line_index, edge_info, N):
    out = {}
    for row in frags.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        sorted_idxs = sorted(line_idxs)
        edge_idxs = sorted_idxs[:N] + sorted_idxs[-N:] if len(sorted_idxs) > 2 * N else sorted_idxs
        toks = []
        for idx in edge_idxs:
            for t, st in line_index.get((row.parent_doc, idx), []):
                if t not in ht.SPECIALS and st != "restored":
                    toks.append(t)
        out[row.fragment_id] = toks
    return out


class SeamFeaturizer:
    def __init__(self, tok, device):
        self.tok = tok
        self.device = device
        with open("configs/pretrain_config.json", encoding="utf-8") as f:
            cfg = json.load(f)
        self.model = HittiteEncoder(len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
                                    cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id).to(device)
        ckpt = torch.load(D14_CKPT, map_location=device, weights_only=False)
        self.model.load_state_dict(ckpt["model"])
        self.model.eval()
        self.line_id, self.par_id = tok.vocab["<LINE>"], tok.vocab["<PAR>"]
        self.mask_id = tok.vocab["<MASK>"]

    def _boundary_seq(self, lead_lines, trail_lines, offset):
        context_full = ht.encode_fragment_window(lead_lines)
        context = context_full[-BOUNDARY_WINDOW:] if context_full else []
        trail_from_offset = trail_lines[offset:] if offset < len(trail_lines) else []
        cont = ht.encode_fragment_window(trail_from_offset)[:BOUNDARY_WINDOW]
        if not context or not cont:
            return None
        return self.tok.encode((context + cont)[:BOUNDARY_SEQ_LEN])

    def score_pair(self, q_lines, c_lines):
        best = None
        all_flags = []
        for direction, (lead, trail) in (("query_leads", (q_lines, c_lines)),
                                         ("candidate_leads", (c_lines, q_lines))):
            for offset in range(MAX_OFFSET + 1):
                ids = self._boundary_seq(lead, trail, offset)
                if ids is None:
                    continue
                positions = [j for j, t in enumerate(ids) if t in (self.line_id, self.par_id)]
                if not positions:
                    continue
                padded = torch.tensor([ids], dtype=torch.long, device=self.device)
                pos_t = torch.tensor(positions, dtype=torch.long, device=self.device)
                with torch.no_grad():
                    hidden = self.model.encode(padded)
                    hid = hidden.expand(len(positions), -1, -1)
                    logits = self.model.boundary_logit(hid, pos_t)
                    prob = torch.sigmoid(logits).mean().item()
                if direction == "query_leads":
                    all_flags.append(prob > 0.5)
                if best is None or prob > best[0]:
                    best = (prob, direction, offset)

        if best is None:
            return 0.0, 0, 0.0, "query_leads", 0
        seam_score, best_dir, best_offset = best
        n_agree = sum(all_flags)

        lead, trail = (q_lines, c_lines) if best_dir == "query_leads" else (c_lines, q_lines)
        H = 5
        context_full = ht.encode_fragment_window(lead)
        context = context_full[-BOUNDARY_WINDOW:] if context_full else []
        trail_from_offset = trail[best_offset:] if best_offset < len(trail) else []
        trail_flat = ht.encode_fragment_window(trail_from_offset)
        if len(trail_flat) < H or not context:
            return seam_score, n_agree, 0.0, best_dir, best_offset
        true_toks = trail_flat[:H]
        right_ctx = trail_flat[H:H + BOUNDARY_WINDOW]
        true_ids = self.tok.encode(true_toks)
        with_ids = self.tok.encode(context + ["<MASK>"] * H + right_ctx)
        null_ids = self.tok.encode(["<MASK>"] * H + right_ctx)
        with_pos = list(range(len(context), len(context) + H))
        null_pos = list(range(0, H))

        def mean_lp(ids, positions):
            padded = torch.tensor([ids], dtype=torch.long, device=self.device)
            with torch.no_grad():
                hidden = self.model.encode(padded)
                logits = self.model.mlm_logits(hidden)
                lp = F.log_softmax(logits, dim=-1)
            return sum(lp[0, p, t].item() for p, t in zip(positions, true_ids)) / len(true_ids)

        lift = mean_lp(with_ids, with_pos) - mean_lp(null_ids, null_pos)
        return seam_score, n_agree, lift, best_dir, best_offset


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    frags_lookup = frags.set_index("fragment_id")
    tok = ht.Tokenizer.load()
    OUT = Path("p4_out")
    rng = random.Random(SEED)

    with open(OUT / "p5_candidates_whole.json", encoding="utf-8") as f:
        candidates = json.load(f)
    with open(OUT / "p5_query_sets.json", encoding="utf-8") as f:
        query_sets = json.load(f)
    join_by_frag = {k: set(v) for k, v in query_sets["join_by_frag"].items()}
    dup_by_frag = {k: set(v) for k, v in query_sets["dup_by_frag"].items()}
    with open(OUT / "p5_d17_scores.json", encoding="utf-8") as f:
        d17_scores = json.load(f)
    with open(OUT / "p5_d17_agreement.json", encoding="utf-8") as f:
        d17_agreement = json.load(f)
    with open(OUT / "p5_d18_scores.json", encoding="utf-8") as f:
        d18_scores = json.load(f)
    with open(OUT / "p5_hard_set.json", encoding="utf-8") as f:
        hard_set = set(json.load(f)["hard_set_query_ids"])
    with open(OUT / "p5_query_tier.json", encoding="utf-8") as f:
        query_tier = json.load(f)

    join_qids = sorted(join_by_frag.keys())
    dup_qids = sorted(dup_by_frag.keys())
    all_qids_for_features = sorted(set(join_qids) | set(dup_qids))

    print("Building BM25 whole-fragment + edge-window score lookups "
         "(A1 refit: IDF/avgdl over FULL non-test universe, not query-derived union)...")
    edge_toks_all = build_edge_window_tokens(frags, line_index, edge_info, EDGE_N)

    full_universe_ids = sorted(frags.loc[frags["main_split"] != "test", "fragment_id"].tolist())
    print(f"Full non-test universe (BM25 IDF/avgdl reference, per P5C_AMENDMENT_1.md A1): "
         f"{len(full_universe_ids)} fragments (expect 21920, matching P4B's B1 reference)")

    cand_toks_whole = [json.loads(frags_lookup.loc[c, "sign_attested"]) if c in frags_lookup.index else []
                       for c in full_universe_ids]
    query_toks_whole = [json.loads(frags_lookup.loc[q, "sign_attested"]) if q in frags_lookup.index else []
                        for q in all_qids_for_features]
    bm25_whole_scores, _ = eh.bm25_score_matrix(cand_toks_whole, query_toks_whole)
    bm25_whole_dense = bm25_whole_scores.toarray()
    cand_idx = {c: i for i, c in enumerate(full_universe_ids)}
    q_idx = {q: i for i, q in enumerate(all_qids_for_features)}

    cand_toks_edge = [edge_toks_all.get(c, []) for c in full_universe_ids]
    query_toks_edge = [edge_toks_all.get(q, []) for q in all_qids_for_features]
    bm25_edge_scores, _ = eh.bm25_score_matrix(cand_toks_edge, query_toks_edge)
    bm25_edge_dense = bm25_edge_scores.toarray()

    def dev_features(qid, cid):
        bm25_w = float(bm25_whole_dense[q_idx[qid], cand_idx[cid]]) if qid in q_idx and cid in cand_idx else 0.0
        bm25_e = float(bm25_edge_dense[q_idx[qid], cand_idx[cid]]) if qid in q_idx and cid in cand_idx else 0.0
        d17_entry = d17_scores.get(qid, {}).get(cid)
        seam_score = d17_entry["score"] if d17_entry else 0.0
        n_agree = d17_agreement.get(qid, {}).get(cid, 0)
        d18_entry = d18_scores.get(qid, {}).get(cid, {})
        d18_lift = d18_entry.get("5", 0.0) if d18_entry else 0.0
        return [bm25_w, bm25_e, seam_score, n_agree, d18_lift]

    # ================================================================
    # TRAIN-SIDE combiner training set
    # ================================================================
    print("Building TRAIN-side positives (real joins + seam-local synthetic)...")
    join_pairs_all = eh.build_join_positives(frags)
    parent_split = dict(zip(frags["parent_doc"], frags["main_split"]))
    train_join_pairs = [p for p in join_pairs_all
                        if parent_split.get(p["fragment_id_a"].split("::")[0]) == "train"]
    print(f"train-side real join pairs: {len(train_join_pairs)}")

    with open(Path("p4_out") / "fracture_calibration.json", encoding="utf-8") as f:
        calib = json.load(f)
    synth_gen = stream_pairs(frags, line_index, edge_info, calib, seed=FRACTURE_SEED + 12345,
                             mode="cut", split="train")
    synth_pairs = [next(synth_gen) for _ in range(N_SYNTHETIC_TRAIN)]
    print(f"seam-local synthetic train pairs: {len(synth_pairs)}")

    print("Building TRAIN-side hard negatives (BM25-mined, train-only corpus -- unaffected by A1)...")
    train_real = frags[(frags["main_split"] == "train") & (~frags["is_bin"])]
    train_ids = train_real["fragment_id"].tolist()
    train_toks = [json.loads(s) for s in train_real["sign_attested"]]
    train_scores, _ = eh.bm25_score_matrix(train_toks, train_toks)

    train_query_ids = sorted(set(p["fragment_id_a"] for p in train_join_pairs) |
                             set(p["fragment_id_b"] for p in train_join_pairs))
    train_positives_by_q = defaultdict(set)
    for p in train_join_pairs:
        train_positives_by_q[p["fragment_id_a"]].add(p["fragment_id_b"])
        train_positives_by_q[p["fragment_id_b"]].add(p["fragment_id_a"])

    train_id_pos = {fid: i for i, fid in enumerate(train_ids)}
    hard_negs = defaultdict(list)
    for qid in train_query_ids:
        if qid not in train_id_pos:
            continue
        qi = train_id_pos[qid]
        row = train_scores[qi].toarray().ravel()
        order = np.argsort(-row, kind="stable")
        positives = train_positives_by_q[qid]
        for i in order:
            cid = train_ids[i]
            if cid == qid or cid in positives:
                continue
            hard_negs[qid].append(cid)
            if len(hard_negs[qid]) >= N_HARD_NEG_PER_POS:
                break

    print("Fitting fixed-vocabulary BM25 scorers (whole-fragment + edge-window) "
         "over the FULL non-test universe (A1 refit)...")
    bm25_whole_scorer = FixedVocabBM25(cand_toks_whole)
    bm25_edge_scorer = FixedVocabBM25(cand_toks_edge)

    print("Scoring TRAIN-side pairs with the frozen D14 seam featurizer "
         "(real joins + synthetic + hard negatives)...")
    featurizer = SeamFeaturizer(tok, device)
    t0 = time.time()
    X, y = [], []

    for i, p in enumerate(train_join_pairs):
        fid_a, fid_b = p["fragment_id_a"], p["fragment_id_b"]
        a_lines = get_fragment_tokens(fid_a, frags_lookup, line_index, edge_info) if fid_a in edge_info else None
        b_lines = get_fragment_tokens(fid_b, frags_lookup, line_index, edge_info) if fid_b in edge_info else None
        if not a_lines or not b_lines:
            continue
        seam, n_agree, lift, _, _ = featurizer.score_pair(a_lines, b_lines)
        a_toks = json.loads(frags_lookup.loc[fid_a, "sign_attested"]) if fid_a in frags_lookup.index else []
        b_toks = json.loads(frags_lookup.loc[fid_b, "sign_attested"]) if fid_b in frags_lookup.index else []
        a_edge = edge_toks_all.get(fid_a, [])
        b_edge = edge_toks_all.get(fid_b, [])
        bm25_w = bm25_whole_scorer.score(a_toks, b_toks)
        bm25_e = bm25_edge_scorer.score(a_edge, b_edge)
        X.append([bm25_w, bm25_e, seam, n_agree, lift])
        y.append(1)
        if i % 200 == 0:
            print(f"  real join {i}/{len(train_join_pairs)}, elapsed {time.time()-t0:.0f}s")

    for i, p in enumerate(synth_pairs):
        a_lines = tokens_to_lines(p["member_a_tokens"])
        b_lines = tokens_to_lines(p["member_b_tokens"])
        seam, n_agree, lift, _, _ = featurizer.score_pair(a_lines, b_lines)
        a_toks = [t for t in p["member_a_tokens"] if t != "<LINE>"]
        b_toks = [t for t in p["member_b_tokens"] if t != "<LINE>"]
        bm25_w = bm25_whole_scorer.score(a_toks, b_toks)
        X.append([bm25_w, bm25_w, seam, n_agree, lift])
        y.append(1)
        if i % 100 == 0:
            print(f"  synthetic {i}/{len(synth_pairs)}, elapsed {time.time()-t0:.0f}s")

    print("Scoring TRAIN-side hard negatives...")
    n_neg = 0
    for qid, negs in hard_negs.items():
        q_lines = get_fragment_tokens(qid, frags_lookup, line_index, edge_info) if qid in edge_info else None
        if not q_lines:
            continue
        for cid in negs:
            c_lines = get_fragment_tokens(cid, frags_lookup, line_index, edge_info) if cid in edge_info else None
            if not c_lines:
                continue
            seam, n_agree, lift, _, _ = featurizer.score_pair(q_lines, c_lines)
            q_toks = json.loads(frags_lookup.loc[qid, "sign_attested"])
            c_toks = json.loads(frags_lookup.loc[cid, "sign_attested"])
            q_edge = edge_toks_all.get(qid, [])
            c_edge = edge_toks_all.get(cid, [])
            bm25_w = bm25_whole_scorer.score(q_toks, c_toks)
            bm25_e = bm25_edge_scorer.score(q_edge, c_edge)
            X.append([bm25_w, bm25_e, seam, n_agree, lift])
            y.append(0)
            n_neg += 1
    print(f"Train set: {sum(y)} positives, {n_neg} negatives. Featurization took {time.time()-t0:.0f}s.")

    X = np.array(X)
    y = np.array(y)
    with open(OUT / "p5_train_features_v2.json", "w", encoding="utf-8") as f:
        json.dump({"X": X.tolist(), "y": y.tolist()}, f)

    combiner = LogisticRegression(max_iter=1000, random_state=SEED)
    combiner.fit(X, y)
    print("Combiner coefficients (bm25_whole, bm25_edge, seam_score, n_agree, d18_lift):",
         combiner.coef_.tolist(), "intercept:", combiner.intercept_.tolist())

    # ================================================================
    # DEV evaluation: ablation grid + gates
    # ================================================================
    print("Scoring dev pairs for the ablation grid...")

    def rank_by(score_fn, qids_subset, positives_by_query):
        ranks = []
        for qid in qids_subset:
            cand_list = candidates.get(qid, [])
            if not cand_list:
                ranks.append(None)
                continue
            scores = [score_fn(qid, cid) for cid in cand_list]
            order = np.argsort(-np.array(scores))
            ranked = [cand_list[i] for i in order]
            positives = positives_by_query.get(qid, set())
            rank = None
            for i, cid in enumerate(ranked):
                if cid in positives:
                    rank = i + 1
                    break
            ranks.append(rank)
        return ranks

    def bm25_alone(qid, cid):
        return dev_features(qid, cid)[0]

    def plus_d17(qid, cid):
        f = dev_features(qid, cid)
        return f[0] + f[2]

    def plus_d18(qid, cid):
        f = dev_features(qid, cid)
        return f[0] + f[4]

    def full_cascade(qid, cid):
        f = dev_features(qid, cid)
        return float(combiner.predict_proba([f])[0, 1])

    rows = {}
    for name, score_fn in (("bm25_alone", bm25_alone), ("plus_d17", plus_d17),
                           ("plus_d18", plus_d18), ("full_cascade", full_cascade)):
        print(f"  ablation row: {name}")
        join_ranks = rank_by(score_fn, join_qids, join_by_frag)
        hard_ranks = rank_by(score_fn, list(hard_set), join_by_frag)
        dup_ranks = rank_by(score_fn, dup_qids, dup_by_frag)
        row = {
            "all_joins": recall_at_ks_wilson(join_ranks, len(join_qids)),
            "hard_set": recall_at_ks_wilson(hard_ranks, len(hard_set)),
            "duplicates": recall_at_ks_wilson(dup_ranks, len(dup_qids)),
        }
        for tier in ("A", "B", "C"):
            tier_qids = [q for q in join_qids if query_tier.get(q) == tier]
            if tier_qids:
                tier_ranks = rank_by(score_fn, tier_qids, join_by_frag)
                row[f"tier_{tier}"] = recall_at_ks_wilson(tier_ranks, len(tier_qids))
        rows[name] = row

    with open(OUT / "p5_ablation_grid_v2.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)

    # ---- verification gate (A1) ----
    bm25_r1 = rows["bm25_alone"]["all_joins"]["recall@1"]["mean"]
    bm25_r10 = rows["bm25_alone"]["all_joins"]["recall@10"]["mean"]
    print(f"\nA1 VERIFICATION GATE: refit bm25_alone all_joins recall@1={bm25_r1:.4f} "
         f"recall@10={bm25_r10:.4f} (target: 0.6760 / 0.8080, P4B B1 reference)")
    gate_pass = abs(bm25_r1 - 0.676) < 5e-5 and abs(bm25_r10 - 0.808) < 5e-5
    print(f"A1 gate: {'PASS' if gate_pass else 'FAIL -- STOP, do not proceed'}")

    # ---- gates G1-G4 ----
    casc_r1 = rows["full_cascade"]["all_joins"]["recall@1"]["mean"]
    casc_r10 = rows["full_cascade"]["all_joins"]["recall@10"]["mean"]
    g1_pass = casc_r1 > bm25_r1 and casc_r10 > bm25_r10

    hard_bm25_r10 = rows["bm25_alone"]["hard_set"]["recall@10"]["mean"]
    hard_casc_r10 = rows["full_cascade"]["hard_set"]["recall@10"]["mean"]
    g2_pass = hard_casc_r10 > hard_bm25_r10

    dup_bm25_r1 = rows["bm25_alone"]["duplicates"]["recall@1"]["mean"]
    dup_casc_r1 = rows["full_cascade"]["duplicates"]["recall@1"]["mean"]
    g4_pass = dup_casc_r1 >= dup_bm25_r1 - 0.02

    gates = {
        "A1_verification_gate": {"pass": bool(gate_pass), "bm25_recall@1": bm25_r1, "bm25_recall@10": bm25_r10,
                                 "target_recall@1": 0.676, "target_recall@10": 0.808,
                                 "n_universe": len(full_universe_ids)},
        "G1_primary": {"pass": bool(g1_pass), "bm25_recall@1": bm25_r1, "cascade_recall@1": casc_r1,
                      "bm25_recall@10": bm25_r10, "cascade_recall@10": casc_r10},
        "G2_hard_set": {"pass": bool(g2_pass), "bm25_recall@10": hard_bm25_r10, "cascade_recall@10": hard_casc_r10,
                       "n_hard": len(hard_set)},
        "G3_per_tier": rows["full_cascade"],
        "G4_no_regression": {"pass": bool(g4_pass), "bm25_recall@1": dup_bm25_r1, "cascade_recall@1": dup_casc_r1},
    }
    with open(OUT / "p5_gates_v2.json", "w", encoding="utf-8") as f:
        json.dump(gates, f, ensure_ascii=False, indent=2, default=str)

    print("Gates (v2, corrected baseline):", json.dumps(gates, indent=2, default=str)[:3000])
    print("D19 refit done. p5_ablation_grid_v2.json, p5_gates_v2.json, p5_train_features_v2.json written.")


if __name__ == "__main__":
    main()
