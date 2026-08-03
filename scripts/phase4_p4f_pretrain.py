#!/usr/bin/env python3
"""P4-F Stage 1: the two named language-conditioning runs.

    python scripts/phase4_p4f_pretrain.py --arm A [--resume]
    python scripts/phase4_p4f_pretrain.py --arm B [--resume]

Authorized by `reports/phase4_p4f_gate3_proposal.md` (RATIFIED 2026-08-02),
Sec.7: "Stage 0 (the code change) and Stage 1 (the two named runs, at the
named budget, against the named falsifier) -- nothing past that."

This is a NEW script, not an edit of `Archive/scripts/19_pretrain.py`: that
file is the frozen Phase 1 snapshot that produced D14, and rewriting it in
place would destroy the provenance of the baseline this experiment compares
against (AGENTS.md, "do not rewrite that snapshot in place"). The training
loop, checkpoint/resume discipline, and evaluation below follow it closely
and deliberately -- same objective, same losses, same negative-tier
curriculum, same 60,000 steps -- because the falsifier compares arm B
against arm A and against D14's own recorded `in_doc` AUC, and a
gratuitously different loop would make both comparisons meaningless.

Arm A and arm B differ in EXACTLY one thing: whether `lang_ids` reach the
model. Both consume `lib/p4f_data.py`, so their training data is identical
by construction rather than by review.

Reserved and refused: `--tag base`. That path is D14's own
(`runs/pretrain_base/checkpoint.pt`); proposal Sec.6 makes writing to it a
process error, so this script refuses it rather than trusting nobody types
it.
"""

import argparse
import csv
import hashlib
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
import eval_harness as eh  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llv2  # noqa: E402
import p4f_data as p4f  # noqa: E402
from hittite_model_p4f import P4FEncoder  # noqa: E402

# Matches D14's recorded config (Archive/reports/pretrain_report.md) in every
# field that is not the conditioning variable. `seed` is proposal Sec.4's
# proposed 20260802, shared by both arms so a difference between them
# reflects conditioning and not seed variance.
DEFAULT_CONFIG = {
    "seed": 20260802,
    "n_layers": 6, "d_model": 384, "n_heads": 6, "d_ff": 1536,
    "seq_len": 512, "dropout": 0.1,
    "mlm_weight": 1.0, "boundary_weight": 1.0,
    "mask_rate": 0.15, "gap_mode_prob": 0.3, "max_span_len": 20,
    "boundary_window": 32, "boundary_seq_len": 64,
    "mlm_batch_size": 16, "boundary_batch_size": 16,
    "lr": 3e-4, "warmup_steps": 500, "max_steps": 60000,
    "checkpoint_every": 500, "eval_every": 500,
    "wall_clock_budget_hours": 24,
}

ARMS = {
    "A": {"tag": "multilingual_unconditioned_p4f", "condition_on_language": False,
          "conditioning_scope": "ALL_LANGUAGES_UNCONDITIONED"},
    "B": {"tag": "multilingual_conditioned_p4f", "condition_on_language": True,
          "conditioning_scope": "MULTILINGUAL_CONDITIONED"},
}

FORBIDDEN_TAGS = {"base"}

# Config fields that MUST be identical across arms. Checked against the
# sibling arm's manifest when it exists, so an accidental confound is caught
# before GPU time is spent rather than during analysis (proposal Sec.9.3).
SHARED_CONFIG_KEYS = sorted(DEFAULT_CONFIG)


def get_git_commit():
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"N/A: {e}"


def config_hash(cfg):
    payload = json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_config(path):
    cfg = dict(DEFAULT_CONFIG)
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def to_device(rows, device, dtype=torch.long):
    return torch.tensor(rows, dtype=dtype, device=device)


def save_checkpoint(path, model, optimizer, step, cfg, arm, local_rng,
                    np_rng_state, torch_rng_state):
    """Atomic write; full RNG state so a resume reproduces the same draws.
    The CPU moves on the RNG tensors are not defensive noise -- torch RNG
    state is always a CPU ByteTensor, and loading with map_location=<cuda>
    would otherwise drag it onto the GPU, which torch.set_rng_state
    rejects (found during D14's resumability testing, kept here)."""
    tmp = Path(str(path) + ".tmp")
    cuda_rng_state = torch.cuda.get_rng_state() if torch.cuda.is_available() else None
    torch.save({
        "step": step, "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "config": cfg, "arm": arm,
        "local_rng_state": local_rng.getstate(), "np_rng_state": np_rng_state,
        "torch_rng_state": torch_rng_state.cpu(),
        "cuda_rng_state": cuda_rng_state.cpu() if cuda_rng_state is not None else None,
        "git_commit": get_git_commit(), "corpus_version": "TLHdig_0.2.0-beta",
    }, tmp)
    os.replace(tmp, path)


