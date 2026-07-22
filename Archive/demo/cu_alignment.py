#!/usr/bin/env python3
"""
cu_alignment.py -- Takšan demo: cu-to-token alignment for glyph
rendering. Reusable module (DM1/DM2 will import this for the actual
glyph-cell render), extracted from the DM0 investigation.

Does NOT modify decompose_corpus.py or p4_out/decomposed_corpus.parquet
in any way -- this is a pure rendering/matching layer on top of the
existing (unmodified) P4 artifacts, so it carries zero risk to P4's
already-completed results (D12 tokenizer, D13 fracture calibration,
D14 pretraining, D15 biencoder all stay exactly as they were).

BACKGROUND (full investigation in dm0_cu_report.md): `cu` sometimes
carries a `▒` (illegible-glyph marker, U+2592) that has no
corresponding token in the decomposed per-line token list -- a damage
marker whose generating XML structure (space runs, empty <del_in>/
<del_fin> pairs) does NOT deterministically predict its presence
(two structural hypotheses were tested at full-corpus scale and both
rejected: neither "space inside a damage span" nor "empty del/laes
span closure" comes close to reliably predicting a marker). Rather
than chase that (elusive, possibly non-deterministic) rule further,
this module exploits an ALREADY-CONFIRMED fact instead (DM0 part c):
`▒` always means illegible, regardless of why it's there. An
unattributed `▒` therefore doesn't need a specific token match -- it
can render as a self-evident illegible cell.

Measured coverage (full corpus, 377,195 non-empty-cu lines):
  - EXACT match (no adjustment needed):      218,291 lines (57.9%)
  - EDGE_TRIM (leading/trailing unmatched
    `▒` consumed as extra illegible cells):    89,501 lines (23.7%)
  - SKELETON_ONLY (real-glyph count matches,
    marker positions differ -- approximate
    render, markers redistributed):             5,706 lines ( 1.5%)
  - UNRESOLVED (falls back to
    transliteration-only, per spec 3.2's
    existing PUA/unmapped-glyph fallback):      63,697 lines (16.9%)
Combined renderable: 83.1%.

DM0_RULING.md (2026-07-22, architect ruling on this gate): Conditional
GO ratified; the original "<1% of lines" bar is REPLACED with "<1%
damage-state misattribution on RENDERED lines" (coverage is not error
-- the 16.9% unresolved fallback is a safe non-error, not counted
against the bar). Ruling 2 requires a hand-audit of 30 edge_trim + 15
skeleton_only sampled lines (see demo/dm0_audit_sample.py ->
reports/dm0_audit_report.md) before skeleton_only ships unconditionally.

FIX (2026-07-22, caught while building the audit tooling): align_line()
originally returned cells carrying only a token STRING, never a
damage_state -- meaning no caller could actually render damage-state-
correct glyphs from its output, only token identity. Fixed: align_line
now accepts a `damage_states` list (parallel to `tokens`) and returns
it per-cell, filtered/reordered in lockstep with token filtering for
skeleton_only (never invented, never defaulted to 'attested').
"""
from pathlib import Path

MARKER = "▒"  # ▒, confirmed NOT a real cuneiform codepoint (DM0 part a)


