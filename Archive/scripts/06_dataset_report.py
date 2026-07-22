#!/usr/bin/env python3
"""
06_dataset_report.py -- P2 master acceptance-check report (Deliverable
5 checks + FULL vs ATTESTED cleanroom rendering samples).

Usage:
    python scripts/06_dataset_report.py

Reads all p2_out/ artifacts from 02-05. FULL and ATTESTED renderings
are computed here from corpus.parquet's existing signs/
sign_damage_states columns rather than materialized as new columns
for all 1.5M words: that data already carries everything needed to
derive either rendering on demand (FULL = all signs; ATTESTED = drop
restored signs, keep laes, keep illegible_x as its literal 'x' mask
token), so persisting a third redundant copy of the text was judged
unnecessary storage for a laptop-scale project. A materialized sample
is written here for the required human sanity check.
"""

import json
import random
from pathlib import Path

import pandas as pd

OUT_DIR = Path("p2_out")
SEED = 20260720
N_SAMPLE_FRAGMENTS = 5


def render_word(signs, states, mode):
    if mode == "full":
        return "-".join(signs)
    out = []
    for s, st in zip(signs, states):
        if st == "restored":
            continue
        out.append(s)
    return "-".join(out) if out else None  # None = word fully vanished under ATTESTED


def render_line(words):
    """words: list of (signs_list, states_list). Returns (full_str, attested_str)."""
    full_parts, attested_parts = [], []
    for signs, states in words:
        full_parts.append(render_word(signs, states, "full"))
        a = render_word(signs, states, "attested")
        if a is not None:
            attested_parts.append(a)
    return " ".join(p for p in full_parts if p), " ".join(attested_parts)


def main() -> None:
    corpus = pd.read_parquet(OUT_DIR / "corpus.parquet")
    doc_table = pd.read_parquet(OUT_DIR / "doc_table.parquet")
    splits = pd.read_parquet(OUT_DIR / "splits.parquet")
    edges = pd.read_parquet(OUT_DIR / "edges.parquet")
    with open(OUT_DIR / "join_pairs.jsonl", encoding="utf-8") as f:
        join_pairs = [json.loads(l) for l in f]

    # ---- attested vs restored sign totals, overall + per split
    doc_splits = doc_table.merge(splits[["doc_id", "main_split"]], on="doc_id", how="left")
    sign_cols = ["attested_sign_count", "restored_sign_count",
                 "laes_sign_count", "illegible_sign_count"]
    overall_totals = doc_splits[sign_cols].sum()
    per_split_totals = doc_splits.groupby("main_split")[sign_cols].sum()

    # ---- top-20 largest compositions by doc/witness count
    top_cth = (doc_table.groupby("cth")["doc_id"].count()
               .sort_values(ascending=False).head(20))

    # ---- per-site counts (already in parse_report.md, restated here for the master report)
    site_counts = doc_table["site"].value_counts()

    # ---- FULL vs ATTESTED sample: 5 fragments, seeded
    rng = random.Random(SEED)
    candidate_docs = doc_table[doc_table["word_count"] > 5]["doc_id"].tolist()
    sample_docs = rng.sample(candidate_docs, min(N_SAMPLE_FRAGMENTS, len(candidate_docs)))

    sample_blocks = []
    for doc_id in sample_docs:
        sub = corpus[corpus["doc_id"] == doc_id].sort_values(
            ["line_index_in_doc", "word_index_in_line"])
        block = [f"### {doc_id}", ""]
        for line_idx, grp in sub.groupby("line_index_in_doc", sort=True):
            words = [(json.loads(r.signs), json.loads(r.sign_damage_states))
                     for r in grp.itertuples()]
            full_str, attested_str = render_line(words)
            label = grp["line_label"].iloc[0]
            if not full_str and not attested_str:
                continue
            block.append(f"- **{label}**")
            block.append(f"  - FULL:     `{full_str}`")
            block.append(f"  - ATTESTED: `{attested_str}`")
        sample_blocks.append("\n".join(block))

    # ---- assemble master report
    lines_out = [
        "# P2 Dataset Report (Deliverable 5 -- master acceptance checks)", "",
        "Aggregates: parse_report.md (D1), unjoin_semantics.md + "
        "join_stats.md (D2), edges_report.md (D3), split_report.md "
        "(D4). This file adds the cross-cutting acceptance-check items "
        "from P2_PARSER_SPEC.md Deliverable 5 not already covered "
        "individually.",
        "",
        "## Acceptance checks summary",
        "",
        "1. Word-token count within ~10% of 1.52M `<w>` elements: "
        "**PASS** (-0.02% delta) -- see parse_report.md",
        "2. Damage-state oracle agreement reported: **DONE** -- "
        "naive hypothesis rejected, corrected hypothesis confirmed "
        "(75.2% exact match on gap-marker-free lines) -- see "
        "parse_report.md",
        "3. >=90% of composite docs unjoined or quarantined: **PASS "
        "(100.0%)** -- see join_stats.md",
        "4. Zero composition-leakage across splits (asserted): "
        "**PASS** -- see split_report.md",
        "5. This report: per-split counts, sign totals, largest "
        "compositions, FULL vs ATTESTED samples -- below",
        "",
        "## Sign totals (attested / restored / laes / illegible_x)",
        "",
        "| scope | attested | restored | laes | illegible_x | "
        "restored share |",
        "|---|---|---|---|---|---|",
    ]

    def sign_row(label, row):
        total = row.sum()
        rf = row["restored_sign_count"] / total if total else 0
        return (f"| {label} | {row['attested_sign_count']:,} | "
                f"{row['restored_sign_count']:,} | {row['laes_sign_count']:,} | "
                f"{row['illegible_sign_count']:,} | {rf:.1%} |")

    lines_out.append(sign_row("overall", overall_totals))
    for split_name in ("train", "dev", "test"):
        if split_name in per_split_totals.index:
            lines_out.append(sign_row(split_name, per_split_totals.loc[split_name]))

    lines_out += ["", "## Top-20 largest compositions (by document/witness count)", "",
                  "| CTH | documents |", "|---|---|"]
    for cth, cnt in top_cth.items():
        lines_out.append(f"| {cth} | {cnt} |")

    lines_out += ["", "## Per-site document counts", "", "| site | documents |", "|---|---|"]
    for site, cnt in site_counts.items():
        lines_out.append(f"| {site} | {cnt} |")

    lines_out += [
        "", "## Fragment / pair / composition counts (cross-reference)",
        f"- Fragments (edges.parquet): {len(edges):,}",
        f"- Join pairs (join_pairs.jsonl): {len(join_pairs):,}",
        f"- Compositions (CTH): {doc_table['cth'].nunique()}",
        f"- Documents: {len(doc_table):,}",
        "",
        "## FULL vs ATTESTED rendering samples "
        f"(seed={SEED}, {N_SAMPLE_FRAGMENTS} fragments, human sanity check)",
        "",
        "ATTESTED = restored (`<del_in>/<del_fin>`) sign content removed "
        "entirely; laes (damaged-but-legible) kept; illegible_x kept as "
        "its literal `x` mask token; words that were *entirely* "
        "restored vanish from the ATTESTED line. This is the strict "
        "eval-time rendering (cleanroom rule: test labels come from "
        "attested content only) -- not annotated for readability.",
        "",
    ]
    lines_out.extend(sample_blocks)

    with open(OUT_DIR / "dataset_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print("Done. dataset_report.md written.")
    print(f"Reports in: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
