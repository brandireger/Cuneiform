#!/usr/bin/env python3
"""
10_resplit.py -- P2.5 Amendment A4: final split re-roll. LAST re-roll
-- after acceptance, splits.json is frozen (constitutional, no
further re-rolls per P2.5_AMENDMENTS.md).

Usage:
    python 10_resplit.py

Universe for composition-splitting = real compositions only
(is_bin=False in cth_bins.csv, all 31 previously-uncertain entries
resolved by user sign-off 2026-07-21 -- see 08_bins.py). Bin
documents get main_split='discovery', never train/dev/test.

Assignment: greedy doc-count balancing (a standard multiway-partition
heuristic -- process compositions largest-first, each goes to
whichever split currently has the lowest current_docs/target_fraction
ratio) targeting 80/10/10 BY DOCUMENTS while keeping composition-
disjointness absolute (05_splits.py's pure composition-count
stratified split produced a skewed 71/23/6 doc share despite balanced
composition counts, because composition size is heavy-tailed -- this
replaces that approach). (size_band, genre_band) strata are still
computed and reported for representation-across-splits transparency,
per spec, but the assignment itself is one global greedy pass (doc-
count is the thing that actually needs balancing; stratifying the
greedy pass itself would just reintroduce the same skew at smaller
scale within each stratum).

site_split is regenerated fresh here (after A5's provenance patch).
"""

import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

OUT_DIR = Path("p2_out")
P25_OUT = Path("p25_out")
SEED = 20260721  # NEW seed for the re-roll, distinct from P2's 20260720 -- logged
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


