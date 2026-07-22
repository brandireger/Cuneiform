#!/usr/bin/env python3
"""
19_pretrain.py -- P4 D14: encoder pre-training.

Usage:
    python scripts/19_pretrain.py [--config pretrain_config.json] [--tag base] [--resume]

Engineering law (CLAUDE.md / P4_NEURAL_SPEC.md): checkpoint at natural
units (every config.checkpoint_every steps), atomic writes (write to
.tmp then os.replace -- never a half-written checkpoint), resumable
(model+optimizer+step+RNG state all saved/restored), seeds + git hash
+ corpus version logged in every artifact.

Data: TRAIN-side + discovery-pool ATTESTED sequences only (never
FULL by default, never dev/test for gradient updates). Dev-side used
for loss curves / early stopping only.
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
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder, apply_span_masking, find_boundary_positions, build_boundary_example

DEFAULT_CONFIG = {
    "seed": 20260722,
    "n_layers": 6, "d_model": 384, "n_heads": 6, "d_ff": 1536,
    "seq_len": 512, "dropout": 0.1,
    "mlm_weight": 1.0, "boundary_weight": 1.0,
    "mask_rate": 0.15, "gap_mode_prob": 0.3, "max_span_len": 20,
    "boundary_window": 32, "boundary_seq_len": 64,
    "mlm_batch_size": 16, "boundary_batch_size": 16,
    "lr": 3e-4, "warmup_steps": 500, "max_steps": 20000,
    "checkpoint_every": 500, "eval_every": 500,
    "wall_clock_budget_hours": 24,
}


def get_git_commit():
    try:
        result = subprocess.run([r"C:\Program Files\Git\bin\git.exe", "rev-parse", "HEAD"],
                                 capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"N/A: {e}"


def load_config(path):
    cfg = dict(DEFAULT_CONFIG)
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def load_pretrain_data(tok, frags, line_index, edge_info, seq_len):
    """Returns dict split -> list of dicts {fragment_id, cth, genre_band, ids}."""
    out = {"train": [], "discovery": [], "dev": []}
    for row in frags.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        if row.main_split == "train":
            bucket = "train"
        elif row.is_bin:
            bucket = "discovery"
        elif row.main_split == "dev":
            bucket = "dev"
        else:
            continue  # test-side: NEVER touched by P4
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        seq = ht.build_structured_sequence_attested(
            row.parent_doc, line_idxs, line_index, top_lost, bot_lost, by_line)
        ids = tok.encode(seq)[:seq_len]
        if len(ids) < 4:
            continue
        out[bucket].append({"fragment_id": row.fragment_id, "cth": row.cth,
                            "genre_band": row.genre_band, "ids": ids})
    return out


def pad_batch(seqs, pad_id, max_len=None):
    max_len = max_len or max(len(s) for s in seqs)
    out = torch.full((len(seqs), max_len), pad_id, dtype=torch.long)
    for i, s in enumerate(seqs):
        out[i, :len(s)] = torch.tensor(s[:max_len], dtype=torch.long)
    return out


def sample_mlm_batch(pool, tok, cfg, rng, del_span_lengths, device):
    specials_ids = set(tok.encode(ht.SPECIALS))
    mask_id, gap_id = tok.vocab["<MASK>"], tok.vocab["<GAP>"]
    batch_ids, batch_labels = [], []
    for _ in range(cfg["mlm_batch_size"]):
        ex = pool[rng.randrange(len(pool))]
        corrupted, labels = apply_span_masking(
            ex["ids"], mask_id, gap_id, len(tok.vocab), specials_ids,
            del_span_lengths, rng, cfg["mask_rate"], cfg["gap_mode_prob"], cfg["max_span_len"])
        batch_ids.append(corrupted[:cfg["seq_len"]])
        batch_labels.append(labels[:cfg["seq_len"]])
    input_ids = pad_batch(batch_ids, tok.pad_id, cfg["seq_len"]).to(device)
    labels = pad_batch(batch_labels, -100, cfg["seq_len"]).to(device)
    return input_ids, labels


def sample_boundary_batch(pool, tok, cfg, rng, device):
    line_id, par_id = tok.vocab["<LINE>"], tok.vocab["<PAR>"]
    by_genre = {}
    for ex in pool:
        by_genre.setdefault(ex["genre_band"], []).append(ex)

    contexts, conts, labels, tiers = [], [], [], []
    attempts = 0
    while len(contexts) < cfg["boundary_batch_size"] and attempts < cfg["boundary_batch_size"] * 20:
        attempts += 1
        ex = pool[rng.randrange(len(pool))]
        boundaries = find_boundary_positions(ex["ids"], line_id, par_id)
        if not boundaries:
            continue
        bp = boundaries[rng.randrange(len(boundaries))]
        neg_pools = {
            "cross_genre": (by_genre.get(ex["genre_band"], pool), ex["cth"]),
            "random": (pool, ex["cth"]),
        }
        result = build_boundary_example(ex["ids"], bp, boundaries, rng, neg_pools,
                                         window=cfg["boundary_window"])
        if result is None:
            continue
        ctx, cont, label, tier = result
        contexts.append(ctx)
        conts.append(cont)
        labels.append(label)
        tiers.append(tier)

    if not contexts:
        return None
    seqs = [c + k for c, k in zip(contexts, conts)]
    boundary_positions = [len(c) - 1 for c in contexts]
    max_len = cfg["boundary_seq_len"]
    input_ids = pad_batch(seqs, tok.pad_id, max_len).to(device)
    boundary_positions = torch.tensor([min(p, max_len - 1) for p in boundary_positions],
                                      dtype=torch.long, device=device)
    labels_t = torch.tensor(labels, dtype=torch.float32, device=device)
    return input_ids, boundary_positions, labels_t, tiers


def save_checkpoint(path, model, optimizer, step, cfg, local_rng, np_rng_state, torch_rng_state):
    """local_rng: the SAME random.Random instance the training loop
    uses for data sampling (sample_mlm_batch/sample_boundary_batch).
    Saving only the global `random` module's state (random.getstate())
    would NOT reproduce identical draws on resume, since this loop
    uses its own local Random instance, not the global module --
    caught during resumability testing (acceptance check 6), not
    assumed correct.

    RNG state tensors are explicitly moved to CPU before saving: torch
    RNG state is always a CPU ByteTensor regardless of device, and
    loading with map_location=<cuda device> (needed so the MODEL
    weights land on GPU) would otherwise silently drag the RNG state
    tensor onto GPU too, which torch.set_rng_state rejects -- caught
    during resumability testing, not assumed correct."""
    tmp = Path(str(path) + ".tmp")
    cuda_rng_state = torch.cuda.get_rng_state() if torch.cuda.is_available() else None
    torch.save({
        "step": step, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
        "config": cfg, "local_rng_state": local_rng.getstate(), "np_rng_state": np_rng_state,
        "torch_rng_state": torch_rng_state.cpu(),
        "cuda_rng_state": cuda_rng_state.cpu() if cuda_rng_state is not None else None,
        "git_commit": get_git_commit(), "corpus_version": "TLHdig_0.2.0-beta",
    }, tmp)
    os.replace(tmp, path)  # atomic on same filesystem


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


@torch.no_grad()
def evaluate(model, dev_pool, tok, cfg, rng, del_span_lengths, device, n_batches=5):
    model.eval()
    mlm_losses, boundary_correct, boundary_total = [], 0, 0
    boundary_labels_all, boundary_probs_all = [], []
    span_exact = {}  # length_band -> [hit, total]
    for _ in range(n_batches):
        input_ids, labels = sample_mlm_batch(dev_pool, tok, cfg, rng, del_span_lengths, device)
        hidden = model.encode(input_ids)
        logits = model.mlm_logits(hidden)
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1), ignore_index=-100)
        mlm_losses.append(loss.item())
        preds = logits.argmax(-1)
        mask = labels != -100
        if mask.any():
            correct = (preds[mask] == labels[mask])
            for is_correct in correct.tolist():
                band = "all"
                span_exact.setdefault(band, [0, 0])
                span_exact[band][1] += 1
                span_exact[band][0] += int(is_correct)

        bb = sample_boundary_batch(dev_pool, tok, cfg, rng, device)
        if bb is not None:
            b_ids, b_pos, b_labels, _b_tiers = bb
            b_hidden = model.encode(b_ids)
            b_logits = model.boundary_logit(b_hidden, b_pos)
            b_probs = torch.sigmoid(b_logits)
            boundary_labels_all.extend(b_labels.tolist())
            boundary_probs_all.extend(b_probs.tolist())
            boundary_correct += ((b_probs > 0.5).float() == b_labels).sum().item()
            boundary_total += len(b_labels)
    model.train()
    auc = None
    if boundary_labels_all and len(set(boundary_labels_all)) > 1:
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(boundary_labels_all, boundary_probs_all)
    return {
        "mlm_loss": float(np.mean(mlm_losses)) if mlm_losses else None,
        "span_exact_match": {k: v[0] / v[1] if v[1] else None for k, v in span_exact.items()},
        "boundary_accuracy": boundary_correct / boundary_total if boundary_total else None,
        "boundary_auc": auc,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/pretrain_config.json")
    ap.add_argument("--tag", default="base")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if not Path(args.config).exists():
        with open(args.config, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    run_dir = Path("runs") / f"pretrain_{args.tag}"
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = run_dir / "checkpoint.pt"
    csv_path = run_dir / "loss_curve.csv"

    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # PERF (2026-07-21, approved by architect, see p4_report.md "training
    # throughput" note): GPU was measured at 100% utilization but only
    # 5.2/12GB VRAM and 85/170W -- compute-bound but inefficient, not
    # data/CPU-bound. TF32 is free on this Ampere (RTX 3060) card (no
    # meaningful precision cost for this model); cudnn.benchmark is safe
    # since every batch uses fixed shapes (seq_len=512 MLM / 64 boundary,
    # fixed batch sizes). Does not affect checkpoint/RNG resumability --
    # these are backend flags, not part of any saved/restored state.
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True

    tok = ht.Tokenizer.load()
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    print("Loading pretrain data...")
    data = load_pretrain_data(tok, frags, line_index, edge_info, cfg["seq_len"])
    train_pool = data["train"] + data["discovery"]
    dev_pool = data["dev"]
    print(f"train+discovery: {len(train_pool)}, dev: {len(dev_pool)}")

    with open(Path("p4_out") / "fracture_calibration.json", encoding="utf-8") as f:
        calib = json.load(f)
    del_span_lengths = [int(k) for k, v in calib["del_span_length"]["histogram"].items()
                        for _ in range(v)]
    if not del_span_lengths:
        del_span_lengths = [1, 2, 3]

    model = HittiteEncoder(len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
                           cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["lr"])
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}")

    rng = random.Random(cfg["seed"] + 1)  # local instance used for ALL data
    # sampling below (sample_mlm_batch/sample_boundary_batch) -- must be
    # created BEFORE any resume-load so load_checkpoint can restore its
    # exact state (see save_checkpoint's docstring for why this matters).

    last_completed_step = -1  # -1 = nothing completed yet (fresh run)
    if args.resume and ckpt_path.exists():
        last_completed_step = load_checkpoint(ckpt_path, model, optimizer, rng, device)
        print(f"Resumed after step {last_completed_step}")
    start_step = last_completed_step + 1  # the checkpoint records the LAST
    # completed step; resuming must start at the NEXT one, not re-run it
    # (caught during resumability testing -- an earlier version double-
    # executed the checkpointed step, an off-by-one).

    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["step", "mlm_loss", "boundary_loss", "total_loss",
                                    "dev_mlm_loss", "dev_span_exact", "dev_boundary_auc", "elapsed_s"])

    t0 = time.time()
    model.train()
    budget_s = cfg["wall_clock_budget_hours"] * 3600

    for step in range(start_step, cfg["max_steps"]):
        if time.time() - t0 > budget_s:
            print(f"Wall-clock budget ({cfg['wall_clock_budget_hours']}h) reached at step {step}.")
            break
        lr = cfg["lr"] * min(1.0, (step + 1) / max(1, cfg["warmup_steps"]))
        for g in optimizer.param_groups:
            g["lr"] = lr

        input_ids, labels = sample_mlm_batch(train_pool, tok, cfg, rng, del_span_lengths, device)
        hidden = model.encode(input_ids)
        mlm_logits = model.mlm_logits(hidden)
        mlm_loss = F.cross_entropy(mlm_logits.view(-1, mlm_logits.size(-1)), labels.view(-1), ignore_index=-100)

        bb = sample_boundary_batch(train_pool, tok, cfg, rng, device)
        if bb is not None:
            b_ids, b_pos, b_labels, _b_tiers = bb
            b_hidden = model.encode(b_ids)
            b_logits = model.boundary_logit(b_hidden, b_pos)
            boundary_loss = F.binary_cross_entropy_with_logits(b_logits, b_labels)
        else:
            boundary_loss = torch.tensor(0.0, device=device)

        total_loss = cfg["mlm_weight"] * mlm_loss + cfg["boundary_weight"] * boundary_loss
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % 50 == 0:
            print(f"step {step}: mlm={mlm_loss.item():.4f} boundary={boundary_loss.item():.4f} "
                  f"total={total_loss.item():.4f} elapsed={time.time()-t0:.0f}s")

        dev_metrics = {"mlm_loss": None, "span_exact_match": {}, "boundary_auc": None}
        if step % cfg["eval_every"] == 0 and dev_pool:
            dev_metrics = evaluate(model, dev_pool, tok, cfg, random.Random(cfg["seed"] + 999),
                                   del_span_lengths, device)
            print(f"  [eval @ {step}] dev_mlm_loss={dev_metrics['mlm_loss']} "
                  f"dev_span_exact={dev_metrics['span_exact_match']} "
                  f"dev_boundary_auc={dev_metrics['boundary_auc']}")

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([step, mlm_loss.item(), boundary_loss.item(), total_loss.item(),
                                    dev_metrics["mlm_loss"], dev_metrics["span_exact_match"].get("all"),
                                    dev_metrics["boundary_auc"], time.time() - t0])

        if step % cfg["checkpoint_every"] == 0 and step > start_step:
            save_checkpoint(ckpt_path, model, optimizer, step, cfg,
                           rng, np.random.get_state(), torch.get_rng_state())
            print(f"  checkpoint saved @ step {step}")

    save_checkpoint(ckpt_path, model, optimizer, step, cfg,
                   rng, np.random.get_state(), torch.get_rng_state())
    print(f"Final checkpoint saved @ step {step}. Done.")


if __name__ == "__main__":
    main()
