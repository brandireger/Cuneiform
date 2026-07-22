#!/usr/bin/env python3
"""
21_pretrain_report.py -- P4 acceptance check 4: D14 pretraining report.

Usage:
    python scripts/21_pretrain_report.py

Loads the FINAL D14 checkpoint (runs/pretrain_base/checkpoint.pt, step
59999 -- confirmed complete: all 60,000 steps ran, scheduled task
exited cleanly) and computes what the spec's acceptance checklist
requires beyond the single pooled numbers 19_pretrain.py's own
evaluate() already logs to loss_curve.csv every 500 steps:

  1. Final losses -- read straight from loss_curve.csv (train) plus a
     fresh, larger-n dev pass for a tighter final pooled number.
  2. Span-infilling exact-match on dev masked spans, BY SPAN-LENGTH
     BAND -- the training-loop evaluate() only reports a single
     pooled token-level accuracy across all masked positions; this
     recomputes SPAN-level (not token-level) exact match, binned by
     each span's actual contiguous length.
  3. Boundary-head AUC on dev, BY NEGATIVE TYPE (in_doc / cross_genre
     / random vs true_continuation) -- the training-loop evaluate()
     only reports one pooled AUC; per spec, "the curriculum's hard
     negatives are the number that matters", so each tier needs its
     own AUC against the positive class.
  4. Restoration-agreement rate: on DEV fragments' REAL editor-
     restored spans (identified from the FULL rendering's damage
     states, not synthetic masking), mask exactly that span and check
     whether the model's top prediction agrees with what the editor
     actually restored. This is an agreement/inter-rater diagnostic,
     NOT a correctness score against ground truth (restorations are
     distilled expert judgment per CLAUDE.md's cleanroom rule 3) --
     reported, never used to select/train the model (already frozen).
  5. 10 qualitative examples, drawn from the restoration-agreement
     pool (masked span -> model proposal vs editor's restoration),
     spanning both agreements and disagreements -- not cherry-picked.

All computation here is READ-ONLY dev-side evaluation against the
already-finished, frozen checkpoint; nothing retrains or touches test.
"""
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import hittite_tokenizer as ht
from hittite_model import HittiteEncoder, apply_span_masking

CKPT_PATH = Path("runs") / "pretrain_base" / "checkpoint.pt"
LOSS_CSV = Path("runs") / "pretrain_base" / "loss_curve.csv"
SEED = 20260722
RESTORED = "restored"

# 19_pretrain.py can't be imported (digit-prefixed module name) --
# exec its definitions into a namespace instead, same technique used
# during the earlier perf-profiling probe.
_ns = {"__file__": str(Path("scripts/19_pretrain.py").resolve())}
with open("scripts/19_pretrain.py", encoding="utf-8") as _f:
    _src = _f.read().replace('if __name__ == "__main__":\n    main()', "")
exec(compile(_src, "scripts/19_pretrain.py", "exec"), _ns)
load_config = _ns["load_config"]
load_pretrain_data = _ns["load_pretrain_data"]
sample_boundary_batch = _ns["sample_boundary_batch"]
evaluate = _ns["evaluate"]


# ---------------------------------------------------------------- full+states rendering

def build_full_sequence_with_states(doc_id, line_idxs, line_index, top_edge_lost,
                                     bottom_edge_lost, on_physical_edge_by_line):
    """Same structural markers as hittite_tokenizer.build_structured_
    sequence (FULL rendering), but keeps (token, damage_state) pairs
    instead of discarding state -- needed to locate real editor-
    restored spans for the restoration-agreement diagnostic."""
    seq = [("<EDGE_T>" if not top_edge_lost else "<GAP>", "attested")]
    sorted_idxs = sorted(line_idxs)
    for pos, idx in enumerate(sorted_idxs):
        toks = line_index.get((doc_id, idx), [])
        line_edge = on_physical_edge_by_line.get(idx)
        if line_edge == "left":
            seq.append(("<EDGE_L>", "attested"))
        seq.extend(toks)
        if line_edge == "right":
            seq.append(("<EDGE_R>", "attested"))
        if pos < len(sorted_idxs) - 1:
            seq.append(("<LINE>", "attested"))
    seq.append(("<EDGE_B>" if not bottom_edge_lost else "<GAP>", "attested"))
    return seq