def get_git_commit():
    try:
        env_path = r"C:\Program Files\Git\bin\git.exe"
        result = subprocess.run([env_path, "rev-parse", "HEAD"],
                                 capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"N/A -- git rev-parse failed: {e}"


def greedy_balance(compositions):
    """compositions: list of (cth, n_docs). Returns dict cth -> split."""
    rng = random.Random(SEED)
    # shuffle first so ties among equal-size compositions aren't resolved
    # by CTH-number order (which would be a hidden non-random bias)
    order = list(compositions)
    rng.shuffle(order)
    order.sort(key=lambda x: -x[1])  # largest first, stable after shuffle

    totals = {"train": 0, "dev": 0, "test": 0}
    targets = {"train": TRAIN_FRAC, "dev": DEV_FRAC, "test": TEST_FRAC}
    assignment = {}
    for cth, n_docs in order:
        # pick the split with the lowest current/target ratio (most
        # "behind" its quota) -- classic greedy multiway balance
        split = min(totals, key=lambda s: totals[s] / targets[s])
        assignment[cth] = split
        totals[split] += n_docs
    return assignment, totals


def main() -> None:
    P25_OUT.mkdir(exist_ok=True)
    doc_table = pd.read_parquet(OUT_DIR / "doc_table.parquet")
    doc_table = doc_table[doc_table["cth"].notna()].copy()
    doc_table["cth"] = doc_table["cth"].astype(int)

    bins_df = pd.read_csv(P25_OUT / "cth_bins.csv")
    assert not bins_df["bin_uncertain"].any(), (
        "BLOCKING: bin_uncertain entries remain unresolved -- A4 cannot "
        "run until 08_bins.py's human sign-off resolution covers all "
        "entries (see P2.5_AMENDMENTS.md A4: 'bin_uncertain resolved by "
        "human review first -- blocking input').")
    is_bin_by_cth = dict(zip(bins_df["cth"], bins_df["is_bin"]))

    doc_table["is_bin"] = doc_table["cth"].map(is_bin_by_cth).fillna(False)

    real_docs = doc_table[~doc_table["is_bin"]]
    bin_docs = doc_table[doc_table["is_bin"]]

    comp = real_docs.groupby("cth").agg(n_docs=("doc_id", "count")).reset_index()
    comp["size_band"] = comp["n_docs"].apply(size_band)
    comp["genre_band"] = (comp["cth"] // 100 * 100).astype(int)

    compositions = list(zip(comp["cth"], comp["n_docs"]))
    assignment, totals = greedy_balance(compositions)
    comp["main_split"] = comp["cth"].map(assignment)

    doc_table["main_split"] = doc_table["cth"].map(assignment)
    doc_table.loc[doc_table["is_bin"], "main_split"] = "discovery"

    # ---- acceptance check: zero composition leakage among real comps
    leak_check = real_docs.assign(main_split=real_docs["cth"].map(assignment)) \
        .groupby("cth")["main_split"].nunique()
    n_leaked = int((leak_check > 1).sum())
    assert n_leaked == 0, f"COMPOSITION LEAKAGE DETECTED: {n_leaked} compositions."

    # ---- acceptance check: no bin doc carries train/dev/test
    bin_mislabeled = doc_table[doc_table["is_bin"] & (doc_table["main_split"] != "discovery")]
    assert len(bin_mislabeled) == 0, (
        f"{len(bin_mislabeled)} bin documents carry a train/dev/test label -- must be 'discovery'.")

    # ---- site_split, regenerated fresh post-A5
    def site_split_for(site):
        if site in HATTUSA_SITES:
            return "train_hattusa"
        if site in PROVINCIAL_SITES:
            return "test_provincial"
        return "excluded_unknown_site"

    doc_table["site_split"] = doc_table["site"].apply(site_split_for)

    doc_table[["doc_id", "cth", "site", "is_bin", "main_split", "site_split"]].to_parquet(
        OUT_DIR / "splits.parquet", index=False)

    doc_counts = doc_table["main_split"].value_counts().to_dict()
    total_docs = len(doc_table)
    comp_counts = comp["main_split"].value_counts().to_dict()
    site_counts = doc_table["site_split"].value_counts().to_dict()
    git_commit = get_git_commit()

    summary = {
        "seed": SEED,
        "corpus_version": CORPUS_VERSION,
        "git_commit": git_commit,
        "frozen": True,
        "frozen_date": "2026-07-21",
        "frozen_note": "P2.5_AMENDMENTS.md A4: LAST re-roll. splits.json "
                        "is now constitutional -- no further re-rolls.",
        "split_fractions": {"train": TRAIN_FRAC, "dev": DEV_FRAC, "test": TEST_FRAC},
        "bin_reframe": {
            "is_bin_docs": int(len(bin_docs)), "is_bin_compositions": int(bin_docs["cth"].nunique()),
            "bin_docs_get_split": "discovery",
            "cth_bins_source": "p25_out/cth_bins.csv, human sign-off recorded 2026-07-21",
        },
        "main_split": {
            "unit": "CTH composition, REAL (non-bin) compositions only",
            "assignment_method": "greedy doc-count balancing (largest-"
                                  "composition-first, min current/target "
                                  "ratio) -- targets 80/10/10 BY DOCUMENTS",
            "doc_counts": doc_counts,
            "composition_counts": comp_counts,
            "composition_leakage_check": "PASS (0 real compositions span multiple splits)",
            "bin_doc_check": "PASS (0 bin documents carry train/dev/test)",
        },
        "site_split": {
            "doc_counts": site_counts,
            "provincial_before_A5": 201, "provincial_after_A5": site_counts.get("test_provincial", 0),
        },
    }
    with open(OUT_DIR / "splits.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines_out = [
        "# P2.5 A4 -- Resplit Report (FROZEN)", "",
        f"- Seed: {SEED} (new for this re-roll, distinct from P2's "
        f"20260720) | Corpus version: {CORPUS_VERSION}",
        f"- Git commit: `{git_commit}`",
        "- **splits.json is now FROZEN -- this is the LAST re-roll per "
        "P2.5_AMENDMENTS.md.**",
        "",
        "## Acceptance check -- composition leakage & bin isolation",
        f"- Composition leakage: **PASS** (0 of {len(comp)} real "
        "compositions span multiple splits)",
        f"- Bin isolation: **PASS** (0 of {len(bin_docs)} bin documents "
        "carry a train/dev/test label; all get `main_split='discovery'`)",
        "",
        "## main_split (real compositions only, doc-count-balanced)", "",
        "| split | documents | doc share | compositions |",
        "|---|---|---|---|",
    ]
    for s in ("train", "dev", "test"):
        d = doc_counts.get(s, 0)
        lines_out.append(f"| {s} | {d} | {100*d/(total_docs - len(bin_docs)):.1f}% | "
                          f"{comp_counts.get(s, 0)} |")
    lines_out.append(f"| discovery (bins) | {doc_counts.get('discovery', 0)} | "
                      f"{100*doc_counts.get('discovery', 0)/total_docs:.1f}% of ALL docs | "
                      f"{int(bin_docs['cth'].nunique())} |")

    lines_out += [
        "",
        "**Compare to P2's original composition-count-only stratified "
        "split (05_splits.py): train 71.0% / dev 22.7% / test 6.3% by "
        "docs despite balanced composition counts. This greedy doc-"
        "count-aware re-roll targets the nominal 80/10/10 directly.**",
        "",
        "## site_split (regenerated post-A5 provenance patch)", "",
        "| bucket | documents |", "|---|---|",
    ]
    for s in ("train_hattusa", "test_provincial", "excluded_unknown_site"):
        lines_out.append(f"| {s} | {site_counts.get(s, 0)} |")
    lines_out.append(f"\n- Provincial count: 201 (P2) -> "
                      f"{site_counts.get('test_provincial', 0)} (post-A5 DAAM/Kp verification)")

    lines_out += ["", "## Size-band / genre-band representation across splits "
                  "(informational, not a hard constraint on the greedy pass)", "",
                  "| size_band | train | dev | test |", "|---|---|---|---|"]
    band_split = comp.groupby(["size_band", "main_split"])["cth"].count().unstack(fill_value=0)
    for band in band_split.index:
        row = band_split.loc[band]
        lines_out.append(f"| {band} | {row.get('train', 0)} | {row.get('dev', 0)} | {row.get('test', 0)} |")

    with open(OUT_DIR / "split_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print(f"Done. Leakage: PASS. Bin isolation: PASS. "
          f"Doc shares: train {100*doc_counts.get('train',0)/(total_docs-len(bin_docs)):.1f}% / "
          f"dev {100*doc_counts.get('dev',0)/(total_docs-len(bin_docs)):.1f}% / "
          f"test {100*doc_counts.get('test',0)/(total_docs-len(bin_docs)):.1f}%.")
    print(f"splits.json FROZEN. Git commit: {git_commit}")
    print(f"Reports in: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
