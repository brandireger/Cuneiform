#!/usr/bin/env python3
"""P4-F Stage 1: the falsifier measurement.

    python scripts/phase4_p4f_stage1_eval.py

Proposal Sec.3 pre-registered the falsifier BEFORE any run: arm B must
exceed arm A by **at least +0.02 `in_doc` boundary AUC** on held-out dev
batches, "measured the same way `Archive/reports/pretrain_report.md` Sec.3
measured D14 (fresh pass, n~1920, `in_doc` tier specifically -- not the
pooled AUC, which the architecture's own spec says is not the number that
matters)".

**Why this script exists rather than reading the last row of a loss curve.**
Training-time evals run `n_batches=5` at batch 16, so each sees at most ~80
boundary examples and the `in_doc` tier only a fraction of those. Arm A's
consecutive evals swing ~4 AUC points with no trend (0.830, 0.807, 0.802,
0.788, 0.799) -- that spread is sampling noise, and it is twice the size of
the +0.02 effect the falsifier is trying to detect. Declaring a verdict from
those rows would repeat the exact mistake this project already made once,
when a dev-only P2-E9 run manufactured a 12.8-point transfer gap on 55 spans
that vanished at scale (PHASE5_SUCCESSOR_HANDOFF.md, trap 2).

**The comparison is PAIRED.** Boundary examples are constructed from the dev
pool by an RNG that never consults a model, so both arms are scored on the
byte-identical example set. That removes example-sampling variance from the
difference entirely -- the remaining uncertainty is about the models, which
is the thing under test. The bootstrap resamples examples (not scores) and
recomputes both arms' AUCs on each replicate, so the reported interval is an
interval on the DIFFERENCE, not two independent intervals eyeballed for
overlap.

Nothing here touches the test split: the dev pool comes from the same
`p4f_data.load_pretrain_data` routing the training runs used, where test-side
fragments are refused outright.
"""

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llv2  # noqa: E402
import p4f_data as p4f  # noqa: E402
from hittite_model_p4f import P4FEncoder  # noqa: E402

# D14's recorded dev `in_doc` AUC (Archive/reports/pretrain_report.md), the
# proposal's secondary bar: arm B must also exceed this to avoid rejection.
D14_IN_DOC_AUC = 0.7461
FALSIFIER_MARGIN = 0.02
# n~1920 == 120 batches x 16, matching D14's reported evaluation size.
DEFAULT_EVAL_BATCHES = 120
EVAL_SEED = 20260803  # distinct from both training seeds


def build_eval_examples(dev_pool, tok, cfg, n_batches, seed):
    """Construct the shared, model-independent evaluation set once."""
    rng = random.Random(seed)
    batches = []
    for _ in range(n_batches):
        bb = p4f.sample_boundary_batch(dev_pool, tok, cfg, rng)
        if bb is not None:
            batches.append(bb)
    return batches


@torch.no_grad()
def score(model, batches, device, condition):
    """Sigmoid probabilities for every evaluation example, in order."""
    model.eval()
    probs, labels, tiers = [], [], []
    for b_ids, b_pos, b_labels, b_tiers, b_langs in batches:
        hidden = model.encode(
            torch.tensor(b_ids, dtype=torch.long, device=device),
            lang_ids=(torch.tensor(b_langs, dtype=torch.long, device=device)
                      if condition else None))
        logits = model.boundary_logit(
            hidden, torch.tensor(b_pos, dtype=torch.long, device=device))
        probs.extend(torch.sigmoid(logits).tolist())
        labels.extend(b_labels)
        tiers.extend(b_tiers)
    return np.array(probs), np.array(labels), np.array(tiers)


def tier_auc(labels, probs, tiers, tier):
    """AUC for one negative tier: that tier's negatives against ALL true
    continuations, matching how D14's per-tier breakdown was computed."""
    keep = (labels == 1) | (tiers == tier)
    y, p = labels[keep], probs[keep]
    if len(set(y.tolist())) < 2:
        return None, 0
    return float(roc_auc_score(y, p)), int(keep.sum())