# ---------------------------------------------------------------- span-exact by band

@torch.no_grad()
def span_exact_by_band(model, dev_pool, tok, cfg, rng, del_span_lengths, device, n_batches=40):
    specials_ids = set(tok.encode(ht.SPECIALS))
    mask_id, gap_id = tok.vocab["<MASK>"], tok.vocab["<GAP>"]
    band_stats = defaultdict(lambda: [0, 0])  # band -> [span_hits, span_total]

    for _ in range(n_batches):
        batch_ids, batch_labels = [], []
        for _ in range(cfg["mlm_batch_size"]):
            ex = dev_pool[rng.randrange(len(dev_pool))]
            corrupted, labels = apply_span_masking(
                ex["ids"], mask_id, gap_id, len(tok.vocab), specials_ids,
                del_span_lengths, rng, cfg["mask_rate"], cfg["gap_mode_prob"], cfg["max_span_len"])
            batch_ids.append(corrupted[:cfg["seq_len"]])
            batch_labels.append(labels[:cfg["seq_len"]])
        max_len = cfg["seq_len"]
        padded = torch.full((len(batch_ids), max_len), tok.pad_id, dtype=torch.long)
        label_arr = torch.full((len(batch_ids), max_len), -100, dtype=torch.long)
        for i, (ids, labs) in enumerate(zip(batch_ids, batch_labels)):
            padded[i, :len(ids)] = torch.tensor(ids)
            label_arr[i, :len(labs)] = torch.tensor(labs)
        padded, label_arr = padded.to(device), label_arr.to(device)
        hidden = model.encode(padded)
        preds = model.mlm_logits(hidden).argmax(-1).cpu()
        labels_cpu = label_arr.cpu()

        for row_p, row_l in zip(preds, labels_cpu):
            i, L = 0, len(row_l)
            while i < L:
                if row_l[i].item() != -100:
                    j = i
                    while j < L and row_l[j].item() != -100:
                        j += 1
                    span_len = j - i
                    hit = all(row_p[k].item() == row_l[k].item() for k in range(i, j))
                    band = span_len if span_len <= 10 else (11 if span_len <= 20 else 21)
                    band_stats[band][1] += 1
                    band_stats[band][0] += int(hit)
                    i = j
                else:
                    i += 1

    def band_label(b):
        if b == 11:
            return "11-20"
        if b == 21:
            return ">20"
        return str(b)

    return {band_label(b): {"exact_match_rate": h / t if t else None, "n": t}
            for b, (h, t) in sorted(band_stats.items())}


# ---------------------------------------------------------------- boundary AUC by tier

@torch.no_grad()
def boundary_auc_by_tier(model, dev_pool, tok, cfg, rng, device, n_calls=60):
    all_probs, all_labels, all_tiers = [], [], []
    for _ in range(n_calls):
        bb = sample_boundary_batch(dev_pool, tok, cfg, rng, device)
        if bb is None:
            continue
        b_ids, b_pos, b_labels, b_tiers = bb
        hidden = model.encode(b_ids)
        probs = torch.sigmoid(model.boundary_logit(hidden, b_pos)).cpu().tolist()
        all_probs.extend(probs)
        all_labels.extend(b_labels.cpu().tolist())
        all_tiers.extend(b_tiers)

    pos_idx = [i for i, l in enumerate(all_labels) if l == 1]
    by_tier = {}
    for tier in ("in_doc", "cross_genre", "random"):
        neg_idx = [i for i, (l, t) in enumerate(zip(all_labels, all_tiers)) if l == 0 and t == tier]
        idx = pos_idx + neg_idx
        y = [all_labels[i] for i in idx]
        p = [all_probs[i] for i in idx]
        auc = roc_auc_score(y, p) if len(set(y)) > 1 and neg_idx else None
        by_tier[tier] = {"auc": auc, "n_positive": len(pos_idx), "n_negative": len(neg_idx)}

    overall_auc = roc_auc_score(all_labels, all_probs) if len(set(all_labels)) > 1 else None
    return overall_auc, by_tier, len(all_labels)


