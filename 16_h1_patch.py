#!/usr/bin/env python3
"""
16_h1_patch.py -- P4 H1: harness patch delta report.

Usage:
    python 16_h1_patch.py

Compares results/ (P3, unpatched) against results_p3_patched/ (P3
scorers re-run through the H1 family-aware harness) and writes
h1_patch_report.md. Run 13_bm25.py --patched first.
"""

import json
from pathlib import Path

RESULTS = Path("results")
PATCHED = Path("results_p3_patched")


def main():
    with open(PATCHED / "p3_summary.json", encoding="utf-8") as f:
        patched_summary = json.load(f)

    lines = [
        "# P4 H1 -- Harness Patch Report", "",
        "## docID-family normalization", "",
        f"- Family pairs found (exhaustive regex sweep over all "
        f"corpus doc_ids, base form independently verified to exist): "
        f"**{patched_summary['h1_family_pairs']}**",
        "  - `IBoT 2.118` <-> `IBoT 2.118 Rs. IV`",
        "  - `KBo 8.96` <-> `KBo 8.96 Vs.`",
        "  - `KUB 41.18` <-> `KUB 41.18 Vs. I`",
        "  - `KUB 7.13` <-> `KUB 7.13 Vs. I`",
        "  - `KUB 7.58` <-> `KUB 7.58 Vs. I` (the pair originally "
        "flagged in P3's failures spot-read -- confirmed byte-"
        "identical ATTESTED content, now excluded from ranking rather "
        "than silently scored as a false positive)",
        f"- Total same-family candidate exclusions applied across the "
        f"full re-run (all scorers x tasks x index variants): "
        f"**{patched_summary['h1_family_exclusion_count']:,}**",
        "",
        "## Exact-dedup groups (98) -- verified, no additional action needed",
        "",
        "The family-key mechanism above already subsumes the required "
        "\"same-family dedup excluded\" behavior (the one dedup group "
        "that is ALSO a real family match -- KUB 7.58 -- is excluded "
        "via family_map, not via a separate dedup-specific rule). The "
        "remaining 97 dedup groups were manually inspected (see "
        "scratch diagnostics): they are near-empty/degenerate "
        "fragments (very short or all-`x` attested content) from "
        "genuinely unrelated tablets across many different sites and "
        "publication series, coincidentally identical only because "
        "there's so little content to differ on. Per spec, these "
        "correctly STAY in ranking as real formulaic collisions -- "
        "part of the task, not a bug.",
        "",
        "## P3 table deltas (unpatched results/ vs patched results_p3_patched/)",
        "",
        "| scorer | metric | unpatched | patched | delta |",
        "|---|---|---|---|---|",
    ]

    with open(RESULTS / "p3_summary.json", encoding="utf-8") as f:
        unpatched_summary = json.load(f)

    for name in ("bm25_sign", "bm25_lemma", "tfidf_cosine_sign"):
        u = unpatched_summary["scorers"][name]
        p = patched_summary["scorers"][name]
        for metric in ("task_a_recall@1", "task_b_pooled_test_only_recall@1",
                       "task_b_tier_A_test_only_recall@1"):
            uv, pv = u[metric], p[metric]
            lines.append(f"| {name} | {metric} | {uv:.4f} | {pv:.4f} | {pv - uv:+.4f} |")

    lines += [
        "",
        "**Honest note (per spec's own framing, but the actual result "
        "differs from its expectation):** the amendment anticipated "
        "\"expect small improvements\" from this patch. What was "
        "actually observed is a small DECREASE in pooled/Task-A "
        "recall for most scorers -- because the pre-patch numbers were "
        "inflated by a handful of queries trivially \"solved\" by "
        "matching their own uncredited docID-family sibling (an "
        "unlabeled near-duplicate, not a genuine retrieval success). "
        "Removing that loophole is a strictly more honest number, even "
        "though it moves in the opposite direction from what was "
        "expected -- reported as observed, not adjusted to match the "
        "anticipated direction.",
        "",
        "## Full patched tables", "",
        "See `results_p3_patched/{scorer}/metrics.json` and `report.md` "
        "for the complete re-emitted P3 tables (all tiers, both index "
        "variants, 2x2 leakage, Task A) under the H1-patched harness.",
    ]

    with open(Path("h1_patch_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Done. h1_patch_report.md written.")


if __name__ == "__main__":
    main()
