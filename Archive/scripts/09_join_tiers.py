#!/usr/bin/env python3
"""
09_join_tiers.py -- P2.5 Amendment A3: join-pair tiering, amends
p2_out/join_pairs.jsonl in place.

Usage:
    python scripts/09_join_tiers.py

tier: A = no-overlap seam (n_shared_lines==0); B = minimal seam (1-2
shared lines); C = extended overlap (3+ shared lines).
geometry: RELABELED per spec -- extended overlap (tier C) = HORIZONTAL
join candidate (break runs vertically through the tablet; both
members independently attest the same lines, i.e. the join seam cuts
across line width); no-overlap / single-line seam (tiers A/B) =
VERTICAL join candidate (fragments stack, one's last preserved line
hands off to the other's first). This replaces the old
"duplicate_like"/"seam"/"unclear" labels from 03_unjoin.py entirely.

For every tier-C pair, an exclusive-content variant is computed:
both members' renderings with all lines they share with the OTHER
member in this specific pair deleted. Degenerate-exclusive guard: if
either member's exclusive remainder has < 8 attested signs or < 2
lines, the pair is marked exclusive_untestable=True and excluded from
tier-C exclusive metrics (counted and reported, never silently
dropped).
"""

import json
import random
from collections import Counter
from pathlib import Path

import pandas as pd

OUT_DIR = Path("p2_out")
P25_OUT = Path("p25_out")
SEED = 20260721
DEGENERATE_MIN_SIGNS = 8
DEGENERATE_MIN_LINES = 2


def render_word(signs, states, mode):
    if mode == "full":
        return "-".join(signs)
    out = [s for s, st in zip(signs, states) if st != "restored"]
    return "-".join(out) if out else None


