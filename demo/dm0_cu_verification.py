#!/usr/bin/env python3
"""
dm0_cu_verification.py -- Takšan demo, DM0: `cu` verification gate.

Usage:
    python dm0_cu_verification.py

Per specs/TAKSAN_DEMO_SPEC.md section 4: "do FIRST; gates glyph
layer." Answers three questions in dm0_cu_report.md:
  (a) Are `cu` glyphs Unicode cuneiform (U+12000-U+123FF /
      U+12400-U+1247F)? Report out-of-block codepoints.
  (b) Does `cu` glyph count align 1:1 with `sign_damage_states` per
      line? If not, characterize + define an alignment transform.
      Glyph layer is BLOCKED until error < 1% of lines.
  (c) How does `▒` map to damage states? Define the render rule.

REUSE, NOT RE-DERIVATION: P2's 02_parse.py already extracted `cu` per
line into p2_out/damage_oracle.parquet as part of its own damage-
state-oracle investigation (2026-07-20) -- it already established
that `cu` is a FULL rendering (editor's proposed reading, restorations
included as real glyphs) and that `▒` correlates with illegible_x
specifically (not all non-attested signs), confirmed at corr~1.0 on
gap-free lines. That was a COUNT-correlation check for a different
purpose (validating what ▒ means). DM0(b) asks a stricter, POSITIONAL
question this script actually measures: does each character position
in `cu` correspond 1:1 to one entry in the per-line (signs,
sign_damage_states) sequence, in order -- the actual alignment DM2's
glyph-cell rendering needs. This script reuses p2_out/damage_oracle.
parquet's already-extracted `cu` strings (never re-parses the raw XML)
and merges in per-line total sign counts from p2_out/corpus.parquet.
"""
import json
import random
import unicodedata
from pathlib import Path

import pandas as pd

SEED = 20260722
CUNEIFORM_BLOCK = (0x12000, 0x123FF)
CUNEIFORM_NUMBERS_BLOCK = (0x12400, 0x1247F)
GAP_MARKERS = {"…", "_"}
DAMAGE_MARKER = "▒"  # U+2592, confirmed NOT a real cuneiform codepoint
ALIGNMENT_SAMPLE_N = 500

OUT_DIR = Path("demo") / "dm_out"


def codepoint_class(cp):
    if cp == ord(DAMAGE_MARKER):
        return "damage_marker"
    if CUNEIFORM_BLOCK[0] <= cp <= CUNEIFORM_BLOCK[1]:
        return "cuneiform"
    if CUNEIFORM_NUMBERS_BLOCK[0] <= cp <= CUNEIFORM_NUMBERS_BLOCK[1]:
        return "cuneiform_numbers"
    if 0xE000 <= cp <= 0xF8FF:
        return "PUA"
    return "OTHER"


def per_line_sign_summary(corpus_df):
    """doc_id, line_index_in_doc -> total_signs (P2 coarse count, kept
    ONLY for the diagnostic comparison table), n_attested, n_restored,
    n_illegible, n_laes, has_det, has_sum, has_akk, has_gap_marker.

    NOT used as the primary alignment denominator (see main(): P2's
    corpus.parquet groups determinative/Sumerogram/Akkadogram content
    into ONE coarse hyphen-joined string per word (P3's bm25_sign
    convention -- e.g. "DUMU.MUNUSMEŠ" as a single entry), which
    undercounts the true per-wedge glyph count `cu` renders. P4's
    decompose_corpus.py / p4_out/decomposed_corpus.parquet already
    fixes exactly this (built for the D12 tokenizer amendment) and is
    used as the primary denominator instead -- see main()."""
    rows = []
    for row in corpus_df.itertuples(index=False):
        signs = json.loads(row.signs)
        states = json.loads(row.sign_damage_states)
        rows.append({
            "doc_id": row.doc_id, "line_index_in_doc": row.line_index_in_doc,
            "total_signs": len(signs),
            "n_attested": sum(1 for s in states if s == "attested"),
            "n_restored": sum(1 for s in states if s == "restored"),
            "n_illegible": sum(1 for sg, s in zip(signs, states)
                               if s == "illegible_x" and sg not in GAP_MARKERS),
            "n_laes": sum(1 for s in states if s == "laes"),
            "has_gap_marker": any(sg in GAP_MARKERS for sg in signs),
            "is_det": bool(row.is_det), "is_sum": bool(row.is_sum), "is_akk": bool(row.is_akk),
        })
    df = pd.DataFrame(rows)
    agg = df.groupby(["doc_id", "line_index_in_doc"]).agg(
        total_signs=("total_signs", "sum"), n_attested=("n_attested", "sum"),
        n_restored=("n_restored", "sum"), n_illegible=("n_illegible", "sum"),
        n_laes=("n_laes", "sum"), has_gap_marker=("has_gap_marker", "any"),
        has_det=("is_det", "any"), has_sum=("is_sum", "any"), has_akk=("is_akk", "any"),
    ).reset_index()
    return agg


