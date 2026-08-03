#!/usr/bin/env python3
"""P4-F follow-up: why does arm A underperform D14 on every tier?

    python scripts/phase4_p4f_baseline_diagnostic.py

`reports/phase4_p4f_stage1.md` recorded three candidate causes and tested
none. Two of them (data admission, seed) can only be separated by new
training runs, which is Stage 2 and is NOT authorized. The third can be
settled right now, for free, and it is the one that most limits the
falsifier's second clause:

  **Is D14's recorded 0.7461 even measured on a comparable population?**

D14's number comes from its own dev pool, rendered language-blind. Stage 1's
arms were evaluated on the 883 dev fragments surviving
`MULTILINGUAL_CONDITIONED` admission. Same protocol, different population --
so "arm B (0.7263) is below D14 (0.7461)" may be comparing across
populations rather than across models.

This script removes that ambiguity by scoring **D14's own frozen checkpoint
on the byte-identical evaluation set the Stage 1 arms were scored on**. It
imports the example construction and scoring from
`phase4_p4f_stage1_eval.py` rather than reimplementing them -- a second
implementation of an evaluation is a second chance to make it
incomparable, which is the whole point of the exercise.

**This does NOT revisit the verdict.** The falsifier was pre-registered
against D14's recorded number and it failed; that stands. This is input to
the Stage 2 proposal that a rejection requires, per proposal Sec.3.

No training. Inference only, on an existing frozen checkpoint, dev split
only -- `runs/pretrain_base/` is opened READ-ONLY and never written.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_harness as eh  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llv2  # noqa: E402
import p4f_data as p4f  # noqa: E402
from hittite_model import HittiteEncoder  # noqa: E402
from hittite_model_p4f import P4FEncoder  # noqa: E402

_eval = __import__("phase4_p4f_stage1_eval")

D14_CHECKPOINT = Path("runs/pretrain_base/checkpoint.pt")
D14_RECORDED_IN_DOC = 0.7461
D14_RECORDED = {"in_doc": 0.7461, "cross_genre": 0.9006, "random": 0.9473,
                "pooled": 0.7904}


def verify_reproduction_is_faithful(state_dict, vocab_size, cfg, device):
    """P4FEncoder(condition_on_language=False) must be D14's architecture,
    not merely a same-sized one. Two checks, because a strict state_dict load
    proves the parameter STRUCTURE matches while saying nothing about whether
    the forward pass composes those parameters the same way."""
    d14 = HittiteEncoder(vocab_size, cfg["d_model"], cfg["n_layers"],
                         cfg["n_heads"], cfg["d_ff"], cfg["seq_len"],
                         cfg["dropout"], 0).to(device)
    repro = P4FEncoder(vocab_size, cfg["d_model"], cfg["n_layers"],
                       cfg["n_heads"], cfg["d_ff"], cfg["seq_len"],
                       cfg["dropout"], 0, condition_on_language=False).to(device)
    d14.load_state_dict(state_dict)        # strict=True by default
    repro.load_state_dict(state_dict)
    d14.eval()
    repro.eval()
    gen = torch.Generator(device="cpu").manual_seed(4242)
    canary = torch.randint(0, vocab_size, (4, 64), generator=gen).to(device)
    with torch.no_grad():
        a = d14.encode(canary)
        b = repro.encode(canary)
        ha = d14.boundary_logit(a, torch.full((4,), 30, dtype=torch.long, device=device))
        hb = repro.boundary_logit(b, torch.full((4,), 30, dtype=torch.long, device=device))
    hidden_diff = (a - b).abs().max().item()
    logit_diff = (ha - hb).abs().max().item()
    return repro, hidden_diff, logit_diff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", default="runs")
    ap.add_argument("--batches", type=int, default=_eval.DEFAULT_EVAL_BATCHES)
    ap.add_argument("--out", default="Phase4/phase4_out/p4f_baseline_diagnostic.json")
    args = ap.parse_args()

    run_root = Path(args.run_root)
    with open("configs/p4f_pretrain_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tok = ht.Tokenizer.load()
    frags, _s, _d = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    admission_scope = p4f.build_data_admission_scope()
    language_index = llv2.load_effective_language_index()
    pools, stats = p4f.load_pretrain_data(
        tok, frags, line_index, edge_info, cfg["seq_len"],
        admission_scope=admission_scope, language_index=language_index)
    dev_pool = pools["dev"]

    # The SAME construction, seed and batch count the falsifier used.
    batches = _eval.build_eval_examples(
        dev_pool, tok, cfg, args.batches, _eval.EVAL_SEED)
    n_examples = sum(len(b[2]) for b in batches)
    print(f"dev fragments: {len(dev_pool)}, evaluation examples: {n_examples}")

    if not D14_CHECKPOINT.exists():
        raise SystemExit(f"D14 checkpoint not found: {D14_CHECKPOINT}")
    ckpt = torch.load(D14_CHECKPOINT, map_location=device, weights_only=False)
    model, hidden_diff, logit_diff = verify_reproduction_is_faithful(
        ckpt["model"], len(tok.vocab), cfg, device)
    print(f"architecture reproduction: max hidden diff {hidden_diff:.2e}, "
          f"max boundary-logit diff {logit_diff:.2e}")
    if max(hidden_diff, logit_diff) > 1e-5:
        raise SystemExit(
            "P4FEncoder does not reproduce HittiteEncoder's forward pass on "
            "identical weights -- the D14 comparison would be invalid.")

    results = {}
    probs, labels, tiers = _eval.score(model, batches, device, condition=False)
    per_tier = {}
    for tier in ("in_doc", "cross_genre", "random"):
        auc, n = _eval.tier_auc(labels, probs, tiers, tier)
        per_tier[tier] = {"auc": auc, "n": n}
    pooled = float(roc_auc_score(labels, probs))
    results["D14_on_stage1_population"] = {
        "checkpoint": str(D14_CHECKPOINT),
        "trained_steps": int(ckpt.get("step", -1)),
        "by_tier": per_tier, "boundary_auc_pooled": pooled,
    }

    # Bootstrap CI on D14-vs-armA, paired on the same examples.
    armA, _cond, _step, _p = _eval.load_arm("A", run_root, tok, cfg, device)
    probs_a, labels_a, tiers_a = _eval.score(armA, batches, device, False)
    keep = (labels == 1) | (tiers == "in_doc")
    idx_pool = np.flatnonzero(keep)
    rng = np.random.default_rng(_eval.EVAL_SEED)
    deltas = []
    for _ in range(2000):
        idx = rng.choice(idx_pool, size=len(idx_pool), replace=True)
        y = labels[idx]
        if len(set(y.tolist())) < 2:
            continue
        deltas.append(roc_auc_score(y, probs[idx]) - roc_auc_score(y, probs_a[idx]))
    deltas = np.array(deltas)
    ci = (float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5)))
    d14_in = per_tier["in_doc"]["auc"]
    a_in = float(roc_auc_score(labels_a[keep], probs_a[keep]))

    payload = {
        "question": (
            "Is D14's recorded in_doc AUC (0.7461) comparable to the Stage 1 "
            "arms', or was it measured on a different population?"),
        "method": (
            "D14's frozen checkpoint scored on the byte-identical evaluation "
            "set the Stage 1 falsifier used (same builder, same seed "
            f"{_eval.EVAL_SEED}, same {args.batches} batches). Inference only; "
            "no training; dev split only."),
        "architecture_reproduction_check": {
            "max_hidden_state_diff": hidden_diff,
            "max_boundary_logit_diff": logit_diff,
        },
        "d14_recorded_on_its_own_population": D14_RECORDED,
        "d14_measured_on_stage1_population": {
            **{k: v["auc"] for k, v in per_tier.items()}, "pooled": pooled},
        "arm_A_in_doc_auc": a_in,
        "d14_minus_armA_in_doc": d14_in - a_in,
        "d14_minus_armA_ci95": ci,
        "population": {
            "dev_fragments": len(dev_pool),
            "evaluation_examples": int(n_examples),
            "line_decisions": language_index.decision_summary(),
            "data_stats": {k: v for k, v in stats.items() if k != "line_decisions"},
        },
        "not_a_revision_of": (
            "The Stage 1 verdict. The falsifier was pre-registered against "
            "D14's RECORDED number and failed; that stands. This is input to "
            "the Stage 2 proposal a rejection requires (proposal Sec.3)."),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 72)
    print(f"{'tier':<14}{'D14 recorded':>14}{'D14 here':>12}{'arm A':>10}{'arm B':>10}")
    armB, _c, _s2, _p2 = _eval.load_arm("B", run_root, tok, cfg, device)
    probs_b, labels_b, tiers_b = _eval.score(armB, batches, device, True)
    for tier in ("in_doc", "cross_genre", "random"):
        k = (labels == 1) | (tiers == tier)
        b_auc = roc_auc_score(labels[k], probs_b[k])
        a_auc = roc_auc_score(labels[k], probs_a[k])
        print(f"{tier:<14}{D14_RECORDED[tier]:>14.4f}{per_tier[tier]['auc']:>12.4f}"
              f"{a_auc:>10.4f}{b_auc:>10.4f}")
    print(f"{'pooled':<14}{D14_RECORDED['pooled']:>14.4f}{pooled:>12.4f}"
          f"{roc_auc_score(labels, probs_a):>10.4f}{roc_auc_score(labels, probs_b):>10.4f}")
    print("=" * 72)
    print(f"D14 - arm A (in_doc, same population): {d14_in - a_in:+.4f} "
          f"95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
