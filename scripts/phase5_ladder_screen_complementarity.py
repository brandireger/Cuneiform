#!/usr/bin/env python3
"""Addendum to the withdrawn-rung screen: do the advancing candidates add
anything BM25 does not already have?

    python scripts/phase5_ladder_screen_complementarity.py

**This is NOT part of the pre-registered decision rule.** It was written
AFTER seeing Stage 2's verdicts and must not be used to revise them —
`reports/phase5_ladder_screen_protocol.md`'s rule stands exactly as ratified.
Its purpose is to inform the Gate-3 proposal that an ADVANCE verdict
requires, by answering the question that decides whether such a proposal is
worth writing:

CANINE and XLM-R are character- and subword-level models. The most
parsimonious explanation for a frozen embedding scoring well on composition
retrieval is that it captures **orthographic similarity** — which is what
BM25 already does lexically, better. If a candidate is right on exactly the
queries BM25 is right on, it is re-deriving BM25's signal, not adding to it,
and a full rung would buy nothing.

Measured here, on the same dev query set and the same `run_task_a`
leave-one-out protocol:

- per-query agreement with BM25 at rank 1;
- queries the candidate gets right that BM25 gets WRONG (the only cell that
  can justify a rung);
- an oracle union, bounding what a perfect BM25+candidate combiner could
  reach.

Training-free. Dev split only.
"""

import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

_screen = __import__("phase5_ladder_screen")

OUT = Path("Phase4/phase4_out/p5_ladder_screen_complementarity.json")


def correct_set(per_query):
    return {r["query_id"] for r in per_query if r.get("recall@1")}


def main():
    rows = _screen.load_dev_fragments()
    print(f"dev fragments: {len(rows)}")

    pq_bm25, agg_bm25 = _screen.task_a(rows, method="bm25")
    bm25_right = correct_set(pq_bm25)
    answered = {r["query_id"] for r in pq_bm25}
    print(f"BM25 recall@1 {agg_bm25['recall@1']['mean']:.4f} on n={agg_bm25['n']}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    result = {
        "note": ("NOT part of the pre-registered decision rule; written after "
                 "seeing Stage 2 verdicts, to inform the Gate-3 proposal an "
                 "ADVANCE requires. Does not revise any verdict."),
        "bm25_recall@1": agg_bm25["recall@1"]["mean"],
        "n_queries": agg_bm25["n"],
        "candidates": {},
    }

    advancing = [c for c in _screen.CANDIDATES
                 if c["name"] in ("google/canine-s", "xlm-roberta-base")]
    for cand in advancing:
        print(f"embedding {cand['name']} ...")
        vecs = _screen.embed(rows, cand, device)
        pq, agg = _screen.task_a(rows, precomputed=_screen.cosine_matrix(vecs))
        cand_right = correct_set(pq)

        both = bm25_right & cand_right
        only_cand = cand_right - bm25_right
        only_bm25 = bm25_right - cand_right
        neither = answered - bm25_right - cand_right
        union = bm25_right | cand_right

        entry = {
            "recall@1": agg["recall@1"]["mean"],
            "both_correct": len(both),
            "only_candidate_correct": len(only_cand),
            "only_bm25_correct": len(only_bm25),
            "neither_correct": len(neither),
            "oracle_union_recall@1": len(union) / len(answered),
            "oracle_gain_over_bm25": len(union) / len(answered) - agg_bm25["recall@1"]["mean"],
            "frac_of_candidate_correct_also_bm25_correct": (
                len(both) / len(cand_right) if cand_right else None),
        }
        result["candidates"][cand["name"]] = entry
        print(f"  recall@1 {entry['recall@1']:.4f} | both {len(both)} | "
              f"only candidate {len(only_cand)} | only BM25 {len(only_bm25)} | "
              f"neither {len(neither)}")
        print(f"  oracle union {entry['oracle_union_recall@1']:.4f} "
              f"(+{entry['oracle_gain_over_bm25']:.4f} over BM25); "
              f"{100*entry['frac_of_candidate_correct_also_bm25_correct']:.1f}% of its "
              "correct answers are ones BM25 already gets")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