def load_arm(arm, run_root, tok, cfg, device):
    spec = {"A": {"tag": "multilingual_unconditioned_p4f", "cond": False},
            "B": {"tag": "multilingual_conditioned_p4f", "cond": True}}[arm]
    path = run_root / f"pretrain_{spec['tag']}" / "checkpoint.pt"
    if not path.exists():
        raise SystemExit(f"Missing checkpoint for arm {arm}: {path}")
    ckpt = torch.load(path, map_location=device, weights_only=False)
    if ckpt.get("arm") != arm:
        raise SystemExit(
            f"{path} records arm {ckpt.get('arm')!r}, expected {arm!r}.")
    model = P4FEncoder(
        len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
        cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id,
        condition_on_language=spec["cond"]).to(device)
    model.load_state_dict(ckpt["model"])
    return model, spec["cond"], int(ckpt["step"]), path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-root", default="runs")
    ap.add_argument("--batches", type=int, default=DEFAULT_EVAL_BATCHES)
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--out", default="Phase4/phase4_out/p4f_stage1_falsifier.json")
    args = ap.parse_args()

    run_root = Path(args.run_root)
    with open("configs/p4f_pretrain_config.json", encoding="utf-8") as f:
        cfg = json.load(f)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok = ht.Tokenizer.load()
    frags, _splits, _doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    admission_scope = p4f.build_data_admission_scope()
    language_index = llv2.load_effective_language_index()
    pools, _stats = p4f.load_pretrain_data(
        tok, frags, line_index, edge_info, cfg["seq_len"],
        admission_scope=admission_scope, language_index=language_index)
    dev_pool = pools["dev"]
    print(f"dev fragments: {len(dev_pool)}")

    print(f"Building shared evaluation set ({args.batches} batches, "
          f"seed {EVAL_SEED})...")
    batches = build_eval_examples(dev_pool, tok, cfg, args.batches, EVAL_SEED)
    n_examples = sum(len(b[2]) for b in batches)
    print(f"evaluation examples: {n_examples}")

    results, scores = {}, {}
    for arm in ("A", "B"):
        model, condition, step, path = load_arm(arm, run_root, tok, cfg, device)
        probs, labels, tiers = score(model, batches, device, condition)
        scores[arm] = probs
        per_tier = {}
        for tier in ("in_doc", "cross_genre", "random"):
            auc, n = tier_auc(labels, probs, tiers, tier)
            per_tier[tier] = {"auc": auc, "n": n}
        pooled = float(roc_auc_score(labels, probs)) if len(set(labels.tolist())) > 1 else None
        results[arm] = {
            "checkpoint": str(path), "final_step": step,
            "condition_on_language": condition,
            "boundary_auc_pooled": pooled, "by_tier": per_tier,
        }
        print(f"arm {arm}: in_doc={per_tier['in_doc']['auc']:.4f} "
              f"(n={per_tier['in_doc']['n']}) pooled={pooled:.4f}")
        del model
        torch.cuda.empty_cache()

    labels_all, tiers_all = labels, tiers  # identical across arms (paired)
    a_in = results["A"]["by_tier"]["in_doc"]["auc"]
    b_in = results["B"]["by_tier"]["in_doc"]["auc"]
    delta = b_in - a_in

    # Paired bootstrap over EXAMPLES: each replicate recomputes both arms'
    # in_doc AUC on the same resampled index set, so the difference keeps its
    # pairing. Replicates without both classes present are skipped rather
    # than scored as 0.
    rng = np.random.default_rng(EVAL_SEED)
    keep = (labels_all == 1) | (tiers_all == "in_doc")
    idx_pool = np.flatnonzero(keep)
    deltas = []
    for _ in range(args.bootstrap):
        idx = rng.choice(idx_pool, size=len(idx_pool), replace=True)
        y = labels_all[idx]
        if len(set(y.tolist())) < 2:
            continue
        deltas.append(roc_auc_score(y, scores["B"][idx])
                      - roc_auc_score(y, scores["A"][idx]))
    deltas = np.array(deltas)
    ci = (float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5)))

    clears_margin = delta >= FALSIFIER_MARGIN
    clears_d14 = b_in > D14_IN_DOC_AUC
    verdict = "SUPPORTED" if (clears_margin and clears_d14) else "REJECTED"

    payload = {
        "estimand": (
            "Dev-side boundary-head AUC on the in_doc negative tier, paired "
            "across arms on one shared, model-independent evaluation set."),
        "evaluation": {
            "n_examples_total": int(n_examples),
            "n_examples_in_doc_tier": int(keep.sum()),
            "batches": args.batches, "seed": EVAL_SEED,
            "bootstrap_replicates": int(len(deltas)),
        },
        "arms": results,
        "falsifier": {
            "pre_registered_margin": FALSIFIER_MARGIN,
            "d14_reference_in_doc_auc": D14_IN_DOC_AUC,
            "arm_A_in_doc_auc": a_in, "arm_B_in_doc_auc": b_in,
            "delta_B_minus_A": delta,
            "delta_ci95": ci,
            "clears_margin": bool(clears_margin),
            "arm_B_exceeds_d14": bool(clears_d14),
            "verdict": verdict,
        },
        "caveats": [
            "One seed per arm. Proposal Sec.8: a single seed is not a "
            "robustness claim and this result is not evidence about seed "
            "variance.",
            "[PROBE -- not for citation] per Gate 4, regardless of outcome.",
            "Beating an unconditioned sibling is not beating BM25; Phase 1's "
            "finding that BM25 leads this architecture family is untouched.",
        ],
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 66)
    print(f"arm A in_doc AUC : {a_in:.4f}")
    print(f"arm B in_doc AUC : {b_in:.4f}")
    print(f"delta (B - A)    : {delta:+.4f}  95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"pre-registered   : >= +{FALSIFIER_MARGIN}  -> {'MET' if clears_margin else 'NOT MET'}")
    print(f"arm B vs D14 {D14_IN_DOC_AUC}: {'above' if clears_d14 else 'BELOW'}")
    print(f"VERDICT: hypothesis {verdict}")
    print("=" * 66)
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