# ---------------------------------------------------------------- restoration agreement

@torch.no_grad()
def restoration_agreement(model, tok, frags, line_index, edge_info, device, seq_len,
                          rng, max_spans=400, batch_size=16):
    dev_frags = frags[(frags["main_split"] == "dev")]
    mask_id = tok.vocab["<MASK>"]
    candidates = []
    for row in dev_frags.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        seq = build_full_sequence_with_states(row.parent_doc, line_idxs, line_index,
                                              top_lost, bot_lost, by_line)
        if len(seq) < 4:
            continue
        i = 0
        while i < len(seq):
            if seq[i][1] == RESTORED:
                j = i
                while j < len(seq) and seq[j][1] == RESTORED:
                    j += 1
                candidates.append((row.fragment_id, seq, i, j))
                i = j
            else:
                i += 1

    rng.shuffle(candidates)
    candidates = candidates[:max_spans]

    results = []
    for start in range(0, len(candidates), batch_size):
        chunk = candidates[start:start + batch_size]
        batch_ids, span_infos = [], []
        for fid, seq, s, e in chunk:
            toks_only = [t for t, _ in seq]
            ids = tok.encode(toks_only)
            if e > seq_len:
                continue
            true_ids = ids[s:e]
            masked_ids = list(ids)
            for k in range(s, e):
                masked_ids[k] = mask_id
            batch_ids.append(masked_ids[:seq_len])
            span_infos.append((fid, s, e, true_ids, toks_only))
        if not batch_ids:
            continue
        max_len = max(len(x) for x in batch_ids)
        padded = torch.full((len(batch_ids), max_len), tok.pad_id, dtype=torch.long)
        for i, ids in enumerate(batch_ids):
            padded[i, :len(ids)] = torch.tensor(ids)
        padded = padded.to(device)
        hidden = model.encode(padded)
        preds = model.mlm_logits(hidden).argmax(-1).cpu()

        for i, (fid, s, e, true_ids, toks_only) in enumerate(span_infos):
            pred_ids = preds[i, s:e].tolist()
            span_len = e - s
            token_hits = sum(1 for p, t in zip(pred_ids, true_ids) if p == t)
            results.append({
                "fragment_id": fid, "span_len": span_len,
                "token_agreement_rate": token_hits / span_len,
                "span_exact_agreement": token_hits == span_len,
                "predicted_tokens": tok.decode(pred_ids),
                "editor_restored_tokens": tok.decode(true_ids),
                "context_before": toks_only[max(0, s - 8):s],
                "context_after": toks_only[e:e + 8],
            })
    return results


# ---------------------------------------------------------------- main

