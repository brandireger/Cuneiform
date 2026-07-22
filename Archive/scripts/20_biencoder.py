#!/usr/bin/env python3
"""
20_biencoder.py -- P4 D15: contrastive bi-encoder retrieval model.

Usage:
    python scripts/20_biencoder.py [--config biencoder_config.json] [--tag base]
                            [--mix balanced|real_only|synthetic_only]
                            [--resume] [--smoke_steps N]

Initializes from a D14 checkpoint (config.init_checkpoint), fine-tunes
with InfoNCE contrastive loss, mean-pooled whole-fragment embeddings.

Positive-pair mix (config.positive_mix, sampled per training example):
  - synthetic_cut:    fracture_engine.stream_pairs(mode='cut', split='train')
  - self_supervised:  fracture_engine.stream_pairs(mode='self_supervised')
  - real_duplicate:   eh.build_duplicate_positives(frags, ..., split='train')
  - real_join:        eh.build_join_positives(frags), parent main_split=='train'
Negatives: in-batch (all other examples' B-side embeddings) + BM25-mined
hard negatives (looked up by the underlying real fragment_id -- the
source fragment for synthetic pairs, fragment_id_a for real pairs),
mined once at startup over the TRAIN real (non-bin) fragment index.

SCOPE DECISION (spec left exact ablation-grid mechanics underspecified,
documented here rather than guessed silently, per this project's
established practice -- see eval_harness.py's docstring for the same
pattern): the "pooling variant" axis of the ablation grid (whole-
fragment mean-pool vs line/passage-level max-over-line-pairs) is
implemented as an EVAL-TIME scoring choice over ONE trained encoder,
not a separate training objective -- HittiteEncoder.line_embeddings()
reuses the same forward pass and mean-pools between <LINE> markers, per
the matrix model's "aggregate over aligned row-pairs" principle. Only
the "positive-mix ratios" axis requires separate training runs (--mix
selects a named preset; each is its own tagged run under runs/).

Engineering law (same as 19_pretrain.py): checkpoint at natural units,
atomic writes, full resumability (model+optimizer+step+RNG state),
seeds+git-hash+corpus-version logged. TRAIN-side + discovery-pool
ATTESTED sequences only for gradient updates; DEV used only for the
three dev gates below, NEVER for training; TEST never touched.

Dev gates (evaluate_dev_gates(), run at eval_every and at the end):
  1. dev duplicates: real dev-side duplicate pairs, recall@1 vs BM25
     baseline computed over the same dev candidate pool.
  2. dev real joins: real dev-side join pairs, recall@k with CIs.
  3. dev synthetic held-out joins: fracture_engine.stream_pairs(
     split='dev') -- same mechanics as training positives but from
     DEV-side source fragments, NEVER used for gradient updates.
Each gate is reported under BOTH pooling variants (mean / line_max).
"""

import argparse
import csv
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder
from fracture_engine import (
    SEED as FRACTURE_SEED, compute_calibration, stream_pairs, eligible_fragments,
)

MIX_PRESETS = {
    "balanced": {"synthetic_cut": 0.3, "self_supervised": 0.2,
                 "real_duplicate": 0.3, "real_join": 0.2},
    "real_only": {"synthetic_cut": 0.0, "self_supervised": 0.0,
                  "real_duplicate": 0.6, "real_join": 0.4},
    "synthetic_only": {"synthetic_cut": 0.6, "self_supervised": 0.4,
                        "real_duplicate": 0.0, "real_join": 0.0},
}

DEFAULT_CONFIG = {
    "seed": 20260722,
    "seq_len": 512,
    "batch_size": 16,
    "lr": 1e-4, "warmup_steps": 200, "max_steps": 5000,
    "checkpoint_every": 250, "eval_every": 250,
    "wall_clock_budget_hours": 12,
    "temperature": 0.05,
    "hard_neg_k": 4,
    "hard_neg_pool_k": 20,
    "positive_mix": "balanced",
    "init_checkpoint": str(Path("runs") / "pretrain_base" / "checkpoint.pt"),
    "dev_synthetic_n": 300,
    "n_layers": 6, "d_model": 384, "n_heads": 6, "d_ff": 1536, "dropout": 0.1,
}