def align_line(cu: str, tokens: list[str], damage_states: list[str] | None = None):
    """cu: the line's `cu` string. tokens: ordered list of decomposed
    token strings for the line (illegible positions are the literal
    string 'x'). damage_states: parallel list (same length/order as
    tokens) of each token's true damage state from decompose_corpus.py
    ('attested'/'restored'/'laes'/'illegible_x') -- REQUIRED for a
    caller to render damage-state-correct cells; omitting it returns
    cells with damage_state=None (token-identity only, no styling
    information), which callers must not render as if it were
    'attested'.

    Returns (category, cells) where category is one of 'exact'/
    'edge_trim'/'skeleton_only'/'unresolved', and cells is a list of
    dicts {kind: 'token'|'marker', token: str|None, damage_state:
    str|None} in cu's left-to-right order (empty list if unresolved --
    caller should fall back to transliteration-only rendering per
    spec 3.2). Marker cells (synthetic, unattributed `▒`) always
    carry damage_state='illegible_x' -- self-evident per DM0 part (c),
    never inferred as anything else.
    """
    n_tok = len(tokens)
    if damage_states is None:
        damage_states = [None] * n_tok

    if len(cu) == n_tok:
        return "exact", [{"kind": "token", "token": t, "damage_state": d}
                         for t, d in zip(tokens, damage_states)]

    diff = len(cu) - n_tok
    if diff > 0:
        left = 0
        while left < len(cu) and cu[left] == MARKER and left < diff:
            left += 1
        right = 0
        while right < len(cu) - left and cu[len(cu) - 1 - right] == MARKER and (left + right) < diff:
            right += 1
        if left + right == diff:
            marker_cell = {"kind": "marker", "token": None, "damage_state": "illegible_x"}
            cells = [dict(marker_cell) for _ in range(left)]
            cells += [{"kind": "token", "token": t, "damage_state": d}
                     for t, d in zip(tokens, damage_states)]
            cells += [dict(marker_cell) for _ in range(right)]
            return "edge_trim", cells

    cu_real_len = len(cu.replace(MARKER, ""))
    n_real_tok = sum(1 for t in tokens if t != "x")
    if cu_real_len == n_real_tok:
        # Real (non-illegible) content lines up in count; marker/x
        # positions differ, so illegible cells are redistributed to
        # match cu's actual marker layout (approximate -- the real
        # tokens keep their relative order, markers fill the gaps).
        # damage_states is filtered in lockstep with tokens so each
        # real token keeps ITS OWN true damage state, just re-sequenced
        # to cu's marker layout -- never invented or defaulted.
        real_pairs = [(t, d) for t, d in zip(tokens, damage_states) if t != "x"]
        cells, ri = [], 0
        for ch in cu:
            if ch == MARKER:
                cells.append({"kind": "marker", "token": None, "damage_state": "illegible_x"})
            else:
                t, d = real_pairs[ri] if ri < len(real_pairs) else (None, None)
                cells.append({"kind": "token", "token": t, "damage_state": d})
                ri += 1
        return "skeleton_only", cells

    return "unresolved", []


def align_corpus_report(decomposed_path=Path("p4_out") / "decomposed_corpus.parquet",
                        oracle_path=Path("p2_out") / "damage_oracle.parquet"):
    """Full-corpus coverage measurement (what dm0_cu_report.md's final
    numbers are drawn from). Returns a dict of category -> count."""
    import pandas as pd
    from collections import Counter

    dec = pd.read_parquet(decomposed_path)
    real = dec[dec["token"] != "<PAR>"]
    per_line_tokens = real.groupby(["doc_id", "line_index_in_doc"])["token"].apply(list).reset_index()

    oracle = pd.read_parquet(oracle_path)
    oracle["cu_str"] = oracle["cu"].fillna("")
    merged = oracle.merge(per_line_tokens, on=["doc_id", "line_index_in_doc"], how="left")
    merged["token"] = merged["token"].apply(lambda x: x if isinstance(x, list) else [])

    pop = merged[merged["cu_str"].str.len() > 0]
    counts = Counter()
    for row in pop.itertuples(index=False):
        category, _ = align_line(row.cu_str, row.token)
        counts[category] += 1
    return dict(counts), len(pop)


if __name__ == "__main__":
    counts, n = align_corpus_report()
    print(f"n lines: {n}")
    for cat, cnt in counts.items():
        print(f"  {cat}: {cnt:,} ({100*cnt/n:.2f}%)")
    renderable = sum(v for k, v in counts.items() if k != "unresolved")
    print(f"combined renderable: {100*renderable/n:.2f}%")
