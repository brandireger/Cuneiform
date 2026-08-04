#!/usr/bin/env python3
"""Is the character n-gram gain actually about CHARACTERS, or just n-grams?

    python scripts/phase5_bigram_control.py

Executes `reports/phase5_bigram_control_protocol.md` (PRE-REGISTERED
2026-08-04, committed before this run). Training-free; dev split only.

The char n-gram control concluded the useful signal is character-level. This
tests that against the cheaper alternative it did not exclude: whole-SIGN
bigrams, which supply n-gram context without character granularity. The
project has had `add_bigrams()` since P3 and never measured it.

Same two-arm structure that retired CANINE:
  R_bigram = BM25 + sign-bigram          vs BM25
  I_char   = BM25 + sign-bigram + char   vs BM25 + sign-bigram   [PRIMARY]
"""

import json
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_harness as eh  # noqa: E402
from effect_decision import practical_increment_verdict  # noqa: E402

_screen = __import__("phase5_ladder_screen")
_comb = __import__("phase5_bm25_combiner")
_ngram = __import__("phase5_char_ngram_control")

OUT = Path("Phase4/phase4_out/p5_bigram_control.json")
CHAR_DELTA = 0.1179            # from phase5_char_ngram_control_results.md
INCREMENT_MARGIN = 0.010
_identity = lambda x: x        # noqa: E731 -- tokens are pre-tokenized


def bigram_similarity(rows):
    """Cosine over TF-IDF of sign unigrams + adjacent-pair bigrams, using the
    harness's own add_bigrams() rather than a local reimplementation."""
    docs = [eh.add_bigrams(r["tokens"]) for r in rows]
    vec = TfidfVectorizer(tokenizer=_identity, preprocessor=_identity,
                          lowercase=False, token_pattern=None, norm="l2")
    X = vec.fit_transform(docs)
    return (X @ X.T).toarray()


def main():
    print("Loading dev fragments (test never loaded)...")
    rows = _screen.load_dev_fragments()
    all_idx = list(range(len(rows)))
    fold_of, load = _comb.assign_folds(rows)
    print(f"dev fragments: {len(rows)}, fold query loads: {load}")

    bm25 = eh.bm25_score_matrix([r["tokens"] for r in rows],
                                [r["tokens"] for r in rows])[0].toarray()
    pq_base, agg_base = _comb.run_subset(rows, bm25, all_idx)
    base_correct = _comb.correct_by_query(pq_base)
    zb = _comb.znorm_rows(bm25)
    print(f"BM25 reference recall@1 {agg_base['recall@1']['mean']:.4f} "
          f"(n={agg_base['n']})")

    zbig = {("bigram",): _comb.znorm_rows(bigram_similarity(rows))}
    zchar = _comb.znorm_rows(_ngram.char_similarity(rows, (4, 6)))
    print("signals built (sign-bigram TF-IDF; char n-gram (4,6))")

    result = {
        "protocol": "reports/phase5_bigram_control_protocol.md "
                    "(PRE-REGISTERED 2026-08-04, committed before this run)",
        "training_free": True, "split": "dev only; test never loaded",
        "char_delta_reference": CHAR_DELTA,
        "bm25_reference_recall@1": agg_base["recall@1"]["mean"],
        "arms": {},
    }

    grid = [(("bigram",), a) for a in _comb.ALPHA_GRID]

    print("\n== (1) BM25 + sign-bigram vs BM25 ==")
    ho_big, pf_big = _ngram.fit_two_param(rows, zb, zbig, None, fold_of,
                                          base_correct, grid, "bigram")
    cmp_big = _comb.compare(ho_big, base_correct)
    ratio = cmp_big["delta"] / CHAR_DELTA
    print(f"  R_bigram = {cmp_big['delta']:+.4f} CI "
          f"{[round(x, 4) for x in cmp_big['delta_ci95']]} "
          f"| {ratio:.3f} of the char n-gram gain")
    result["arms"]["bm25_plus_bigram"] = {**cmp_big, "per_fold": pf_big,
                                          "ratio_of_char_gain": ratio}

    print("\n== (2) BM25 + sign-bigram + char n-gram vs BM25 + sign-bigram "
          " [PRIMARY] ==")
    ho_both, pf_both = _ngram.fit_two_param(rows, zb, zbig, zchar, fold_of,
                                            base_correct, grid, "bigram+char")
    cmp_incr = _comb.compare(ho_both, ho_big)
    cmp_vs_bm25 = _comb.compare(ho_both, base_correct)
    print(f"  I_char = {cmp_incr['delta']:+.4f} CI "
          f"{[round(x, 4) for x in cmp_incr['delta_ci95']]} "
          f"(+{cmp_incr['n_gained']}/-{cmp_incr['n_lost']})")
    print(f"  (BM25+bigram+char vs BM25 alone: {cmp_vs_bm25['delta']:+.4f})")
    result["arms"]["bm25_plus_bigram_plus_char"] = {
        "vs_bm25_plus_bigram": cmp_incr, "vs_bm25_alone": cmp_vs_bm25,
        "per_fold": pf_both}

    if not cmp_incr["ci_excludes_zero"]:
        historical_verdict = "CHARACTER_GRANULARITY_NOT_THE_POINT"
    elif cmp_incr["delta"] >= INCREMENT_MARGIN:
        historical_verdict = "CHARACTER_GRANULARITY_EARNS_ITS_KEEP"
    else:
        historical_verdict = "INCONCLUSIVE"
    corrected_verdict = practical_increment_verdict(
        cmp_incr["delta"], cmp_incr["delta_ci95"], INCREMENT_MARGIN,
        positive_label="MATERIAL_CHARACTER_INCREMENT_DETECTED",
        below_margin_label="CHARACTER_INCREMENT_BELOW_0.010",
    )
    result["decision"] = {
        "primary_statistic": "I_char = held-out recall@1 delta of "
                             "BM25+bigram+char over BM25+bigram",
        "I_char": cmp_incr["delta"], "I_char_ci95": cmp_incr["delta_ci95"],
        "I_char_ci_excludes_zero": cmp_incr["ci_excludes_zero"],
        "R_bigram": cmp_big["delta"], "ratio_of_char_gain": ratio,
        "verdict": historical_verdict,
        "verdict_is_historical": True,
        "historical_preregistered_verdict": historical_verdict,
        "corrected_interpretation": corrected_verdict,
        "correction_note": (
            "The interval [-0.0012, +0.0324] includes both zero and effects "
            "larger than the 0.010 margin; it is therefore inconclusive, not "
            "an equivalence result."),
    }
    print(f"\n== HISTORICAL PRE-REGISTERED VERDICT: {historical_verdict} ==")
    print(f"== CORRECTED INTERPRETATION: {corrected_verdict} ==")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"written to {OUT}")


if __name__ == "__main__":
    main()