def get_git_commit():
    try:
        result = subprocess.run([r"C:\Program Files\Git\bin\git.exe", "rev-parse", "HEAD"],
                                 capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"N/A: {e}"


def load_config(path, mix_override=None):
    cfg = dict(DEFAULT_CONFIG)
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    if mix_override:
        cfg["positive_mix"] = mix_override
    if isinstance(cfg["positive_mix"], str):
        cfg["positive_mix_name"] = cfg["positive_mix"]
        cfg["positive_mix"] = MIX_PRESETS[cfg["positive_mix"]]
    else:
        cfg["positive_mix_name"] = "custom"
    return cfg


# ---------------------------------------------------------------- data pools

def load_encoded_pool(tok, frags, line_index, edge_info, seq_len):
    """fragment_id -> {ids, cth, main_split, is_bin}. TRAIN + discovery
    + dev only (test never encoded here)."""
    out = {}
    for row in frags.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        if row.main_split not in ("train", "dev") and not row.is_bin:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        seq = ht.build_structured_sequence_attested(
            row.parent_doc, line_idxs, line_index, top_lost, bot_lost, by_line)
        ids = tok.encode(seq)[:seq_len]
        if len(ids) < 4:
            continue
        out[row.fragment_id] = {"ids": ids, "cth": row.cth,
                                 "main_split": row.main_split, "is_bin": bool(row.is_bin)}
    return out


def filter_join_pairs_by_split(join_pairs, frags, split):
    parent_split = dict(zip(frags["parent_doc"], frags["main_split"]))
    out = []
    for p in join_pairs:
        parent = p["fragment_id_a"].split("::")[0]
        if parent_split.get(parent) == split:
            out.append(p)
    return out


def build_hard_neg_index(frags, pool_k=20):
    """BM25-mined hard negatives over TRAIN real (non-bin) fragments,
    keyed by fragment_id -> [neg_fid, ...] (excludes self)."""
    train_real = frags[(frags["main_split"] == "train") & (~frags["is_bin"])]
    ids = train_real["fragment_id"].tolist()
    toks = [json.loads(s) for s in train_real["sign_attested"]]
    scores, _ = eh.bm25_score_matrix(toks, toks)
    out = {}
    for qi, qid in enumerate(ids):
        row = scores[qi].toarray().ravel()
        order = np.argsort(-row, kind="stable")
        negs = [ids[i] for i in order if ids[i] != qid][:pool_k]
        out[qid] = negs
    return out, set(ids)


# ---------------------------------------------------------------- sampling

class PositiveSampler:
    """Wraps the four positive-pair sources behind one sample() call
    that returns (ids_a, ids_b, query_fid) using the configured mix
    ratios. Streaming sources (fracture engine) are generators created
    once and pulled from lazily; real-pair sources are lists sampled
    uniformly at random each call."""

    def __init__(self, cfg, tok, frags, line_index, edge_info, calib, encoded_pool, seed):
        self.cfg = cfg
        self.tok = tok
        self.seq_len = cfg["seq_len"]
        self.encoded_pool = encoded_pool
        self.rng = random.Random(seed)

        mix = cfg["positive_mix"]
        self.sources = [k for k, v in mix.items() if v > 0]
        self.weights = [mix[k] for k in self.sources]

        if mix.get("synthetic_cut", 0) > 0:
            self.gen_cut = stream_pairs(frags, line_index, edge_info, calib,
                                         seed=seed, mode="cut", split="train")
        if mix.get("self_supervised", 0) > 0:
            self.gen_ssl = stream_pairs(frags, line_index, edge_info, calib,
                                         seed=seed + 1, mode="self_supervised")

        join_pairs = eh.build_join_positives(frags)
        self.join_pair_set = {frozenset((p["fragment_id_a"], p["fragment_id_b"])) for p in join_pairs}
        self.real_join_train = filter_join_pairs_by_split(join_pairs, frags, "train")
        self.real_dup_train = eh.build_duplicate_positives(frags, self.join_pair_set, split="train")

    def _encode_tokens(self, toks):
        return self.tok.encode(toks)[:self.seq_len]

    def sample(self):
        src = self.rng.choices(self.sources, weights=self.weights, k=1)[0]
        if src == "synthetic_cut":
            p = next(self.gen_cut)
            a = self._encode_tokens(p["member_a_tokens"])
            b = self._encode_tokens(p["member_b_tokens"])
            return a, b, p["source_fragment_id"]
        if src == "self_supervised":
            p = next(self.gen_ssl)
            a = self._encode_tokens(p["view_a_tokens"])
            b = self._encode_tokens(p["view_b_tokens"])
            return a, b, p["source_fragment_id"]
        if src == "real_duplicate":
            pool = self.real_dup_train
        else:  # real_join
            pool = self.real_join_train
        if not pool:
            return self.sample()  # fall through if this source is empty
        p = pool[self.rng.randrange(len(pool))]
        fid_a, fid_b = p["fragment_id_a"], p["fragment_id_b"]
        if fid_a not in self.encoded_pool or fid_b not in self.encoded_pool:
            return self.sample()
        return self.encoded_pool[fid_a]["ids"], self.encoded_pool[fid_b]["ids"], fid_a


def pad_batch(seqs, pad_id, max_len=None):
    max_len = max_len or max(len(s) for s in seqs)
    out = torch.full((len(seqs), max_len), pad_id, dtype=torch.long)
    for i, s in enumerate(seqs):
        out[i, :len(s)] = torch.tensor(s[:max_len], dtype=torch.long)
    return out


def sample_contrastive_batch(sampler, hard_neg_index, encoded_pool, cfg, device, tok):
    batch_a, batch_b, query_fids = [], [], []
    for _ in range(cfg["batch_size"]):
        a, b, qfid = sampler.sample()
        batch_a.append(a)
        batch_b.append(b)
        query_fids.append(qfid)

    extra_neg_ids = []
    seen = set(query_fids)
    for qfid in query_fids:
        for neg_fid in hard_neg_index.get(qfid, [])[:cfg["hard_neg_k"]]:
            if neg_fid in seen or neg_fid not in encoded_pool:
                continue
            seen.add(neg_fid)
            extra_neg_ids.append(encoded_pool[neg_fid]["ids"])

    max_len = min(max(len(s) for s in batch_a + batch_b + (extra_neg_ids or [[0]])), cfg["seq_len"])
    a_ids = pad_batch(batch_a, tok.pad_id, max_len).to(device)
    b_ids = pad_batch(batch_b, tok.pad_id, max_len).to(device)
    neg_ids = pad_batch(extra_neg_ids, tok.pad_id, max_len).to(device) if extra_neg_ids else None
    return a_ids, b_ids, neg_ids


def info_nce_loss(emb_a, emb_b, extra_neg_emb, temperature):
    emb_a = F.normalize(emb_a, dim=-1)
    emb_b = F.normalize(emb_b, dim=-1)
    B = emb_a.shape[0]
    labels = torch.arange(B, device=emb_a.device)

    logits_ab = emb_a @ emb_b.t() / temperature
    if extra_neg_emb is not None and extra_neg_emb.shape[0] > 0:
        extra = F.normalize(extra_neg_emb, dim=-1)
        logits_ab = torch.cat([logits_ab, emb_a @ extra.t() / temperature], dim=1)
    loss_a = F.cross_entropy(logits_ab, labels)

    logits_ba = emb_b @ emb_a.t() / temperature  # hard negs are A-side only, by construction
    loss_b = F.cross_entropy(logits_ba, labels)
    return (loss_a + loss_b) / 2


# ---------------------------------------------------------------- checkpointing

def save_checkpoint(path, model, optimizer, step, cfg, local_rng, np_rng_state, torch_rng_state,
                     init_checkpoint_step):
    tmp = Path(str(path) + ".tmp")
    cuda_rng_state = torch.cuda.get_rng_state() if torch.cuda.is_available() else None
    torch.save({
        "step": step, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
        "config": cfg, "local_rng_state": local_rng.getstate(), "np_rng_state": np_rng_state,
        "torch_rng_state": torch_rng_state.cpu(),
        "cuda_rng_state": cuda_rng_state.cpu() if cuda_rng_state is not None else None,
        "git_commit": get_git_commit(), "corpus_version": "TLHdig_0.2.0-beta",
        "init_checkpoint_step": init_checkpoint_step,
    }, tmp)
    os.replace(tmp, path)


def load_checkpoint(path, model, optimizer, local_rng, device):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    optimizer.load_state_dict(ckpt["optimizer"])
    local_rng.setstate(ckpt["local_rng_state"])
    np.random.set_state(ckpt["np_rng_state"])
    torch.set_rng_state(ckpt["torch_rng_state"].cpu())
    if ckpt.get("cuda_rng_state") is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state(ckpt["cuda_rng_state"].cpu())
    return ckpt["step"]


def init_from_pretrain(model, path, device):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    return ckpt["step"]


# ---------------------------------------------------------------- embedding / dense retrieval

@torch.no_grad()
def embed_all_mean(model, fid_list, encoded_pool, tok, device, seq_len, batch_size=32):
    model.eval()
    out = {}
    for i in range(0, len(fid_list), batch_size):
        chunk = fid_list[i:i + batch_size]
        seqs = [encoded_pool[f]["ids"] for f in chunk]
        ids = pad_batch(seqs, tok.pad_id, min(max(len(s) for s in seqs), seq_len)).to(device)
        emb = model.mean_pool(ids).cpu().numpy()
        for f, e in zip(chunk, emb):
            out[f] = e
    model.train()
    return out


@torch.no_grad()
def embed_all_lines(model, fid_list, encoded_pool, tok, device, seq_len, batch_size=32):
    model.eval()
    out = {}
    line_id = tok.vocab["<LINE>"]
    for i in range(0, len(fid_list), batch_size):
        chunk = fid_list[i:i + batch_size]
        seqs = [encoded_pool[f]["ids"] for f in chunk]
        ids = pad_batch(seqs, tok.pad_id, min(max(len(s) for s in seqs), seq_len)).to(device)
        line_embs = model.line_embeddings(ids, line_id)
        for f, e in zip(chunk, line_embs):
            out[f] = F.normalize(e, dim=-1).cpu().numpy()
    model.train()
    return out


def cosine_score_matrix(query_embs, cand_embs):
    q = query_embs / (np.linalg.norm(query_embs, axis=1, keepdims=True) + 1e-9)
    c = cand_embs / (np.linalg.norm(cand_embs, axis=1, keepdims=True) + 1e-9)
    return q @ c.T


def run_dense_retrieval(query_ids, query_embs, cand_ids, cand_embs, positives_by_query, ks=(1, 5, 10, 100)):
    scores = cosine_score_matrix(query_embs, cand_embs)
    per_query = []
    for qi, qid in enumerate(query_ids):
        positives = positives_by_query.get(qid, set())
        if not positives:
            continue
        ranked = eh.top_k_ranking(scores[qi], cand_ids, exclude_id=qid)
        m = eh.recall_and_rank(ranked, positives, ks=ks)
        m["query_id"] = qid
        m["top1"] = ranked[0] if ranked else None
        per_query.append(m)
    return per_query, eh.aggregate_metrics(per_query, ks=ks)


def run_line_max_retrieval(query_ids, query_line_embs, cand_ids, cand_line_embs, positives_by_query, ks=(1, 5, 10, 100)):
    """Max-over-line-pairs cosine score, per the matrix model's
    multi-row-consistency framing (here reduced to a max, not full
    aggregation, as the tractable eval-time proxy)."""
    cand_arr = [cand_line_embs[c] for c in cand_ids]
    per_query = []
    for qid in query_ids:
        positives = positives_by_query.get(qid, set())
        if not positives or qid not in query_line_embs:
            continue
        qlines = query_line_embs[qid]  # (n_q, D)
        scores = np.full(len(cand_ids), -1.0)
        for ci, clines in enumerate(cand_arr):
            if cand_ids[ci] == qid:
                continue
            sim = qlines @ clines.T
            scores[ci] = float(sim.max()) if sim.size else -1.0
        ranked = eh.top_k_ranking(scores, cand_ids, exclude_id=qid)
        m = eh.recall_and_rank(ranked, positives, ks=ks)
        m["query_id"] = qid
        m["top1"] = ranked[0] if ranked else None
        per_query.append(m)
    return per_query, eh.aggregate_metrics(per_query, ks=ks)


# ---------------------------------------------------------------- dev gates

def evaluate_dev_gates(model, tok, cfg, frags, line_index, edge_info, calib,
                        encoded_pool, join_pair_set, device, n_batches_note=""):
    dev_real = frags[(frags["main_split"] == "dev") & (~frags["is_bin"]) &
                      (frags["fragment_id"].isin(encoded_pool.keys()))]
    dev_ids = dev_real["fragment_id"].tolist()
    if len(dev_ids) < 4:
        return {"note": "too few dev fragments for dense dev gates"}

    mean_embs = embed_all_mean(model, dev_ids, encoded_pool, tok, device, cfg["seq_len"])
    line_embs = embed_all_lines(model, dev_ids, encoded_pool, tok, device, cfg["seq_len"])
    mean_mat = np.stack([mean_embs[f] for f in dev_ids])

    out = {}

    # ---- gate 1: dev duplicates, dense (mean + line_max) vs BM25
    dup_pairs = eh.build_duplicate_positives(frags, join_pair_set, split="dev")
    dup_by_frag = {}
    for p in dup_pairs:
        if p["fragment_id_a"] not in encoded_pool or p["fragment_id_b"] not in encoded_pool:
            continue
        dup_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        dup_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
    if dup_by_frag:
        qids = [q for q in dup_by_frag if q in dev_ids]
        qmat = np.stack([mean_embs[f] for f in qids]) if qids else np.zeros((0, mean_mat.shape[1]))
        _, agg_mean = run_dense_retrieval(qids, qmat, dev_ids, mean_mat, dup_by_frag)
        _, agg_line = run_line_max_retrieval(qids, line_embs, dev_ids, line_embs, dup_by_frag)
        qtoks = [json.loads(s) for s in dev_real.set_index("fragment_id").loc[qids, "sign_attested"]]
        cand_toks = [json.loads(s) for s in dev_real["sign_attested"]]
        _, agg_bm25 = eh.run_retrieval(qids, qtoks, dev_ids, cand_toks, dup_by_frag, method="bm25")
        out["dev_duplicates"] = {"mean_pool": agg_mean, "line_max": agg_line, "bm25_baseline": agg_bm25}
    else:
        out["dev_duplicates"] = {"note": "no dev-side duplicate pairs with both members encoded"}

    # ---- gate 2: dev real joins, dense (mean + line_max)
    join_pairs = eh.build_join_positives(frags)
    dev_joins = filter_join_pairs_by_split(join_pairs, frags, "dev")
    join_by_frag = {}
    for p in dev_joins:
        if p["fragment_id_a"] not in encoded_pool or p["fragment_id_b"] not in encoded_pool:
            continue
        join_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        join_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
    if join_by_frag:
        qids = [q for q in join_by_frag if q in dev_ids]
        qmat = np.stack([mean_embs[f] for f in qids]) if qids else np.zeros((0, mean_mat.shape[1]))
        _, agg_mean = run_dense_retrieval(qids, qmat, dev_ids, mean_mat, join_by_frag)
        _, agg_line = run_line_max_retrieval(qids, line_embs, dev_ids, line_embs, join_by_frag)
        out["dev_real_joins"] = {"mean_pool": agg_mean, "line_max": agg_line}
    else:
        out["dev_real_joins"] = {"note": "no dev-side real join pairs with both members encoded"}

    # ---- gate 3: dev synthetic held-out joins
    gen = stream_pairs(frags, line_index, edge_info, calib, seed=FRACTURE_SEED + 777,
                        mode="cut", split="dev")
    synth_pairs = [next(gen) for _ in range(cfg["dev_synthetic_n"])]
    if synth_pairs:
        synth_a_ids = {f"synA{i}": tok.encode(p["member_a_tokens"])[:cfg["seq_len"]]
                       for i, p in enumerate(synth_pairs)}
        synth_b_ids = {f"synB{i}": tok.encode(p["member_b_tokens"])[:cfg["seq_len"]]
                       for i, p in enumerate(synth_pairs)}
        synth_pool = {**synth_a_ids, **synth_b_ids}
        synth_cand_ids = list(synth_pool.keys())
        synth_mean = embed_all_mean(model, synth_cand_ids,
                                     {k: {"ids": v} for k, v in synth_pool.items()},
                                     tok, device, cfg["seq_len"])
        synth_mean_mat = np.stack([synth_mean[f] for f in synth_cand_ids])
        synth_pos = {f"synA{i}": {f"synB{i}"} for i in range(len(synth_pairs))}
        qids = list(synth_pos.keys())
        qmat = np.stack([synth_mean[f] for f in qids])
        _, agg_synth = run_dense_retrieval(qids, qmat, synth_cand_ids, synth_mean_mat, synth_pos)
        out["dev_synthetic_joins"] = {"mean_pool": agg_synth, "n_pairs": len(synth_pairs)}
    else:
        out["dev_synthetic_joins"] = {"note": "no synthetic dev pairs generated"}

    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/biencoder_config.json")
    ap.add_argument("--tag", default="base")
    ap.add_argument("--mix", default=None, choices=list(MIX_PRESETS.keys()))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke_steps", type=int, default=None,
                     help="Override max_steps for a quick mechanical smoke test.")
    args = ap.parse_args()

    cfg = load_config(args.config, mix_override=args.mix)
    if args.smoke_steps:
        cfg["max_steps"] = args.smoke_steps
        cfg["checkpoint_every"] = max(1, args.smoke_steps // 2)
        cfg["eval_every"] = max(1, args.smoke_steps // 2)
    if not Path(args.config).exists():
        with open(args.config, "w", encoding="utf-8") as f:
            json.dump({**cfg, "positive_mix": cfg["positive_mix_name"]}, f, ensure_ascii=False, indent=2)

    tag = f"{args.tag}_{cfg['positive_mix_name']}"
    run_dir = Path("runs") / f"biencoder_{tag}"
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = run_dir / "checkpoint.pt"
    csv_path = run_dir / "loss_curve.csv"

    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}. Run dir: {run_dir}. Mix: {cfg['positive_mix_name']} {cfg['positive_mix']}")

    tok = ht.Tokenizer.load()
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    print("Loading encoded pool (train+discovery+dev, ATTESTED)...")
    encoded_pool = load_encoded_pool(tok, frags, line_index, edge_info, cfg["seq_len"])
    print(f"encoded_pool: {len(encoded_pool)} fragments")

    with open(Path("p4_out") / "fracture_calibration.json", encoding="utf-8") as f:
        calib = json.load(f)

    print("Building hard-negative index (BM25 over TRAIN real fragments)...")
    hard_neg_index, _ = build_hard_neg_index(frags, cfg["hard_neg_pool_k"])
    print(f"hard_neg_index: {len(hard_neg_index)} queries")

    sampler = PositiveSampler(cfg, tok, frags, line_index, edge_info, calib, encoded_pool,
                               seed=cfg["seed"] + 1)
    join_pair_set = sampler.join_pair_set

    model = HittiteEncoder(len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
                           cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id).to(device)

    init_step = None
    if not args.resume:
        init_path = Path(cfg["init_checkpoint"])
        if init_path.exists():
            init_step = init_from_pretrain(model, init_path, device)
            print(f"Initialized from D14 checkpoint @ pretrain step {init_step} ({init_path})")
        else:
            print(f"WARNING: init_checkpoint {init_path} not found -- training from random init.")

    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["lr"])
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}")

    rng = random.Random(cfg["seed"] + 2)

    last_completed_step = -1
    if args.resume and ckpt_path.exists():
        last_completed_step = load_checkpoint(ckpt_path, model, optimizer, rng, device)
        print(f"Resumed after step {last_completed_step}")
    start_step = last_completed_step + 1

    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["step", "loss", "elapsed_s"])

    t0 = time.time()
    model.train()
    budget_s = cfg["wall_clock_budget_hours"] * 3600
    step = start_step - 1

    for step in range(start_step, cfg["max_steps"]):
        if time.time() - t0 > budget_s:
            print(f"Wall-clock budget ({cfg['wall_clock_budget_hours']}h) reached at step {step}.")
            break
        lr = cfg["lr"] * min(1.0, (step + 1) / max(1, cfg["warmup_steps"]))
        for g in optimizer.param_groups:
            g["lr"] = lr

        a_ids, b_ids, neg_ids = sample_contrastive_batch(
            sampler, hard_neg_index, encoded_pool, cfg, device, tok)
        emb_a = model.mean_pool(a_ids)
        emb_b = model.mean_pool(b_ids)
        emb_neg = model.mean_pool(neg_ids) if neg_ids is not None else None
        loss = info_nce_loss(emb_a, emb_b, emb_neg, cfg["temperature"])

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % 20 == 0:
            print(f"step {step}: loss={loss.item():.4f} elapsed={time.time()-t0:.0f}s")

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([step, loss.item(), time.time() - t0])

        if step % cfg["eval_every"] == 0 and step > start_step:
            gates = evaluate_dev_gates(model, tok, cfg, frags, line_index, edge_info, calib,
                                       encoded_pool, join_pair_set, device)
            with open(run_dir / f"dev_gates_step{step}.json", "w", encoding="utf-8") as f:
                json.dump(gates, f, ensure_ascii=False, indent=2, default=str)
            print(f"  [dev gates @ {step}] written to dev_gates_step{step}.json")

        if step % cfg["checkpoint_every"] == 0 and step > start_step:
            save_checkpoint(ckpt_path, model, optimizer, step, cfg, rng,
                           np.random.get_state(), torch.get_rng_state(), init_step)
            print(f"  checkpoint saved @ step {step}")

    save_checkpoint(ckpt_path, model, optimizer, step, cfg, rng,
                   np.random.get_state(), torch.get_rng_state(), init_step)
    print(f"Final checkpoint saved @ step {step}.")

    print("Running final dev-gate evaluation...")
    final_gates = evaluate_dev_gates(model, tok, cfg, frags, line_index, edge_info, calib,
                                     encoded_pool, join_pair_set, device)
    with open(run_dir / "dev_gates_final.json", "w", encoding="utf-8") as f:
        json.dump(final_gates, f, ensure_ascii=False, indent=2, default=str)
    print(json.dumps(final_gates, indent=2, default=str)[:3000])
    print("Done.")


if __name__ == "__main__":
    main()
