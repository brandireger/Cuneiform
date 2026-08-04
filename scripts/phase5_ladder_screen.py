#!/usr/bin/env python3
"""Withdrawn-rung screen: are ByT5 / CANINE / XLM-R / mT5 worth pursuing?

    python scripts/phase5_ladder_screen.py [--stage 1|2|all]

Executes `reports/phase5_ladder_screen_protocol.md` (RATIFIED 2026-08-04).
Training-free by design: Stage 1 is tokenizer statistics, Stage 2 is a
forward pass over frozen pretrained weights. No gradients are computed
anywhere in this file.

The protocol's two load-bearing constraints, both enforced here:

1. **The BM25 reference is computed, not quoted.** The published Task A
   recall@1 of 0.7831 is TEST-side and unusable. BM25 runs on the identical
   dev query set, in this execution, and `R_bm25` is pinned before any
   candidate is embedded.
2. **One ranking implementation.** Candidates are scored through
   `eval_harness.run_task_a`'s `precomputed_scores` path, so the leave-one-out
   exclusions and composition ranking are literally the same code BM25 goes
   through.

Dev split only; test is never loaded.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402

ADVANCE_RATIO = 0.50  # pre-registered; see protocol "Pre-registered decision rule"

# max_tokens is each model's NATIVE limit, not a uniform cap. Stage 1 showed
# a flat 512 would truncate ~30% of ByT5's and CANINE's fragments purely
# because their tokenizers are 3x more fertile -- handicapping them for a
# property that has nothing to do with whether their representation is
# useful. The frozen probe is already biased against these candidates
# (protocol, "Why the bar is deliberately generous"), so a self-inflicted
# second handicap is not acceptable. Set BEFORE any candidate was scored.
# XLM-R's 512 is a hard architectural limit (learned position embeddings);
# ByT5/mT5 use relative positions and CANINE supports 2048, so those are
# raised to what fits comfortably in 12GB at batch 8.
CANDIDATES = [
    {"rung": 3, "name": "google/byt5-small", "kind": "t5", "max_tokens": 1024},
    {"rung": 4, "name": "google/canine-s", "kind": "encoder", "max_tokens": 2048},
    {"rung": 6, "name": "xlm-roberta-base", "kind": "encoder", "max_tokens": 512},
    {"rung": 6, "name": "google/mt5-small", "kind": "t5", "max_tokens": 1024},
]

OUT_DIR = Path("Phase4/phase4_out")


def load_dev_fragments():
    """Dev-side fragments, real compositions only, rendered ATTESTED.

    Same routing the P4-F data path uses: bins are discovery-pool and carry
    main_split='discovery', so filtering to main_split=='dev' already excludes
    them. Test is never selected.
    """
    frags, _splits, _doc = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    rows = []
    for row in frags.itertuples(index=False):
        if row.main_split != "dev" or row.fragment_id not in edge_info:
            continue
        li, tl, bl, by = edge_info[row.fragment_id]
        toks = ht.build_structured_sequence_attested(
            row.parent_doc, li, line_index, tl, bl, by)
        content = [t for t in toks if not t.startswith("<")]
        if len(content) < 4:
            continue
        rows.append({
            "fragment_id": row.fragment_id, "parent_doc": row.parent_doc,
            "cth": row.cth, "tokens": content,
            "text": " ".join(content),
        })
    return rows


# --------------------------------------------------------------- Stage 1

def stage1(rows):
    """Tokenizer fertility. Diagnostic only -- cannot advance or eliminate."""
    from transformers import AutoTokenizer
    sign_tokens = sum(len(r["tokens"]) for r in rows)
    out = {"n_fragments": len(rows), "sign_level_tokens": sign_tokens,
           "candidates": {}}
    sample = [r["text"] for r in rows]
    for cand in CANDIDATES:
        tk = AutoTokenizer.from_pretrained(cand["name"])
        total = 0
        lengths = []
        unk_id = getattr(tk, "unk_token_id", None)
        unk = 0
        for text in sample:
            ids = tk(text, add_special_tokens=False)["input_ids"]
            total += len(ids)
            lengths.append(len(ids))
            if unk_id is not None:
                unk += sum(1 for i in ids if i == unk_id)
        lengths = np.array(lengths)
        out["candidates"][cand["name"]] = {
            "rung": cand["rung"],
            "tokens_emitted": int(total),
            "fertility_vs_sign_level": round(total / sign_tokens, 3),
            "mean_len": round(float(lengths.mean()), 1),
            "p95_len": int(np.percentile(lengths, 95)),
            "max_len": int(lengths.max()),
            "frac_fragments_over_512": round(float((lengths > 512).mean()), 4),
            "frac_truncated_at_model_limit": round(
                float((lengths > cand["max_tokens"]).mean()), 4),
            "max_tokens_used": cand["max_tokens"],
            "unk_tokens": int(unk),
        }
        print(f"  {cand['name']:<24} fertility x{out['candidates'][cand['name']]['fertility_vs_sign_level']:<6} "
              f"mean_len {out['candidates'][cand['name']]['mean_len']:<7} "
              f">512: {100*out['candidates'][cand['name']]['frac_fragments_over_512']:.1f}%  "
              f"unk {out['candidates'][cand['name']]['unk_tokens']}")
    return out


# --------------------------------------------------------------- Stage 2

@torch.no_grad()
def embed(rows, cand, device):
    """Mean-pooled final encoder hidden states. Frozen weights, no grads."""
    from transformers import AutoModel, AutoTokenizer, T5EncoderModel
    tk = AutoTokenizer.from_pretrained(cand["name"])
    if cand["kind"] == "t5":
        model = T5EncoderModel.from_pretrained(cand["name"])
    else:
        model = AutoModel.from_pretrained(cand["name"])
    model.to(device).eval()

    vecs = []
    B = 8
    for i in range(0, len(rows), B):
        batch = [r["text"] for r in rows[i:i + B]]
        enc = tk(batch, return_tensors="pt", padding=True, truncation=True,
                 max_length=cand["max_tokens"])
        enc = {k: v.to(device) for k, v in enc.items()}
        hidden = model(**enc).last_hidden_state          # (B, T, D)
        mask = enc["attention_mask"].unsqueeze(-1).float()
        pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1.0)
        vecs.append(pooled.float().cpu())
    del model
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return torch.cat(vecs).numpy()


def cosine_matrix(vecs):
    v = vecs / np.linalg.norm(vecs, axis=1, keepdims=True).clip(min=1e-8)
    return v @ v.T


def task_a(rows, precomputed=None, method="bm25"):
    ids = [r["fragment_id"] for r in rows]
    toks = [r["tokens"] for r in rows]
    parent = [r["parent_doc"] for r in rows]
    cth = [r["cth"] for r in rows]
    return eh.run_task_a(ids, toks, parent, cth, ids, toks, parent, cth,
                         method=method, precomputed_scores=precomputed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["1", "2", "all"])
    args = ap.parse_args()

    print("Loading dev fragments (test never loaded)...")
    rows = load_dev_fragments()
    n_comps = len({r["cth"] for r in rows})
    print(f"dev fragments: {len(rows)}, distinct compositions: {n_comps}")

    result = {
        "protocol": "reports/phase5_ladder_screen_protocol.md (RATIFIED 2026-08-04)",
        "advance_ratio": ADVANCE_RATIO,
        "n_dev_fragments": len(rows),
        "n_compositions": n_comps,
        "chance_recall_at_1": round(1.0 / n_comps, 5),
    }

    if args.stage in ("1", "all"):
        print("\n== Stage 1: tokenization fertility ==")
        result["stage1"] = stage1(rows)

    if args.stage in ("2", "all"):
        print("\n== Stage 2: BM25 reference (pinned BEFORE any candidate) ==")
        _pq, bm25 = task_a(rows, method="bm25")
        r_bm25 = bm25["recall@1"]["mean"]
        threshold = ADVANCE_RATIO * r_bm25
        print(f"  R_bm25 recall@1 = {r_bm25:.4f}  (CI {bm25['recall@1']['ci']})")
        print(f"  ADVANCE threshold = {ADVANCE_RATIO} x R_bm25 = {threshold:.4f}")
        result["bm25_reference"] = {
            "recall@1": r_bm25, "recall@5": bm25["recall@5"]["mean"],
            "mrr": bm25["mrr"]["mean"], "n": bm25["n"],
            "n_excluded_single_witness": bm25["n_excluded_single_witness"],
        }
        result["advance_threshold"] = threshold

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"\n== Stage 2: frozen-embedding probes (device {device}) ==")
        result["candidates"] = {}
        for cand in CANDIDATES:
            print(f"  embedding {cand['name']} ...")
            vecs = embed(rows, cand, device)
            _pq, agg = task_a(rows, precomputed=cosine_matrix(vecs))
            r1 = agg["recall@1"]["mean"]
            verdict = "ADVANCE" if r1 >= threshold else "CONFIRMED_WITHDRAWN"
            result["candidates"][cand["name"]] = {
                "rung": cand["rung"], "recall@1": r1,
                "recall@1_ci": agg["recall@1"]["ci"],
                "recall@5": agg["recall@5"]["mean"], "mrr": agg["mrr"]["mean"],
                "n": agg["n"], "verdict": verdict,
                "ratio_of_bm25": round(r1 / r_bm25, 4) if r_bm25 else None,
            }
            print(f"    recall@1={r1:.4f}  ({100*r1/r_bm25:.1f}% of BM25)  -> {verdict}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "p5_ladder_screen.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