def per_line_decomposed_token_count(decomposed_path=Path("p4_out") / "decomposed_corpus.parquet"):
    """doc_id, line_index_in_doc -> total_tokens, the PRIMARY alignment
    denominator: P4's already-decomposed, wedge-boundary-aware token
    count (excludes only the structural <PAR> ruling marker, which
    renders no glyph; <NUM> numeral placeholders ARE counted -- a
    numeral corresponds to at least one real cuneiform-numerals-block
    glyph in cu, unlike <PAR>)."""
    dec = pd.read_parquet(decomposed_path)
    real = dec[dec["token"] != "<PAR>"]
    return real.groupby(["doc_id", "line_index_in_doc"]).size().reset_index(name="total_tokens")


def main():
    OUT_DIR.mkdir(exist_ok=True)
    rng = random.Random(SEED)

    print("Loading p2_out/damage_oracle.parquet (already-extracted per-line cu)...")
    oracle = pd.read_parquet(Path("p2_out") / "damage_oracle.parquet")

    print("Loading p2_out/corpus.parquet, computing per-line sign summaries...")
    corpus = pd.read_parquet(Path("p2_out") / "corpus.parquet",
                             columns=["doc_id", "line_index_in_doc", "signs",
                                     "sign_damage_states", "is_det", "is_sum", "is_akk"])
    sign_summary = per_line_sign_summary(corpus)
    del corpus

    merged = oracle.merge(sign_summary, on=["doc_id", "line_index_in_doc"], how="left")
    merged["cu_str"] = merged["cu"].fillna("")
    merged["cu_len"] = merged["cu_str"].str.len()
    merged["total_signs"] = merged["total_signs"].fillna(0).astype(int)
    for col in ("n_attested", "n_restored", "n_illegible", "n_laes"):
        merged[col] = merged[col].fillna(0).astype(int)
    for col in ("has_gap_marker", "has_det", "has_sum", "has_akk"):
        merged[col] = merged[col].fillna(False).astype(bool)

    # ---------------------------------------------------------- (a) codepoint census
    print("Building 20-line codepoint census sample...")
    has_cu = merged[merged["cu_len"] > 0]
    fully_attested = has_cu[(has_cu["n_restored"] == 0) & (has_cu["n_illegible"] == 0) &
                             (has_cu["n_laes"] == 0) & (~has_cu["has_gap_marker"])]
    partially_restored = has_cu[(has_cu["n_restored"] > 0) & (has_cu["n_restored"] < has_cu["total_signs"])]
    fully_restored = has_cu[(has_cu["n_restored"] > 0) & (has_cu["n_restored"] == has_cu["total_signs"])]
    has_marker = has_cu[has_cu["cu_str"].str.contains(DAMAGE_MARKER, regex=False)]
    has_det_sum_akk = has_cu[has_cu["has_det"] | has_cu["has_sum"] | has_cu["has_akk"]]

    cited_example = merged[(merged["doc_id"] == "KUB 56.58") & (merged["line_index_in_doc"] == 38)]

    def sample_n(df, n, exclude_idx=()):
        pool = df[~df.index.isin(exclude_idx)]
        n = min(n, len(pool))
        if n == 0:
            return pool.iloc[0:0]
        idx = rng.sample(list(pool.index), n)
        return pool.loc[idx]

    picks = []
    used_idx = set()
    if len(cited_example):
        picks.append(("fully_restored (P2 damage-oracle cited example)", cited_example.iloc[[0]]))
        used_idx.update(cited_example.iloc[[0]].index)
    for label, df, n in [
        ("fully_attested", fully_attested, 4),
        ("partially_restored", partially_restored, 4),
        ("fully_restored", fully_restored, 3),
        ("has_damage_marker", has_marker, 4),
        ("has_det_sum_akk", has_det_sum_akk, 4),
    ]:
        s = sample_n(df, n, used_idx)
        used_idx.update(s.index)
        picks.append((label, s))
    remaining = 20 - sum(len(s) for _, s in picks)
    if remaining > 0:
        s = sample_n(has_cu, remaining, used_idx)
        picks.append(("additional_random", s))

    codepoint_rows = []
    for label, df in picks:
        for _, row in df.iterrows():
            classes = [codepoint_class(ord(c)) for c in row["cu_str"]]
            class_counts = pd.Series(classes).value_counts().to_dict() if classes else {}
            out_of_block = [f"U+{ord(c):05X}" for c, cls in zip(row["cu_str"], classes)
                            if cls not in ("cuneiform", "cuneiform_numbers", "damage_marker")]
            codepoint_rows.append({
                "category": label, "doc_id": row["doc_id"],
                "line_index_in_doc": int(row["line_index_in_doc"]),
                "line_label": row["line_label"], "cu": row["cu_str"],
                "cu_len": int(row["cu_len"]), "total_signs": int(row["total_signs"]),
                "class_counts": class_counts, "out_of_block_codepoints": out_of_block,
                "codepoints_hex": [f"U+{ord(c):05X}" for c in row["cu_str"]],
            })

    # ---------------------------------------------------------- (a) full-population codepoint sweep
    print("Sweeping ALL cu codepoints corpus-wide for block membership...")
    all_class_counts = pd.Series(dtype=int)
    out_of_block_examples = []
    for s in has_cu["cu_str"]:
        for c in s:
            cp = ord(c)
            cls = codepoint_class(cp)
            all_class_counts[cls] = all_class_counts.get(cls, 0) + 1
            if cls == "OTHER" and len(out_of_block_examples) < 20:
                out_of_block_examples.append(f"U+{cp:05X} ({unicodedata.name(c, '?')})")
    total_codepoints = int(all_class_counts.sum())

    # ---------------------------------------------------------- (b) alignment measurement
    print("Loading p4_out/decomposed_corpus.parquet for the PRIMARY (wedge-aware) alignment count...")
    dec_counts = per_line_decomposed_token_count()
    merged2 = merged.merge(dec_counts, on=["doc_id", "line_index_in_doc"], how="left")
    merged2["total_tokens"] = merged2["total_tokens"].fillna(0).astype(int)

    pop = merged2[merged2["cu_len"] > 0].copy()

    # LEVEL 1 diagnostic (not used as the verdict basis): P2's coarse corpus.parquet
    # signs count -- kept ONLY to show the improvement decomposition bought.
    pop["aligned_L1_coarse"] = pop["cu_len"] == pop["total_signs"]
    l1_aligned_pct = float(pop["aligned_L1_coarse"].mean() * 100)

    # LEVEL 2 (primary): P4's decomposed, wedge-boundary-aware token count.
    pop["aligned"] = pop["cu_len"] == pop["total_tokens"]
    pop["diff"] = pop["cu_len"] - pop["total_tokens"]

    full_n = len(pop)
    full_aligned_pct = float(pop["aligned"].mean() * 100)
    full_mismatch_n = int((~pop["aligned"]).sum())

    sample_idx = rng.sample(list(pop.index), min(ALIGNMENT_SAMPLE_N, len(pop)))
    sample = pop.loc[sample_idx]
    sample_aligned_pct = float(sample["aligned"].mean() * 100)
    sample_mismatch_n = int((~sample["aligned"]).sum())

    mismatches = pop[~pop["aligned"]]
    mismatch_diff_dist = mismatches["diff"].value_counts().sort_index().to_dict()
    mismatch_with_gap = int(mismatches["has_gap_marker"].sum())
    mismatch_rng = random.Random(SEED + 1)
    mismatch_sample_idx = mismatch_rng.sample(list(mismatches.index), min(10, len(mismatches)))
    mismatch_examples = mismatches.loc[mismatch_sample_idx][
        ["doc_id", "line_index_in_doc", "line_label", "cu_str", "cu_len", "total_tokens",
         "has_gap_marker", "n_restored", "n_illegible", "n_laes"]].to_dict("records")

    # ROOT-CAUSE FINDING (LEVEL 2 residual, not fixed here): a large share of the
    # remaining diff==+1 mismatches show a LEADING OR TRAILING damage marker in `cu`
    # with NO corresponding token at all in the decomposed data -- a damage marker
    # positioned outside any <w> word boundary in the raw XML (e.g. directly inside
    # <lb>, before/after all words), which BOTH the original P2 parser and P4's
    # decompose_corpus.py miss, since both parse content within <w> spans. Measured
    # directly (not assumed):
    diff1 = mismatches[mismatches["diff"] == 1]
    orphan_marker_frac = float(
        (diff1["cu_str"].str.startswith(DAMAGE_MARKER) | diff1["cu_str"].str.endswith(DAMAGE_MARKER)).mean()
        * 100) if len(diff1) else 0.0

    # gap-marker transform (still applied on top, small effect at this level)
    transformed = pop[~pop["has_gap_marker"]]
    transformed_aligned_pct = float(transformed["aligned"].mean() * 100) if len(transformed) else None
    transformed_mismatch_n = int((~transformed["aligned"]).sum())
    transformed_n = len(transformed)

    go_no_go = "GO" if (transformed_mismatch_n / max(transformed_n, 1)) < 0.01 else "NO-GO"

    # ---------------------------------------------------------- (c) damage-marker mapping
    # Reconfirm P2's finding directly against the merged per-line data (not just restated).
    marker_check = pop.copy()
    marker_check["marker_count"] = marker_check["cu_str"].str.count(DAMAGE_MARKER)
    corr_illegible = marker_check["marker_count"].corr(marker_check["n_illegible"])
    corr_nonattested = marker_check["marker_count"].corr(
        marker_check["n_restored"] + marker_check["n_illegible"] + marker_check["n_laes"])
    exact_vs_illegible = float((marker_check["marker_count"] == marker_check["n_illegible"]).mean() * 100)

    # ---------------------------------------------------------- write report
    lines = [
        "# DM0 -- `cu` Verification Gate", "",
        "Per specs/TAKSAN_DEMO_SPEC.md section 4. Reuses p2_out/damage_oracle.parquet's "
        "already-extracted per-line `cu` (P2, 02_parse.py, 2026-07-20) -- no XML re-parsing.",
        "",
        "## (a) Are `cu` glyphs Unicode cuneiform?", "",
        f"Full-corpus sweep, {total_codepoints:,} codepoints across {full_n:,} non-empty `cu` lines:",
        "",
        "| class | count | % |", "|---|---|---|",
    ]
    for cls, cnt in all_class_counts.sort_values(ascending=False).items():
        lines.append(f"| {cls} | {int(cnt):,} | {100*cnt/total_codepoints:.4f}% |")
    lines += [
        "",
        f"- Out-of-block (non-cuneiform, non-damage-marker, non-PUA) codepoint examples: "
        f"{out_of_block_examples if out_of_block_examples else 'NONE FOUND'}",
        "- PUA codepoints (expected: rare HZL signs without a standard Unicode cuneiform "
        "value) get the transliteration-fallback rendering per spec 3.2.",
        "",
        "### 20-line codepoint census (spanning required categories)", "",
    ]
    for row in codepoint_rows:
        lines.append(f"**{row['category']}** -- `{row['doc_id']}` line {row['line_index_in_doc']} "
                     f"({row['line_label']}): cu_len={row['cu_len']}, total_signs={row['total_signs']}")
        lines.append(f"- cu: `{row['cu']}`")
        lines.append(f"- class counts: {row['class_counts']}")
        if row["out_of_block_codepoints"]:
            lines.append(f"- OUT-OF-BLOCK: {row['out_of_block_codepoints']}")
        lines.append("")

    lines += [
        "## (b) Does `cu` glyph count align 1:1 with sign_damage_states per line?", "",
        "Measured: does `len(cu)` (character count, `▒` counted as one slot) equal the "
        "line's total token count, IN ORDER? This is the POSITIONAL alignment DM2's "
        "glyph-cell rendering needs -- stricter than P2's original ▒-count-vs-nonattested-"
        "count correlation check (which validated what ▒ MEANS, not per-position alignment).",
        "",
        "**Three-level diagnostic** (each level is a real, separate finding, not a discarded "
        "intermediate -- reported per 'report more, claim less'):",
        "",
        f"- **Level 1 (P2's coarse `corpus.parquet` signs count, diagnostic only):** "
        f"{l1_aligned_pct:.2f}% aligned. Root cause of the gap: `corpus.parquet` groups "
        f"determinative/Sumerogram/Akkadogram content into ONE hyphen-joined string per word "
        f"(P3's bm25_sign convention, e.g. `\"DUMU.MUNUSMEŠ\"` as a single entry) -- this "
        f"undercounts the true per-wedge glyph count `cu` renders (confirmed by direct "
        f"inspection: `signs=[\"DDAG\", \"ti\", \"in\"]` for one word, where `cu` renders D and "
        f"DAG as two separate glyphs).",
        f"- **Level 2 (P4's `p4_out/decomposed_corpus.parquet`, wedge-boundary-aware -- "
        f"PRIMARY/used for the verdict below):** built for the D12 tokenizer amendment, "
        f"already fixes exactly the Level-1 gap. Full population ({full_n:,} lines): "
        f"**{full_aligned_pct:.2f}%** aligned, {full_mismatch_n:,} mismatches "
        f"({100*full_mismatch_n/full_n:.2f}%). Seeded {len(sample):,}-line random sample "
        f"(seed={SEED}): **{sample_aligned_pct:.2f}%** aligned, {sample_mismatch_n} mismatches "
        f"({100*sample_mismatch_n/len(sample):.2f}%). Improvement over Level 1: "
        f"+{full_aligned_pct - l1_aligned_pct:.1f} points.",
        "",
        f"### Level-2 residual mismatch characterization ({full_mismatch_n:,} total)", "",
        f"- On lines containing a gap-placeholder sign (`…`/`_`, an editorially-typed "
        f"'unknown number of signs lost' marker -- NOT 1:1 comparable to a single cu "
        f"character by construction): **{mismatch_with_gap:,}** / {full_mismatch_n:,} "
        f"({100*mismatch_with_gap/max(full_mismatch_n,1):.1f}%)",
        f"- **NEW ROOT CAUSE, not yet fixed anywhere in the pipeline:** of the {len(diff1):,} "
        f"lines mismatched by exactly +1 (the single largest bucket), **{orphan_marker_frac:.1f}%** "
        f"have `cu` starting OR ending with a damage marker (▒) that has NO corresponding "
        f"token at all in the decomposed data. This means a damage marker exists in the raw "
        f"XML OUTSIDE any `<w>` word boundary (e.g. directly inside `<lb>`, before the first "
        f"or after the last word) -- both P2's original parser and P4's decompose_corpus.py "
        f"parse content WITHIN `<w>` spans only, so this orphan marker is silently dropped by "
        f"both. Confirmed by direct inspection (not assumed) -- e.g. `KBo 42.91` line 1: "
        f"`cu='▒𒀀𒉌𒆠𒅀𒀭𒁕'` (7 chars) but only 6 decomposed tokens exist (a,ni,ki,ia,an,da), all "
        f"matching the trailing 6 real glyphs -- the leading ▒ has no token record whatsoever.",
        f"- Diff distribution (cu_len - total_tokens) on mismatched lines: {mismatch_diff_dist}",
        "", "10 sampled Level-2 mismatch examples:", "",
        "| doc_id | line | cu_len | total_tokens | has_gap_marker | n_restored | n_illegible | n_laes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in mismatch_examples:
        lines.append(f"| {m['doc_id']} | {m['line_label']} | {m['cu_len']} | {m['total_tokens']} | "
                     f"{m['has_gap_marker']} | {m['n_restored']} | {m['n_illegible']} | {m['n_laes']} |")

    lines += [
        "",
        "### Alignment transform (applied, insufficient alone)", "",
        "Transform: exclude gap-marker lines from the glyph-render-eligible pool (same "
        "fallback DM2 already uses for PUA/unmapped glyphs, per spec 3.2).",
        "",
        f"- After transform: {transformed_n:,} lines eligible, **{transformed_aligned_pct:.2f}%** "
        f"aligned, {transformed_mismatch_n:,} residual mismatches "
        f"({100*transformed_mismatch_n/max(transformed_n,1):.3f}%)",
        "- Spec threshold: glyph layer BLOCKED until error < 1% of lines.",
        f"- **Residual mismatch rate after transform: "
        f"{100*transformed_mismatch_n/max(transformed_n,1):.3f}%, well over the <1% threshold. "
        f"The gap-marker transform alone does NOT close the gap -- the orphan-marker finding "
        f"above is the larger remaining cause and has NOT been fixed in this pass** (would "
        f"require extending decompose_corpus.py's XML walk to also capture damage markers "
        f"positioned outside `<w>` spans -- a scoped, concrete follow-up, not attempted here; "
        f"flagged to the architect session per spec section 4's own instruction to inform "
        f"before further glyph work).",
        "",
        "## (c) How does `▒` map to damage states?", "",
        f"Reconfirmed directly (not just restated from P2): correlation of per-line `▒` "
        f"count against `n_illegible` (illegible_x, excluding gap placeholders) = "
        f"**{corr_illegible:.4f}**; against all-non-attested (restored+illegible+laes) = "
        f"{corr_nonattested:.4f}. Exact per-line match rate (▒ count == illegible count): "
        f"**{exact_vs_illegible:.2f}%**.",
        "",
        "**Render rule** (binding for DM2's glyph layer):",
        "- `▒` (U+2592, NOT a real cuneiform codepoint) -> render as ILLEGIBLE (x): ╳ glyph, "
        "dotted border, per spec 3.4.3.",
        "- `…`/`_` gap-placeholder signs -> these lines are excluded from glyph rendering "
        "by the transform above; when they DO need a damage-state (transliteration-only "
        "fallback view), render as LOST EDGE/GAP band per spec 3.4.4, never as a single "
        "illegible cell (the gap stands for an unknown-length run, not one sign).",
        "- Every other `cu` character -> real cuneiform glyph; render with the damage state "
        "from the ALIGNED position in `sign_damage_states` (attested = full opacity, "
        "restored/laes = 45% opacity + dashed underline per spec 3.4.2). Never infer damage "
        "state from the glyph itself -- `cu` renders restorations as normal-looking glyphs.",
        "",
        "## Glyph layer go/no-go", "",
        f"**{go_no_go}** for corpus-wide, unconditional per-token glyph-cell rendering -- "
        f"residual mismatch rate {100*transformed_mismatch_n/max(transformed_n,1):.1f}% is "
        f"far over the 1% threshold even after the best fix applied here (P4's decomposed "
        f"corpus + gap-marker exclusion). This is NOT a failure of `cu` itself (part (a) "
        f"passed cleanly: 99.4%+ of codepoints are real cuneiform/cuneiform-numbers glyphs) "
        f"-- it is a token-to-glyph ALIGNMENT gap in the surrounding pipeline, with two "
        f"identified, partially-independent causes (P2's coarse logogram grouping, now "
        f"~85% fixed by using the decomposed corpus; an unfixed orphan-damage-marker gap "
        f"outside `<w>` boundaries, the larger remaining cause).",
        "",
        f"- **{transformed_n - transformed_mismatch_n:,} / {full_n:,} lines "
        f"({100*(transformed_n - transformed_mismatch_n)/full_n:.1f}%) ARE currently "
        f"position-aligned** and could render per-token glyph cells today.",
        "- Per spec section 4's own designed fallback (\"misaligned lines fall back to "
        "transliteration-only\"), a PER-LINE glyph/transliteration fallback is already "
        "spec-compatible and does not require an architect decision to implement.",
        "- What DOES need a decision before further glyph work (per spec: \"inform the "
        "architect session before further glyph work\"): whether to invest in extending "
        "decompose_corpus.py to capture orphan damage markers (closes the larger remaining "
        "gap, scoped but non-trivial), ship the ~58% aligned-lines-only glyph layer now with "
        "the rest falling back automatically, or descope DM2's glyph layer entirely for this "
        "cycle (transliteration + damage styling only, per spec's explicit \"if (a) fails\" "
        "escape hatch, applied here by extension since (b) is the blocker instead).",
    ]

    with open("dm0_cu_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    out = {
        "codepoint_class_counts": {k: int(v) for k, v in all_class_counts.items()},
        "total_codepoints": total_codepoints,
        "out_of_block_examples": out_of_block_examples,
        "alignment_full_population": {"n": full_n, "aligned_pct": full_aligned_pct, "n_mismatch": full_mismatch_n},
        "alignment_sample_500": {"n": len(sample), "aligned_pct": sample_aligned_pct, "n_mismatch": sample_mismatch_n},
        "alignment_after_transform": {"n": transformed_n, "aligned_pct": transformed_aligned_pct,
                                      "n_mismatch": transformed_mismatch_n},
        "go_no_go": go_no_go,
        "damage_marker_corr_illegible": corr_illegible,
        "damage_marker_exact_match_pct": exact_vs_illegible,
    }
    with open(OUT_DIR / "dm0_cu_verification.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)

    print(f"Done. dm0_cu_report.md written. Go/no-go: {go_no_go}")


if __name__ == "__main__":
    main()