def load_checkpoint(path, model, optimizer, local_rng, device, arm):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    if ckpt.get("arm") != arm:
        raise SystemExit(
            f"REFUSING to resume: {path} was written by arm {ckpt.get('arm')!r}, "
            f"not arm {arm!r}. Resuming across arms would silently initialize one "
            "arm from the other's weights and invalidate the comparison.")
    model.load_state_dict(ckpt["model"])
    optimizer.load_state_dict(ckpt["optimizer"])
    local_rng.setstate(ckpt["local_rng_state"])
    np.random.set_state(ckpt["np_rng_state"])
    torch.set_rng_state(ckpt["torch_rng_state"].cpu())
    if ckpt.get("cuda_rng_state") is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state(ckpt["cuda_rng_state"].cpu())
    return ckpt["step"]


@torch.no_grad()
def evaluate(model, dev_pool, tok, cfg, rng, del_span_lengths, device,
             condition, n_batches=5):
    """Dev metrics. `boundary_auc_by_tier` is what the falsifier reads:
    proposal Sec.3 names the `in_doc` tier specifically, "not the pooled
    AUC, which the architecture's own spec says is not the number that
    matters"."""
    model.eval()
    mlm_losses = []
    span_hit = span_total = 0
    labels_by_tier, probs_by_tier = {}, {}
    all_labels, all_probs = [], []

    for _ in range(n_batches):
        ids, labels, langs = p4f.sample_mlm_batch(
            dev_pool, tok, cfg, rng, del_span_lengths)
        input_ids = to_device(ids, device)
        label_t = to_device(labels, device)
        lang_t = to_device(langs, device) if condition else None
        hidden = model.encode(input_ids, lang_ids=lang_t)
        logits = model.mlm_logits(hidden)
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)),
                               label_t.view(-1), ignore_index=-100)
        mlm_losses.append(loss.item())
        mask = label_t != -100
        if mask.any():
            correct = (logits.argmax(-1)[mask] == label_t[mask])
            span_hit += int(correct.sum().item())
            span_total += int(mask.sum().item())

        bb = p4f.sample_boundary_batch(dev_pool, tok, cfg, rng)
        if bb is None:
            continue
        b_ids, b_pos, b_labels, b_tiers, b_langs = bb
        b_hidden = model.encode(
            to_device(b_ids, device),
            lang_ids=to_device(b_langs, device) if condition else None)
        b_logits = model.boundary_logit(b_hidden, to_device(b_pos, device))
        b_probs = torch.sigmoid(b_logits).tolist()
        for label, prob, tier in zip(b_labels, b_probs, b_tiers):
            all_labels.append(label)
            all_probs.append(prob)
            # A negative's tier is its own; a true continuation is a
            # positive for EVERY tier's AUC, since each tier's AUC ranks
            # true continuations against that tier's negatives.
            tiers = ["in_doc", "cross_genre", "random"] if label == 1 else [tier]
            for t in tiers:
                labels_by_tier.setdefault(t, []).append(label)
                probs_by_tier.setdefault(t, []).append(prob)
    model.train()

    def auc(labels, probs):
        if not labels or len(set(labels)) < 2:
            return None
        from sklearn.metrics import roc_auc_score
        return float(roc_auc_score(labels, probs))

    return {
        "mlm_loss": float(np.mean(mlm_losses)) if mlm_losses else None,
        "span_exact_match": span_hit / span_total if span_total else None,
        "boundary_auc_pooled": auc(all_labels, all_probs),
        "boundary_auc_by_tier": {
            t: auc(labels_by_tier[t], probs_by_tier[t]) for t in labels_by_tier},
        "n_boundary_examples": len(all_labels),
    }


def build_manifest(cfg, arm, arm_spec, data_stats, language_index,
                   admission_scope, n_params, device, pools):
    """The run manifest. Split deliberately into a `shared` block (must be
    byte-identical across arms) and an `arm` block (must differ) so proposal
    Sec.9 item 3 is a mechanical comparison, not an eyeball one."""
    return {
        "shared": {
            "config": cfg,
            "config_hash": config_hash(cfg),
            "corpus_version": "TLHdig_0.2.0-beta",
            "data_admission_scope": admission_scope.manifest_entry(),
            "train_pool_size": len(pools["train"]),
            "discovery_pool_size": len(pools["discovery"]),
            "dev_pool_size": len(pools["dev"]),
            "data_stats": data_stats,
            "language_dataset": language_index.manifest_entry(),
            "n_params_excluding_conditioning": n_params["base"],
            "tokenizer_vocab_size": n_params["vocab_size"],
        },
        "arm": {
            "arm": arm,
            "tag": arm_spec["tag"],
            "condition_on_language": arm_spec["condition_on_language"],
            "language_scope": arm_spec["conditioning_scope"],
            "n_params_total": n_params["total"],
        },
        "provenance": {
            "git_commit": get_git_commit(),
            "device": str(device),
            "torch_version": torch.__version__,
            "proposal": "reports/phase4_p4f_gate3_proposal.md (RATIFIED 2026-08-02)",
        },
    }