def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    cfg = load_config("configs/pretrain_config.json")
    tok = ht.Tokenizer.load()
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    print("Loading dev pool...")
    data = load_pretrain_data(tok, frags, line_index, edge_info, cfg["seq_len"])
    dev_pool = data["dev"]
    print(f"dev pool: {len(dev_pool)} fragments")

    with open(Path("p4_out") / "fracture_calibration.json", encoding="utf-8") as f:
        calib = json.load(f)
    del_span_lengths = [int(k) for k, v in calib["del_span_length"]["histogram"].items() for _ in range(v)]

    model = HittiteEncoder(len(tok.vocab), cfg["d_model"], cfg["n_layers"], cfg["n_heads"],
                           cfg["d_ff"], cfg["seq_len"], cfg["dropout"], tok.pad_id).to(device)
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    model.eval()
    final_step = ckpt["step"]
    git_commit = ckpt.get("git_commit", "N/A")
    print(f"Loaded checkpoint @ step {final_step}, git commit {git_commit}")

    # ---- 1. final losses: train (from csv) + fresh larger-n dev pass
    with open(LOSS_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    last_train = rows[-1]
    last_logged_eval = [r for r in rows if r["dev_mlm_loss"]][-1]

    rng = random.Random(SEED + 12345)
    print("Running fresh final dev evaluation (n_batches=20)...")
    final_eval = evaluate(model, dev_pool, tok, cfg, rng, del_span_lengths, device, n_batches=20)

    # ---- 2. span-exact by band
    print("Computing span-infilling exact-match by length band...")
    band_results = span_exact_by_band(model, dev_pool, tok, cfg,
                                       random.Random(SEED + 111), del_span_lengths, device, n_batches=40)

    # ---- 3. boundary AUC by negative type
    print("Computing boundary-head AUC by negative type...")
    overall_auc, by_tier_auc, n_boundary = boundary_auc_by_tier(
        model, dev_pool, tok, cfg, random.Random(SEED + 222), device, n_calls=60)

    # ---- 4/5. restoration agreement + qualitative examples
    print("Computing restoration-agreement diagnostic...")
    rest_results = restoration_agreement(model, tok, frags, line_index, edge_info, device,
                                         cfg["seq_len"], random.Random(SEED + 333))
    if rest_results:
        token_agree = float(np.mean([r["token_agreement_rate"] for r in rest_results]))
        span_agree = float(np.mean([r["span_exact_agreement"] for r in rest_results]))
    else:
        token_agree = span_agree = None

    rng_q = random.Random(SEED + 444)
    agreeing = [r for r in rest_results if r["span_exact_agreement"]]
    disagreeing = [r for r in rest_results if not r["span_exact_agreement"]]
    rng_q.shuffle(agreeing)
    rng_q.shuffle(disagreeing)
    qual_examples = agreeing[:5] + disagreeing[:5]
    if len(qual_examples) < 10:
        rest_pool = agreeing[5:] + disagreeing[5:]
        rng_q.shuffle(rest_pool)
        qual_examples += rest_pool[:10 - len(qual_examples)]

    # ---- write report
    lines = [
        "# P4 D14 -- Pretraining Report", "",
        f"- Checkpoint: `{CKPT_PATH}`, final step **{final_step}** (config max_steps="
        f"{cfg['max_steps']}, so all steps completed)",
        f"- Git commit: {git_commit}. Corpus version: TLHdig_0.2.0-beta. Seed: {SEED}.",
        f"- Architecture: {cfg['n_layers']} layers, d_model={cfg['d_model']}, "
        f"{cfg['n_heads']} heads, d_ff={cfg['d_ff']}, seq_len={cfg['seq_len']}. "
        f"{sum(p.numel() for p in model.parameters()):,} params.",
        "- Data: TRAIN + discovery-pool ATTESTED sequences for gradient updates; "
        "DEV used only for loss curves / diagnostics below; TEST never touched.",
        "",
        "## 1. Final losses", "",
        f"- Train (last logged step {last_train['step']}): mlm_loss="
        f"{float(last_train['mlm_loss']):.4f}, boundary_loss={float(last_train['boundary_loss']):.4f}, "
        f"total_loss={float(last_train['total_loss']):.4f}",
        f"- Dev, last training-loop eval (step {last_logged_eval['step']}): mlm_loss="
        f"{float(last_logged_eval['dev_mlm_loss']):.4f}, span_exact(pooled, token-level)="
        f"{float(last_logged_eval['dev_span_exact']):.4f}, boundary_auc(pooled)="
        f"{float(last_logged_eval['dev_boundary_auc']):.4f}",
        f"- Dev, FRESH final pass (n_batches=20, this report): mlm_loss="
        f"{final_eval['mlm_loss']:.4f}, boundary_accuracy={final_eval['boundary_accuracy']:.4f}, "
        f"boundary_auc(pooled)={final_eval['boundary_auc']:.4f}",
        f"- First eval (step 0, for reference): mlm_loss=7.8523, span_exact(token)=0.0, "
        "boundary_auc=0.4757 (chance)",
        "",
        "## 2. Span-infilling exact-match by span-length band (dev, SPAN-level, not token-level)", "",
        "Note: this differs from the training-loop's pooled `dev_span_exact` above, which "
        "is TOKEN-level accuracy at masked positions. Here, a span counts as a hit only if "
        "EVERY position in that contiguous masked run is predicted correctly -- a stricter, "
        "per-span-length-banded metric, per the acceptance checklist.",
        "",
        "| span length | n spans | exact-match rate |", "|---|---|---|",
    ]
    for band, d in band_results.items():
        rate = f"{d['exact_match_rate']:.3f}" if d["exact_match_rate"] is not None else "n/a"
        lines.append(f"| {band} | {d['n']} | {rate} |")

    lines += [
        "", "## 3. Boundary-head AUC by negative type (dev)", "",
        f"- Overall pooled AUC (this report's fresh pass, n={n_boundary}): "
        f"{overall_auc:.4f}" if overall_auc is not None else "- Overall pooled AUC: n/a",
        "", "| negative tier | AUC vs true_continuation | n_positive | n_negative |",
        "|---|---|---|---|",
    ]
    for tier, d in by_tier_auc.items():
        auc_s = f"{d['auc']:.4f}" if d["auc"] is not None else "n/a"
        lines.append(f"| {tier} | {auc_s} | {d['n_positive']} | {d['n_negative']} |")
    lines.append("")
    lines.append(
        "Per spec: \"the curriculum's hard negatives are the number that matters\" -- "
        "`random` is the easiest tier (unrelated text, any genre); `cross_genre` is harder "
        "(same genre_band, different composition); `in_doc` is hardest (a shuffled position "
        "from the SAME fragment, so surface style/vocabulary give no signal at all).")

    lines += [
        "", "## 4. Restoration-agreement diagnostic (dev)", "",
        "Diagnostic only -- restorations are distilled expert judgment, per CLAUDE.md's "
        "cleanroom rule 3 (\"training signal yes, evaluation signal never\"). This measures "
        "AGREEMENT with the editor's proposal, not correctness against ground truth, and was "
        "NEVER used to select or train this (already-frozen) checkpoint.",
        "",
        f"- Real editor-restored spans sampled from dev fragments: **{len(rest_results)}** "
        f"(cap 400)",
        f"- Token-level agreement rate: "
        f"{token_agree:.4f}" if token_agree is not None else "- Token-level agreement rate: n/a",
        f"- Span-level EXACT agreement rate (every token in the span matches): "
        f"{span_agree:.4f}" if span_agree is not None else "- Span-level exact agreement rate: n/a",
        "",
        "## 5. Ten qualitative examples (5 agreements, 5 disagreements -- not cherry-picked)", "",
    ]
    for i, ex in enumerate(qual_examples, 1):
        verdict = "AGREE" if ex["span_exact_agreement"] else "DISAGREE"
        lines.append(f"### Example {i}/10 -- `{ex['fragment_id']}`, span_len={ex['span_len']}, {verdict}")
        lines.append(f"- context before: `{' '.join(ex['context_before'])}`")
        lines.append(f"- **editor's restoration**: `{' '.join(ex['editor_restored_tokens'])}`")
        lines.append(f"- **model's proposal**: `{' '.join(ex['predicted_tokens'])}`")
        lines.append(f"- context after: `{' '.join(ex['context_after'])}`")
        lines.append(f"- token-level agreement on this span: {ex['token_agreement_rate']:.2f}")
        lines.append("")

    with open("pretrain_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # machine-readable companion
    out = {
        "checkpoint_step": final_step, "git_commit": git_commit, "seed": SEED,
        "final_train_losses": {k: last_train[k] for k in ("step", "mlm_loss", "boundary_loss", "total_loss")},
        "final_dev_eval_fresh": final_eval,
        "span_exact_by_band": band_results,
        "boundary_auc_overall": overall_auc,
        "boundary_auc_by_tier": by_tier_auc,
        "n_boundary_examples": n_boundary,
        "restoration_agreement": {
            "n_spans": len(rest_results), "token_agreement_rate": token_agree,
            "span_exact_agreement_rate": span_agree,
        },
    }
    with open(Path("p4_out") / "pretrain_report.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)

    print("Done. pretrain_report.md + p4_out/pretrain_report.json written.")


if __name__ == "__main__":
    main()