def main() -> None:
    P25_OUT.mkdir(exist_ok=True)
    corpus = pd.read_parquet(OUT_DIR / "corpus.parquet")
    bins_df = pd.read_csv(P25_OUT / "cth_bins.csv")
    is_bin_by_cth = dict(zip(bins_df["cth"], bins_df["is_bin"]))

    reconstructed = {}
    with open(OUT_DIR / "unjoin_reconstructed.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            reconstructed[d["doc_id"]] = d

    pairs = []
    with open(OUT_DIR / "join_pairs.jsonl", encoding="utf-8") as f:
        for line in f:
            pairs.append(json.loads(line))

    # index corpus by (doc_id, line_index_in_doc) -> list of (signs, states)
    # for fast exclusive-rendering lookups on tier-C pairs only
    corpus_idx = {}
    for row in corpus.itertuples():
        key = (row.doc_id, row.line_index_in_doc)
        corpus_idx.setdefault(key, []).append(
            (json.loads(row.signs), json.loads(row.sign_damage_states)))

    def render_exclusive(doc_id, line_idxs):
        full_lines, attested_lines = [], []
        n_attested_signs = 0
        for idx in sorted(line_idxs):
            words = corpus_idx.get((doc_id, idx), [])
            f_parts, a_parts = [], []
            for signs, states in words:
                fw = render_word(signs, states, "full")
                if fw:
                    f_parts.append(fw)
                aw = render_word(signs, states, "attested")
                if aw:
                    a_parts.append(aw)
                    n_attested_signs += len(aw.split("-"))
            if f_parts:
                full_lines.append(" ".join(f_parts))
            if a_parts:
                attested_lines.append(" ".join(a_parts))
        return full_lines, attested_lines, n_attested_signs

    tier_counts = Counter()
    jointype_tier_counts = Counter()
    bin_tier_counts = Counter()
    shared_line_hist = Counter()
    n_exclusive_untestable = 0
    n_tier_c = 0
    worked_examples = {}
    tier_c_spotcheck = []

    enriched = []
    for p in pairs:
        n = p["n_shared_lines"]
        if n == 0:
            tier = "A"
        elif n <= 2:
            tier = "B"
        else:
            tier = "C"
        geometry = "horizontal" if tier == "C" else "vertical"

        cth = p.get("cth")
        parent_is_bin = bool(is_bin_by_cth.get(cth, False))

        p["tier"] = tier
        p["geometry"] = geometry
        p["parent_is_bin"] = parent_is_bin
        p.pop("junction_geometry", None)  # replaced by 'geometry' above

        tier_counts[tier] += 1
        jointype_tier_counts[(tier, p["join_type"])] += 1
        bin_tier_counts[(tier, parent_is_bin)] += 1
        shared_line_hist[n] += 1

        if tier == "C":
            n_tier_c += 1
            doc_id = p["parent_doc"]
            rec = reconstructed.get(doc_id)
            if rec is not None:
                sig_a, sig_b = p["member_a"]["siglum"], p["member_b"]["siglum"]
                lines_a = rec["member_lines"].get(sig_a, [])
                lines_b = rec["member_lines"].get(sig_b, [])
                excl_idx_a = [e["line_idx"] for e in lines_a if sig_b not in e["shared_with"]]
                excl_idx_b = [e["line_idx"] for e in lines_b if sig_a not in e["shared_with"]]

                full_a, att_a, n_sign_a = render_exclusive(doc_id, excl_idx_a)
                full_b, att_b, n_sign_b = render_exclusive(doc_id, excl_idx_b)

                untestable = (n_sign_a < DEGENERATE_MIN_SIGNS or n_sign_b < DEGENERATE_MIN_SIGNS
                              or len(excl_idx_a) < DEGENERATE_MIN_LINES
                              or len(excl_idx_b) < DEGENERATE_MIN_LINES)
                if untestable:
                    n_exclusive_untestable += 1

                p["members_exclusive"] = True
                p["exclusive_untestable"] = untestable
                p["exclusive_content"] = {
                    "member_a_full": full_a, "member_a_attested": att_a,
                    "member_a_n_attested_signs": n_sign_a, "member_a_n_lines": len(excl_idx_a),
                    "member_b_full": full_b, "member_b_attested": att_b,
                    "member_b_n_attested_signs": n_sign_b, "member_b_n_lines": len(excl_idx_b),
                }

                if tier not in worked_examples and not untestable:
                    worked_examples[tier] = p
                if not untestable:
                    tier_c_spotcheck.append(p)
            else:
                p["members_exclusive"] = False
                p["exclusive_untestable"] = None

        if tier != "C":
            worked_examples.setdefault(tier, p)

        enriched.append(p)

    with open(OUT_DIR / "join_pairs.jsonl", "w", encoding="utf-8") as f:
        for p in enriched:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    lines_out = [
        "# P2.5 A3 -- Join Tiers Report", "",
        f"- Total pairs: {len(enriched)}",
        "", "## Tier counts", "",
        "| tier | geometry | count |", "|---|---|---|",
    ]
    for tier, geom in (("A", "vertical"), ("B", "vertical"), ("C", "horizontal")):
        lines_out.append(f"| {tier} | {geom} | {tier_counts.get(tier, 0)} |")

    lines_out += ["", "## Tier x join_type", "", "| tier | join_type | count |", "|---|---|---|"]
    for (tier, jt), cnt in sorted(jointype_tier_counts.items(), key=lambda x: (x[0][0], x[0][1] or "")):
        lines_out.append(f"| {tier} | {jt} | {cnt} |")

    lines_out += ["", "## Tier x parent_is_bin", "", "| tier | parent_is_bin | count |", "|---|---|---|"]
    for (tier, is_bin), cnt in sorted(bin_tier_counts.items(), key=lambda x: (x[0][0], x[0][1])):
        lines_out.append(f"| {tier} | {is_bin} | {cnt} |")

    lines_out += ["", "## n_shared_lines histogram", "", "| n_shared_lines | count |", "|---|---|"]
    for n, cnt in sorted(shared_line_hist.items()):
        lines_out.append(f"| {n} | {cnt} |")

    lines_out += [
        "",
        "## Tier-C exclusive-content variant",
        f"- Tier-C pairs: {n_tier_c}",
        f"- exclusive_untestable (< {DEGENERATE_MIN_SIGNS} attested signs "
        f"or < {DEGENERATE_MIN_LINES} lines remaining after shared-line "
        f"deletion in EITHER member): {n_exclusive_untestable} "
        f"({100*n_exclusive_untestable/n_tier_c:.1f}% of tier-C, if tier-C > 0)"
        if n_tier_c else "- No tier-C pairs found.",
        "",
        "**Evaluation policy (for the eval harness in a later phase): "
        "tier A is the headline physical-join metric; tier B secondary; "
        "tier C is reported ONLY via the exclusive-content variant as "
        "the honest number (excluding exclusive_untestable pairs), with "
        "the full-reconstruction number shown alongside labeled as an "
        "upper bound (it is contaminated by shared-line duplication).**",
        "",
        "## Worked examples (one per tier)", "",
    ]
    for tier in ("A", "B", "C"):
        ex = worked_examples.get(tier)
        if not ex:
            lines_out.append(f"### Tier {tier}: none available\n")
            continue
        lines_out.append(f"### Tier {tier} -- {ex['parent_doc']} "
                          f"({ex['member_a']['manuscript']} <-> {ex['member_b']['manuscript']})")
        lines_out.append(f"- join_type: {ex['join_type']}, n_shared_lines: "
                          f"{ex['n_shared_lines']}, parent_is_bin: {ex['parent_is_bin']}")
        if tier == "C" and ex.get("exclusive_content"):
            ec = ex["exclusive_content"]
            lines_out.append(f"- member_a exclusive ATTESTED "
                              f"({ec['member_a_n_lines']} lines, "
                              f"{ec['member_a_n_attested_signs']} signs): "
                              f"{' / '.join(ec['member_a_attested'][:3])}")
            lines_out.append(f"- member_b exclusive ATTESTED "
                              f"({ec['member_b_n_lines']} lines, "
                              f"{ec['member_b_n_attested_signs']} signs): "
                              f"{' / '.join(ec['member_b_attested'][:3])}")
        lines_out.append("")

    lines_out += [
        "## Tier-C exclusive-content spot-check (3 pairs, acceptance check 4)",
        "",
        f"Seeded random sample (seed={SEED}) from "
        f"{len(tier_c_spotcheck)} testable tier-C pairs, showing full "
        "reconstruction (contaminated by the shared overlap) vs. "
        "exclusive-content rendering (shared lines removed) side by "
        "side, to make visible exactly what the exclusive variant "
        "strips out.", "",
    ]
    rng = random.Random(SEED)
    spotcheck_sample = rng.sample(tier_c_spotcheck, min(3, len(tier_c_spotcheck)))
    for i, ex in enumerate(spotcheck_sample, 1):
        ec = ex["exclusive_content"]
        lines_out.append(f"### Spot-check {i}/3 -- {ex['parent_doc']} "
                          f"({ex['member_a']['manuscript']} <-> {ex['member_b']['manuscript']})")
        lines_out.append(f"- n_shared_lines: {ex['n_shared_lines']}, "
                          f"join_type: {ex['join_type']}, parent_is_bin: {ex['parent_is_bin']}")
        lines_out.append(f"- member_a FULL ({ec['member_a_n_lines']} exclusive "
                          f"+ {ex['n_shared_lines']} shared lines total): "
                          f"{' / '.join(ec['member_a_full'][:4])}")
        lines_out.append(f"- member_a EXCLUSIVE ATTESTED "
                          f"({ec['member_a_n_lines']} lines, "
                          f"{ec['member_a_n_attested_signs']} signs, shared "
                          f"lines removed): {' / '.join(ec['member_a_attested'][:4])}")
        lines_out.append(f"- member_b FULL: {' / '.join(ec['member_b_full'][:4])}")
        lines_out.append(f"- member_b EXCLUSIVE ATTESTED "
                          f"({ec['member_b_n_lines']} lines, "
                          f"{ec['member_b_n_attested_signs']} signs): "
                          f"{' / '.join(ec['member_b_attested'][:4])}")
        lines_out.append("")

    with open(P25_OUT / "join_tiers_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print(f"Done. Tiers: A={tier_counts.get('A',0)}, B={tier_counts.get('B',0)}, "
          f"C={tier_counts.get('C',0)}. Tier-C exclusive_untestable: {n_exclusive_untestable}.")
    print(f"join_pairs.jsonl amended in place. Report in: {P25_OUT.resolve()}")


if __name__ == "__main__":
    main()