def check_arm_symmetry(manifest, run_root, arm):
    """If the sibling arm has already written a manifest, its `shared` block
    must match this one exactly. Catches an accidental confound before the
    second run spends 24h being uncomparable to the first."""
    sibling = "B" if arm == "A" else "A"
    path = run_root / f"pretrain_{ARMS[sibling]['tag']}" / "manifest.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        other = json.load(f)
    mine, theirs = manifest["shared"], other.get("shared", {})
    differing = sorted(
        k for k in set(mine) | set(theirs) if mine.get(k) != theirs.get(k))
    if differing:
        raise SystemExit(
            f"REFUSING to start arm {arm}: its shared config/data block differs "
            f"from arm {sibling}'s already-recorded run in {differing}. The "
            "falsifier compares these two runs directly, so any difference "
            "outside the conditioning variable invalidates it. Resolve, or "
            "delete the stale sibling run, before proceeding.")
    return sibling


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--config", default="configs/p4f_pretrain_config.json")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-steps", type=int, default=None,
                    help="Override for smoke tests ONLY; a Stage 1 run is "
                         "60,000 steps and any other value is recorded in the "
                         "manifest as a non-Stage-1 run.")
    ap.add_argument("--run-root", default="runs")
    args = ap.parse_args()

    arm_spec = ARMS[args.arm]
    if arm_spec["tag"] in FORBIDDEN_TAGS:  # pragma: no cover - guard
        raise SystemExit("Refusing a reserved tag.")

    cfg = load_config(args.config)
    if args.max_steps is not None:
        cfg["max_steps"] = args.max_steps
    if not Path(args.config).exists():
        Path(args.config).parent.mkdir(parents=True, exist_ok=True)
        with open(args.config, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

    run_root = Path(args.run_root)
    run_dir = run_root / f"pretrain_{arm_spec['tag']}"
    if run_dir.resolve() == (run_root / "pretrain_base").resolve():
        raise SystemExit("Refusing to write to D14's frozen run directory.")
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = run_dir / "checkpoint.pt"
    csv_path = run_dir / "loss_curve.csv"

    random.seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    torch.manual_seed(cfg["seed"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        # Same Ampere backend flags D14 used (see 19_pretrain.py's PERF
        # note): TF32 and cudnn.benchmark, safe because every batch has
        # fixed shapes. Backend flags, not saved state -- resumability is
        # unaffected.
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
    print(f"Arm {args.arm} ({arm_spec['tag']}) | device: {device} | "
          f"condition_on_language={arm_spec['condition_on_language']}")

    tok = ht.Tokenizer.load()
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    admission_scope = p4f.build_data_admission_scope()
    print(f"Loading language dataset (admission scope: "
          f"{admission_scope.describe()})...")
    language_index = llv2.load_effective_language_index()

    print("Rendering pretrain data with per-token languages...")
    pools, data_stats = p4f.load_pretrain_data(
        tok, frags, line_index, edge_info, cfg["seq_len"],
        admission_scope=admission_scope, language_index=language_index)
    data_stats["line_decisions"] = language_index.decision_summary()
    train_pool = pools["train"] + pools["discovery"]
    dev_pool = pools["dev"]
    print(f"train+discovery: {len(train_pool)}, dev: {len(dev_pool)}, "
          f"tokens kept: {data_stats['tokens_kept']:,}")
    if not train_pool or not dev_pool:
        raise SystemExit("Empty train or dev pool -- refusing to train.")

    with open(Path("Phase1_pipeline/p4_out") / "fracture_calibration.json",
              encoding="utf-8") as f:
        calib = json.load(f)
    del_span_lengths = [int(k) for k, v in calib["del_span_length"]["histogram"].items()
                        for _ in range(v)] or [1, 2, 3]

    condition = arm_spec["condition_on_language"]
    model = P4FEncoder(
        len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
        cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id,
        condition_on_language=condition).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["lr"])
    total_params = sum(p.numel() for p in model.parameters())
    lang_params = (model.lang_emb.weight.numel() if condition else 0)
    print(f"Model params: {total_params:,} "
          f"(language embedding: {lang_params:,})")

    manifest = build_manifest(
        cfg, args.arm, arm_spec, data_stats, language_index, admission_scope,
        {"total": total_params, "base": total_params - lang_params,
         "vocab_size": len(tok.vocab)},
        device, pools)
    sibling = check_arm_symmetry(manifest, run_root, args.arm)
    if sibling:
        print(f"Shared block matches arm {sibling}'s recorded run.")
    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    rng = random.Random(cfg["seed"] + 1)  # created BEFORE any resume load so
    # load_checkpoint can restore its exact state
    last_completed_step = -1
    if args.resume and ckpt_path.exists():
        last_completed_step = load_checkpoint(
            ckpt_path, model, optimizer, rng, device, args.arm)
        print(f"Resumed after step {last_completed_step}")
    start_step = last_completed_step + 1

    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["step", "mlm_loss", "boundary_loss", "total_loss",
                 "dev_mlm_loss", "dev_span_exact", "dev_boundary_auc_pooled",
                 "dev_boundary_auc_in_doc", "elapsed_s"])

    t0 = time.time()
    model.train()
    budget_s = cfg["wall_clock_budget_hours"] * 3600
    step = start_step - 1

    for step in range(start_step, cfg["max_steps"]):
        if time.time() - t0 > budget_s:
            print(f"Wall-clock budget ({cfg['wall_clock_budget_hours']}h) "
                  f"reached at step {step}. Resume with --resume.")
            break
        lr = cfg["lr"] * min(1.0, (step + 1) / max(1, cfg["warmup_steps"]))
        for g in optimizer.param_groups:
            g["lr"] = lr

        ids, labels, langs = p4f.sample_mlm_batch(
            train_pool, tok, cfg, rng, del_span_lengths)
        hidden = model.encode(
            to_device(ids, device),
            lang_ids=to_device(langs, device) if condition else None)
        mlm_logits = model.mlm_logits(hidden)
        mlm_loss = F.cross_entropy(
            mlm_logits.view(-1, mlm_logits.size(-1)),
            to_device(labels, device).view(-1), ignore_index=-100)

        bb = p4f.sample_boundary_batch(train_pool, tok, cfg, rng)
        if bb is not None:
            b_ids, b_pos, b_labels, _tiers, b_langs = bb
            b_hidden = model.encode(
                to_device(b_ids, device),
                lang_ids=to_device(b_langs, device) if condition else None)
            b_logits = model.boundary_logit(b_hidden, to_device(b_pos, device))
            boundary_loss = F.binary_cross_entropy_with_logits(
                b_logits, to_device(b_labels, device, dtype=torch.float32))
        else:
            boundary_loss = torch.tensor(0.0, device=device)

        total_loss = (cfg["mlm_weight"] * mlm_loss
                      + cfg["boundary_weight"] * boundary_loss)
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step % 50 == 0:
            print(f"step {step}: mlm={mlm_loss.item():.4f} "
                  f"boundary={boundary_loss.item():.4f} "
                  f"total={total_loss.item():.4f} elapsed={time.time()-t0:.0f}s")

        dev = {"mlm_loss": None, "span_exact_match": None,
               "boundary_auc_pooled": None, "boundary_auc_by_tier": {}}
        if step % cfg["eval_every"] == 0:
            dev = evaluate(model, dev_pool, tok, cfg,
                           random.Random(cfg["seed"] + 999), del_span_lengths,
                           device, condition)
            print(f"  [eval @ {step}] mlm={dev['mlm_loss']} "
                  f"span_exact={dev['span_exact_match']} "
                  f"auc_pooled={dev['boundary_auc_pooled']} "
                  f"auc_in_doc={dev['boundary_auc_by_tier'].get('in_doc')}")

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [step, mlm_loss.item(), boundary_loss.item(), total_loss.item(),
                 dev["mlm_loss"], dev["span_exact_match"],
                 dev["boundary_auc_pooled"],
                 dev["boundary_auc_by_tier"].get("in_doc"), time.time() - t0])

        if step % cfg["checkpoint_every"] == 0 and step > start_step:
            save_checkpoint(ckpt_path, model, optimizer, step, cfg, args.arm,
                            rng, np.random.get_state(), torch.get_rng_state())
            print(f"  checkpoint saved @ step {step}")

    save_checkpoint(ckpt_path, model, optimizer, step, cfg, args.arm,
                    rng, np.random.get_state(), torch.get_rng_state())
    print(f"Final checkpoint saved @ step {step}. Done.")


if __name__ == "__main__":
    main()
