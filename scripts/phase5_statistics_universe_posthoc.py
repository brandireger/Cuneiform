#!/usr/bin/env python3
"""Post-hoc reading of the statistics-universe control's per-query artifact.

    python scripts/phase5_statistics_universe_posthoc.py

**NOT PRE-REGISTERED.** The pre-registered run
(`reports/phase5_statistics_universe_protocol.md`) compared every arm against
the BM25 reference of its own universe. It did not compare the arms with each
other, because that was not the question it was committed to.

Seeing the U3 arms converge raises one question the pre-registered output
cannot answer: the corrective review's own decomposition attributed +0.0520 to
unigram TF-IDF and a further **+0.0497** to the separately tuned bigram arm.
That second component is a PAIRED contrast between two arms, so restating it
under the declared universe needs the paired comparison, not a difference of
two deltas against a common baseline.

This reads the per-query correctness the pre-registered run already wrote and
computes that contrast in every universe, using the same `compare` and
`_cluster_summary` the rest of the line uses. It adds no new scoring, no new
fitting and no new model. It is descriptive and carries no decision weight.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

_comb = __import__("phase5_bm25_combiner")
_uni = __import__("phase5_unigram_tfidf_control")

OUT_DIR = Path("Phase4/phase4_out")
PER_QUERY = OUT_DIR / "p5_statistics_universe_per_query.jsonl"
RUN = OUT_DIR / "p5_statistics_universe.json"
OUT = OUT_DIR / "p5_statistics_universe_posthoc.json"

UNIVERSES = ["U1_dev_fit_dev_index", "U2_full_fit_dev_index",
             "U3_full_fit_full_index"]
CONTRASTS = [
    ("bm25_plus_bigram_tfidf", "bm25_plus_unigram_tfidf"),
    ("bm25_plus_char_ngram", "bm25_plus_bigram_tfidf"),
    ("bm25_plus_char_ngram", "bm25_plus_unigram_tfidf"),
]


def main():
    records = [json.loads(line) for line in
               PER_QUERY.read_text(encoding="utf-8").splitlines() if line]
    rows = [{"fragment_id": r["query_id"], "cth": r["cth"]} for r in records]

    def correctness(universe, arm):
        key = f"{universe}::{arm}"
        return {r["query_id"]: r[key] for r in records if key in r}

    out = {
        "status": "POST_HOC_NOT_PREREGISTERED",
        "source_run": str(RUN),
        "source_per_query": str(PER_QUERY),
        "note": ("Paired arm-vs-arm contrasts, which the pre-registered run "
                 "did not compute. Descriptive; no decision weight. The "
                 "arms are separately tuned, so this is not a formal "
                 "conditional-increment model -- that requires the joint "
                 "factorial fit of review step 2."),
        "contrasts": {},
    }
    for candidate, reference in CONTRASTS:
        label = f"{candidate}_vs_{reference}"
        out["contrasts"][label] = {}
        for universe in UNIVERSES:
            cand = correctness(universe, candidate)
            ref = correctness(universe, reference)
            cmp_q = _comb.compare(cand, ref)
            cluster = _uni._cluster_summary(rows, cand, ref)
            out["contrasts"][label][universe] = {
                **cmp_q, "composition_cluster": cluster}
            print(f"{label:>52s} | {universe:24s} "
                  f"delta {cmp_q['delta']:+.4f} "
                  f"queryCI {[round(x, 4) for x in cmp_q['delta_ci95']]} "
                  f"clusterCI "
                  f"{[round(x, 4) for x in cluster['query_micro_cluster_ci95']]} "
                  f"(+{cmp_q['n_gained']}/-{cmp_q['n_lost']})")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nwritten {OUT}")


if __name__ == "__main__":
    main()
