#!/usr/bin/env python3
"""
05_splits.py -- Leakage-safe train/dev/test splits, by CTH composition.

Usage:
    python 05_splits.py

Reads p2_out/doc_table.parquet (from 02_parse.py). Two independent
split axes are produced, per P2_PARSER_SPEC.md Deliverable 4:

1. main_split (train/dev/test, ~80/10/10): the unit of assignment is
   the WHOLE CTH composition -- every document of a composition lands
   on the same side, so joined-doc members (same parent doc, same
   CTH) automatically co-travel. Stratified by (size_band, genre_band)
   so rare/large compositions aren't all dumped in one split.
2. site_split (train_hattusa / test_provincial / excluded): the
   CLAUDE.md headline generalization experiment. This is DELIBERATELY
   NOT composition-disjoint -- the same composition can supply both
   Hattusa and provincial witnesses, which is the whole point (does a
   model trained on the capital's material generalize to a newly-
   excavated provincial fragment of a composition it already knows?).
   It is an independent column, not a replacement for main_split.

genre_band is CTH // 100 -- a COARSE NUMERIC-RANGE PROXY only, not a
scholarly genre classification (no authoritative live catalog lookup
was performed here); documented per CLAUDE.md's "explicit, never
silent" standard rather than presented as real genre metadata.

"unknown"-site docs (CHDS/DBH/FHL/DAAM/UBT/VSNF/HFAC/Privat/... --
2,263 docs) are very likely Boğazköy/Hattusa material published under
different museum/series sigla not yet in SITE_PREFIXES, not genuine
provincial finds -- they are excluded from cross_site eval rather than
guessed into either bucket, and flagged for expert prefix review.
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

OUT_DIR = Path("p2_out")
SEED = 20260720
CORPUS_VERSION = "TLHdig_0.2.0-beta"
TRAIN_FRAC, DEV_FRAC, TEST_FRAC = 0.8, 0.1, 0.1

PROVINCIAL_SITES = {
    "Masat/Tapikka", "Ortakoy/Sapinuwa", "Kusakli/Sarissa",
    "Kayalipinar/Samuha", "Ugarit", "Emar", "Alalakh",
}
HATTUSA_SITES = {"Hattusa", "Hattusa(coll.)"}


def size_band(n):
    if n <= 1:
        return "1"
    if n <= 5:
        return "2-5"
    if n <= 20:
        return "6-20"
    if n <= 50:
        return "21-50"
    return "51+"


def main() -> None:
    doc_table = pd.read_parquet(OUT_DIR / "doc_table.parquet")
    doc_table = doc_table[doc_table["cth"].notna()].copy()
    doc_table["cth"] = doc_table["cth"].astype(int)

    # ---- composition table
    comp = doc_table.groupby("cth").agg(
        n_docs=("doc_id", "count"),
        sites=("site", lambda s: sorted(set(s))),
    ).reset_index()
    comp["size_band"] = comp["n_docs"].apply(size_band)
    comp["genre_band"] = (comp["cth"] // 100 * 100).astype(int)
    comp["strata"] = list(zip(comp["size_band"], comp["genre_band"]))

    # ---- stratified composition-level split (main_split)
    rng = random.Random(SEED)
    strata_groups = defaultdict(list)
    for row in comp.itertuples():
        strata_groups[row.strata].append(row.cth)

    cth_assignment = {}
    for strata, cths in strata_groups.items():
        cths = sorted(cths)  # deterministic order before shuffling
        rng.shuffle(cths)
        n = len(cths)
        n_train = round(n * TRAIN_FRAC)
        n_dev = round(n * DEV_FRAC)
        # guarantee dev/test get at least something when a stratum is
        # tiny, rather than silently starving them via rounding
        if n >= 3:
            n_train = min(n_train, n - 2)
            n_dev = max(n_dev, 1)
        train_cths = cths[:n_train]
        dev_cths = cths[n_train:n_train + n_dev]
        test_cths = cths[n_train + n_dev:]
        for c in train_cths:
            cth_assignment[c] = "train"
        for c in dev_cths:
            cth_assignment[c] = "dev"
        for c in test_cths:
            cth_assignment[c] = "test"

    comp["main_split"] = comp["cth"].map(cth_assignment)
    doc_table["main_split"] = doc_table["cth"].map(cth_assignment)

    # ---- acceptance check #4: zero composition leakage, asserted
    leak_check = doc_table.groupby("cth")["main_split"].nunique()
    n_leaked = int((leak_check > 1).sum())
    assert n_leaked == 0, (
        f"COMPOSITION LEAKAGE DETECTED: {n_leaked} CTH compositions "
        "span more than one split. This must never happen -- aborting "
        "rather than writing a leaking split.")

    # ---- site_split (independent axis, deliberately not comp-disjoint)
    def site_split_for(site):
        if site in HATTUSA_SITES:
            return "train_hattusa"
        if site in PROVINCIAL_SITES:
            return "test_provincial"
        return "excluded_unknown_site"

    doc_table["site_split"] = doc_table["site"].apply(site_split_for)

    # ---- write per-doc split assignment
    doc_table[["doc_id", "cth", "site", "main_split", "site_split"]].to_parquet(
        OUT_DIR / "splits.parquet", index=False)

    # ---- splits.json (machine-readable summary + provenance)
    main_split_doc_counts = doc_table["main_split"].value_counts().to_dict()
    main_split_cth_counts = comp["main_split"].value_counts().to_dict()
    site_split_doc_counts = doc_table["site_split"].value_counts().to_dict()

    summary = {
        "seed": SEED,
        "corpus_version": CORPUS_VERSION,
        "git_commit": "N/A -- working directory is not a git repository",
        "split_fractions": {"train": TRAIN_FRAC, "dev": DEV_FRAC, "test": TEST_FRAC},
        "genre_band_definition": "CTH // 100 * 100 -- coarse numeric-range "
                                  "proxy only, not a scholarly genre catalog lookup",
        "main_split": {
            "unit": "CTH composition (all docs + all reconstructed join "
                    "members of a composition land on one side)",
            "doc_counts": main_split_doc_counts,
            "composition_counts": main_split_cth_counts,
            "composition_leakage_check": "PASS (0 compositions span multiple splits)",
        },
        "site_split": {
            "unit": "document (NOT composition-disjoint by design -- see "
                    "docstring)",
            "doc_counts": site_split_doc_counts,
            "provincial_sites_included": sorted(PROVINCIAL_SITES),
            "hattusa_sites_included": sorted(HATTUSA_SITES),
            "excluded_note": "'unknown'-site docs (museum/series sigla not "
                              "yet mapped, e.g. CHDS/DBH/FHL/VSNF/HFAC) are "
                              "excluded from this axis, not guessed into "
                              "either bucket -- likely mostly Hattusa "
                              "material under unmapped sigla, needs expert "
                              "prefix review before inclusion.",
        },
    }
    with open(OUT_DIR / "splits.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # ---- split_report.md
    lines_out = [
        "# P2 Deliverable 4 -- Splits Report", "",
        f"- Seed: {SEED} | Corpus version: {CORPUS_VERSION} | "
        f"Git commit: N/A (not a git repository)",
        f"- Compositions (CTH) split: {len(comp)}",
        f"- Documents split: {len(doc_table)}",
        "",
        "## Acceptance check #4 -- composition leakage",
        f"**{summary['main_split']['composition_leakage_check']}** "
        f"(programmatically asserted; {n_leaked} leaking compositions found)",
        "",
        "## main_split (train/dev/test, composition-disjoint)", "",
        "| split | documents | doc share | compositions |",
        "|---|---|---|---|",
    ]
    total_docs = len(doc_table)
    for s in ("train", "dev", "test"):
        d = main_split_doc_counts.get(s, 0)
        lines_out.append(
            f"| {s} | {d} | {100*d/total_docs:.1f}% | "
            f"{main_split_cth_counts.get(s, 0)} |")
    lines_out += [
        "",
        "**Caveat: document-count shares deviate from the nominal "
        "80/10/10 target** (stratification balances *composition* "
        "count per (size_band, genre_band) stratum, not document "
        "count) -- composition size is heavy-tailed (65 compositions "
        "have 51+ docs, some far more), so which large compositions "
        "land in dev vs test by chance swings doc-count share "
        "noticeably even with matched composition counts. This is a "
        "known, documented consequence of composition-level splitting "
        "being required for leakage safety, not a bug -- report doc "
        "counts per split alongside any dev/test metric rather than "
        "assuming parity.",
        "", "## site_split (Hattusa -> provincial generalization axis)", "",
                  "| bucket | documents |", "|---|---|"]
    for s in ("train_hattusa", "test_provincial", "excluded_unknown_site"):
        lines_out.append(f"| {s} | {site_split_doc_counts.get(s, 0)} |")
    lines_out += [
        "",
        f"**Caveat (per CLAUDE.md open question 3, restated):** "
        f"test_provincial = {site_split_doc_counts.get('test_provincial', 0)} "
        "documents total -- a small held-out set. Report this "
        "generalization experiment's results with wide uncertainty "
        "framing; do not oversell precision on a test set this size.",
        "",
        "## Composition size-band distribution (stratification input)", "",
        "| size_band | compositions |", "|---|---|",
    ]
    for band, cnt in comp["size_band"].value_counts().sort_index().items():
        lines_out.append(f"| {band} | {cnt} |")
    lines_out += ["", "## Genre-band distribution (CTH//100, coarse proxy only)", "",
                  "| genre_band | compositions | docs |", "|---|---|---|"]
    genre_doc_counts = doc_table.groupby(
        (doc_table["cth"] // 100 * 100))["doc_id"].count()
    for band, cnt in comp["genre_band"].value_counts().sort_index().items():
        lines_out.append(f"| {band} | {cnt} | {genre_doc_counts.get(band, 0)} |")
    lines_out += ["", "*Full per-document assignment in splits.parquet.*"]

    with open(OUT_DIR / "split_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print(f"Done. {len(comp)} compositions / {len(doc_table)} docs split. "
          f"Leakage check: {'PASS' if n_leaked == 0 else 'FAIL'}.")
    print(f"Reports in: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
