#!/usr/bin/env python3
"""Real-gaps production pipeline -- Step 1: structural census.

Ixca's direction (2026-07-25): build the real-gap-filling pipeline one
step at a time, evaluating results before continuing, and -- for
`restored` spans specifically -- check the editor's own restoration
against independent witness evidence rather than presuming it correct
("let the artifacts do the talking, not the editors").

This step does NOT build a witness index or query anything yet. It only
answers: how many genuine gaps exist, and what does the editor's own
restored content look like where one exists. That's the number needed
before deciding whether the witness-matching layer (step 2) is worth
building at the scale being considered.

Scope, matching the project's own established conventions:
  - train + dev only. Bins (`main_split == "discovery"`) excluded, per
    the P2.5 bin reframe (a bin fragment's CTH membership isn't
    reliable, so composition-scoped witness comparison doesn't apply to
    it). Test excluded absolutely, via lib.contracts.assert_no_test --
    not just as a query source, but as a witness source too, so this
    new pipeline never opens the frozen split in any capacity.
  - "Real gap" = a contiguous run of `restored` or `illegible_x` tokens
    in the decomposed sign stream (Phase1_pipeline/p4_out/
    decomposed_corpus.parquet), grouped by (doc_id, line_index_in_doc),
    ordered by word_pos.

Usage:
    python scripts/real_gap_census.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import contracts  # noqa: E402

import pandas as pd  # noqa: E402

from phase2_io import split_lookup_fail_closed  # noqa: E402

SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
DECOMPOSED_PATH = Path("Phase1_pipeline/p4_out/decomposed_corpus.parquet")
DOC_TABLE_PATH = Path("Phase1_pipeline/p2_out/doc_table.parquet")

OUT_DIR = Path("Phase3/real_gaps_out")
OUT_JSON = OUT_DIR / "real_gap_census.json"
REPORT_PATH = OUT_DIR / "real_gap_census_report.md"

REAL_GAP_STATES = {"restored", "illegible_x"}


def load_allowed_doc_ids():
    """train + dev only, bins and test excluded. Returns (allowed_ids,
    split_lookup, ambiguous) -- split_lookup covers only unambiguous docs
    so assert_no_test can verify status for anything encountered.

    Docs with more than one distinct main_split value across duplicate
    splits.parquet rows (a real, pre-existing data-quality wrinkle --
    caught live: 'HT 39' resolves to 'discovery' under one CTH and 'test'
    under another) are excluded from the allowed set entirely, matching
    the existing convention in scripts/p2e_witness_recoverability.py's
    load_dev_inputs() (split_lookup_fail_closed() already omits them from
    the lookup, so they're never selected) -- reported here, not
    silently dropped, and never guessed at."""
    splits = pd.read_parquet(
        SPLITS_PATH, columns=["doc_id", "cth", "is_bin", "main_split"])
    split_lookup, ambiguous = split_lookup_fail_closed(splits)

    allowed = {
        doc_id for doc_id, split in split_lookup.items()
        if split in ("train", "dev")
    }
    bin_rows = splits[splits["doc_id"].isin(allowed) & splits["is_bin"]]
    if len(bin_rows):
        raise SystemExit(
            f"CENSUS ABORT: {len(bin_rows)} train/dev doc_id(s) are "
            f"flagged is_bin=True -- bin reframe violated, refusing to "
            f"proceed."
        )
    contracts.assert_no_test(allowed, split_lookup, label="real-gap census")
    return allowed, split_lookup, ambiguous


def find_runs(doc_id, line_idx, tokens):
    """tokens: ordered list of (word_pos, token, damage_state,
    word_index_in_line). Yields one dict per contiguous run of
    REAL_GAP_STATES tokens."""
    run = []

    def flush():
        if not run:
            return None
        return {
            "doc_id": doc_id,
            "line_index_in_doc": line_idx,
            "length": len(run),
            "damage_states": [t[2] for t in run],
            "tokens": [t[1] for t in run],
            "word_indices": sorted({t[3] for t in run if t[3] is not None}),
            "is_pure_restored": all(t[2] == "restored" for t in run),
            "is_pure_illegible": all(t[2] == "illegible_x" for t in run),
            # Exact word_pos span (in the RAW per-line token list this run
            # was found in) -- lets a downstream consumer locate the run's
            # precise position directly, rather than re-matching by content
            # (fragile if a duplicate token+damage_state sequence occurs
            # more than once in the same line).
            "word_pos_start": run[0][0],
            "word_pos_end": run[-1][0],
        }

    for word_pos, token, state, widx in tokens:
        if state in REAL_GAP_STATES:
            run.append((word_pos, token, state, widx))
        else:
            found = flush()
            if found:
                yield found
            run = []
    found = flush()
    if found:
        yield found


def main():
    allowed_ids, split_lookup, ambiguous_ids = load_allowed_doc_ids()
    print(f"Allowed (train+dev, non-bin) documents: {len(allowed_ids):,}")
    if ambiguous_ids:
        print(f"Excluded (ambiguous main_split across duplicate rows): "
              f"{len(ambiguous_ids)} -- {sorted(ambiguous_ids)}")

    doc_table = pd.read_parquet(
        DOC_TABLE_PATH, columns=["doc_id", "cth", "site"])
    doc_cth = dict(zip(doc_table["doc_id"], doc_table["cth"]))
    doc_site = dict(zip(doc_table["doc_id"], doc_table["site"]))

    decomposed = pd.read_parquet(
        DECOMPOSED_PATH,
        columns=["doc_id", "line_index_in_doc", "word_pos", "token",
                  "damage_state", "word_index_in_line"],
        filters=[("doc_id", "in", list(allowed_ids))],
    )
    contracts.assert_no_test(
        set(decomposed["doc_id"]), split_lookup, label="real-gap census decomposed read")
    print(f"Decomposed rows loaded: {len(decomposed):,}")

    decomposed = decomposed.sort_values(
        ["doc_id", "line_index_in_doc", "word_pos"])

    runs = []
    docs_with_runs = set()
    for (doc_id, line_idx), group in decomposed.groupby(
            ["doc_id", "line_index_in_doc"], sort=False):
        tokens = [
            (int(r.word_pos), r.token, r.damage_state,
             None if pd.isna(r.word_index_in_line) else int(r.word_index_in_line))
            for r in group.itertuples(index=False)
        ]
        for run in find_runs(doc_id, int(line_idx), tokens):
            run["cth"] = doc_cth.get(doc_id)
            run["site"] = doc_site.get(doc_id)
            runs.append(run)
            docs_with_runs.add(doc_id)

    n_restored_pure = sum(1 for r in runs if r["is_pure_restored"])
    n_illegible_pure = sum(1 for r in runs if r["is_pure_illegible"])
    n_mixed = len(runs) - n_restored_pure - n_illegible_pure

    length_counter = Counter(r["length"] for r in runs)
    cth_counter = Counter(r["cth"] for r in runs)

    # For pure-restored runs: what does the editor's own content actually
    # look like? (Not yet compared to anything -- that's step 2.)
    restored_runs = [r for r in runs if r["is_pure_restored"]]
    empty_restored = sum(1 for r in restored_runs if not any(t.strip() for t in r["tokens"]))
    restored_length_counter = Counter(r["length"] for r in restored_runs)

    docs_by_cth = defaultdict(set)
    for doc_id in allowed_ids:
        docs_by_cth[doc_cth.get(doc_id)].add(doc_id)
    cth_doc_counts = {cth: len(ids) for cth, ids in docs_by_cth.items()}

    top_cths = cth_counter.most_common(15)

    result = {
        "allowed_documents": len(allowed_ids),
        "excluded_ambiguous_split_documents": sorted(ambiguous_ids),
        "documents_with_at_least_one_real_gap": len(docs_with_runs),
        "total_real_gap_runs": len(runs),
        "runs_pure_restored": n_restored_pure,
        "runs_pure_illegible": n_illegible_pure,
        "runs_mixed_restored_and_illegible": n_mixed,
        "run_length_distribution": dict(sorted(length_counter.items())),
        "restored_run_length_distribution": dict(sorted(restored_length_counter.items())),
        "restored_runs_with_empty_editor_content": empty_restored,
        "restored_runs_total": len(restored_runs),
        "top_15_cths_by_real_gap_count": [
            {"cth": cth, "real_gap_runs": count,
              "documents_in_composition": cth_doc_counts.get(cth, 0)}
            for cth, count in top_cths
        ],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    report_lines = [
        "# Real-gap structural census (step 1)",
        "",
        "Pure structural count -- no witness lookup, no calibration, no UI.",
        "Scope: train + dev documents only (bins and test excluded; test",
        "exclusion checked via `lib.contracts.assert_no_test`, twice --",
        "once on the allowed-ID set, once on what the decomposed reader",
        "actually returned).",
        "",
        f"- **{result['allowed_documents']:,}** train/dev, non-bin documents in scope. "
        f"**{len(result['excluded_ambiguous_split_documents'])}** additional doc_id(s) excluded entirely "
        "for a real, pre-existing data problem this census surfaced: duplicate `splits.parquet` rows under "
        "different CTH numbers with disagreeing `main_split` values (one, `HT 39`, resolves to `test` under "
        "one interpretation) -- quarantined rather than guessed, matching "
        "`scripts/p2e_witness_recoverability.py`'s existing convention.",
        f"- **{result['documents_with_at_least_one_real_gap']:,}** of those have at least one real gap "
        f"({result['documents_with_at_least_one_real_gap'] / result['allowed_documents'] * 100:.1f}%).",
        f"- **{result['total_real_gap_runs']:,}** total real-gap runs found "
        f"({result['runs_pure_restored']:,} pure `restored`, "
        f"{result['runs_pure_illegible']:,} pure `illegible_x`, "
        f"{result['runs_mixed_restored_and_illegible']:,} mixed within one contiguous run).",
        "",
        "## Run length distribution (all real gaps, signs)",
        "",
        "| length | count |",
        "|---|---|",
    ]
    for length, count in sorted(length_counter.items()):
        report_lines.append(f"| {length} | {count:,} |")

    report_lines += [
        "",
        "## Restored-run editor content (not yet compared to anything)",
        "",
        f"Of {result['restored_runs_total']:,} pure-`restored` runs, "
        f"**{result['restored_runs_with_empty_editor_content']:,}** have no non-blank editor "
        "content at all (a restoration placeholder with nothing proposed).",
        "",
        "| length | count |",
        "|---|---|",
    ]
    for length, count in sorted(restored_length_counter.items()):
        report_lines.append(f"| {length} | {count:,} |")

    report_lines += [
        "",
        "## Top 15 compositions by real-gap count",
        "",
        "| CTH | real-gap runs | documents in composition |",
        "|---|---|---|",
    ]
    for row in result["top_15_cths_by_real_gap_count"]:
        report_lines.append(
            f"| {row['cth']} | {row['real_gap_runs']:,} | {row['documents_in_composition']:,} |")

    report_lines += [
        "",
        "## What this does not yet tell us",
        "",
        "Whether any independent witness exists for any of these gaps at all "
        "(step 2: build the anchor-context witness index and query it), or "
        "whether the editor's restored content agrees with what witnesses "
        "independently attest (step 3, restored spans only, per Ixca's "
        "\"let the artifacts do the talking\" framing). This step only "
        "establishes there is a real, sizeable population to build that "
        "layer for.",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Found {len(runs):,} real-gap runs across {len(docs_with_runs):,} documents.")
    print(f"Report: {REPORT_PATH}")
    print(f"JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
