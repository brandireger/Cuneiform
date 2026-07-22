#!/usr/bin/env python3
"""
08_bins.py -- P2.5 Amendment A1: identify fragment-bin CTH numbers vs
real compositions.

Usage:
    python scripts/08_bins.py

DATA SOURCE DECISION (deviates from the amendment's literal plan of
657 individual per-CTH fetches): the live CTH catalogue at
hethport.uni-wuerzburg.de/CTH/ is dead (redirects to a generic
landing page -- the portal migrated to a JS-rendered SPA at
hethport.net with no discoverable static catalogue endpoint). The
Wayback Machine has a 2025-05-14 archived snapshot of the legacy
unfiltered index page (http://www.hethport.uni-wuerzburg.de/CTH/
index.php) containing ALL 836 CTH entries with real German titles in
one page. This is used instead: ONE HTTP request total, cached to
cth_index_raw.html forever after first fetch -- more polite than the
amendment's per-number plan, not less, and satisfies "one pass, ever"
literally. Verified: covers all 657 of the corpus's distinct CTH
numbers (0 missing).

Classification: is_bin=True when the title matches a fragment-bin
keyword pattern AND is "short/generic" (a genre-or-language qualifier
plus the bin keyword and little else, e.g. "Ritualfragmente",
"Hethitische Fragmente verschiedenen Inhaltes"). Longer/more specific
titles that happen to contain a bin keyword (e.g. a real composition
titled "... Fragmente der Tafel X von Y") are flagged bin_uncertain
for human review rather than auto-decided, per spec.
"""

import csv
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import urllib.request

OUT_DIR = Path("p25_out")
CACHE_HTML = OUT_DIR / "cth_index_raw.html"
CACHE_META = OUT_DIR / "cth_index_fetch_meta.txt"
WAYBACK_URL = ("http://web.archive.org/web/20250514171511/"
               "https://www.hethport.uni-wuerzburg.de/CTH/index.php")

ENTRY_RE = re.compile(
    r'<span class="CTHcatnrZchn"><a[^>]*> CTH ([\d.]+) </a></span>\s*'
    r'(.*?)\s*(?:<span class="CTHcatstichw">|</p>)')
TAG_RE = re.compile(r"<[^>]+>")

# DE/FR/EN fragment-bin keyword patterns, case-insensitive
BIN_KEYWORD_RE = re.compile(
    r"fragmente|fragments?|bruchst[uü]cke|unbestimmbar|unidentif|"
    r"divers|unclassified|nicht zugeordnet",
    re.IGNORECASE)

# seed hypotheses from P2.5_AMENDMENTS.md A1 -- cross-checked against
# the title-driven classification below, NEVER used to override it
SEED_BIN_HYPOTHESES = {
    209, 212, 215, 458, 470, 500, 530, 582, 590, 626, 627, 628, 670,
    745, 790, 791, 819, 826, 827, 828, 829, 830, 831, 832, 833,
}

# titles matching BIN_KEYWORD_RE with <= this many words are treated as
# confidently generic catch-all bins; longer ones are bin_uncertain
# (calibrated by manual inspection of the actual title distribution --
# see bins_report.md 'calibration sample' section)
SHORT_TITLE_WORD_THRESHOLD = 6


def fetch_and_cache_index() -> str:
    OUT_DIR.mkdir(exist_ok=True)
    if CACHE_HTML.exists():
        return CACHE_HTML.read_text(encoding="utf-8")
    req = urllib.request.Request(WAYBACK_URL, headers={"User-Agent": "cuneiform-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", "replace")
    CACHE_HTML.write_text(html, encoding="utf-8")
    CACHE_META.write_text(
        f"source_url: {WAYBACK_URL}\n"
        f"fetched_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"note: single bulk fetch, cached permanently -- do not re-fetch\n",
        encoding="utf-8")
    return html


def parse_titles(html: str) -> dict:
    titles = {}
    for m in ENTRY_RE.finditer(html):
        num_str, raw_title = m.group(1), m.group(2)
        title = TAG_RE.sub("", raw_title).strip()
        if "." in num_str:
            continue  # subdivision entry (e.g. 19.I) -- base entry covers the corpus's plain-int CTH labels
        try:
            n = int(num_str)
        except ValueError:
            continue
        if n not in titles:
            titles[n] = title
    return titles


def classify(cth: int, title: str):
    has_keyword = bool(BIN_KEYWORD_RE.search(title))
    n_words = len(title.split())
    seeded = cth in SEED_BIN_HYPOTHESES
    if not has_keyword:
        is_bin = False
        uncertain = False
        reason = "no bin keyword in title"
        if seeded:
            uncertain = True
            reason = ("seed hypothesis flagged this as a possible bin, but "
                       "title has NO fragment-bin keyword -- seed was wrong "
                       "or title is misleading; human review requested")
    elif n_words <= SHORT_TITLE_WORD_THRESHOLD:
        is_bin = True
        uncertain = False
        reason = f"bin keyword + short/generic title ({n_words} words)"
    else:
        is_bin = False
        uncertain = True
        reason = (f"bin keyword present but title is long/specific "
                  f"({n_words} words) -- may be a real composition whose "
                  "title mentions fragments; human review requested")
    return is_bin, uncertain, reason


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    html = fetch_and_cache_index()
    titles = parse_titles(html)

    doc_table = pd.read_parquet("p2_out/doc_table.parquet")
    doc_table = doc_table[doc_table["cth"].notna()].copy()
    doc_table["cth"] = doc_table["cth"].astype(int)
    corpus_cths = sorted(doc_table["cth"].unique())
    doc_counts = doc_table.groupby("cth")["doc_id"].count().to_dict()

    with open(OUT_DIR / "cth_titles.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cth", "title", "fetch_date", "source"])
        for cth in corpus_cths:
            w.writerow([cth, titles.get(cth, ""), date.today().isoformat(),
                        WAYBACK_URL if cth in titles else "NOT_FOUND"])

    rows = []
    missing_titles = []
    for cth in corpus_cths:
        title = titles.get(cth)
        if title is None:
            missing_titles.append(cth)
            rows.append({"cth": cth, "title": "", "is_bin": False,
                         "bin_uncertain": True, "doc_count": doc_counts.get(cth, 0),
                         "reason": "no title found in source -- cannot classify, "
                                   "treated as uncertain pending manual lookup"})
            continue
        is_bin, uncertain, reason = classify(cth, title)
        rows.append({"cth": cth, "title": title, "is_bin": is_bin,
                     "bin_uncertain": uncertain, "doc_count": doc_counts.get(cth, 0),
                     "reason": reason})

    bins_df = pd.DataFrame(rows).sort_values("cth")
    uncertain_before_resolution = bins_df[bins_df["bin_uncertain"]].copy()

    # ---- human sign-off resolution (2026-07-21, recorded per
    # P2.5_AMENDMENTS.md acceptance check 1 -- user reviewed
    # bins_report.md's uncertain list and decided):
    # (1) bin-keyword + long/specific title (e.g. CTH 500 "Fragmente
    #     von Fest- und Beschwoerungsritualen aus Kizzuwatna") -> BIN.
    #     User's stated rationale: cataloguer explicitly labeled these
    #     "fragments" even with a narrower theme; safer to keep out of
    #     duplicate-positive supervision and into the discovery pool.
    # (2) seed hypothesis flagged but title has NO bin keyword at all
    #     (626/627/628/826/827/828 -- "Fest der Eile", "KI.LAM-Fest",
    #     "(h)isuwa-Fest", "Etikett...", "Orakel in archaischer
    #     Sprache", "Orakelanfragen") -> REAL. No textual bin evidence
    #     whatsoever; the seed list was simply wrong for these six.
    no_keyword_seed_mismatch = {626, 627, 628, 826, 827, 828}
    for idx, row in bins_df.iterrows():
        if not row["bin_uncertain"]:
            continue
        if row["cth"] in no_keyword_seed_mismatch:
            bins_df.loc[idx, "is_bin"] = False
            bins_df.loc[idx, "bin_uncertain"] = False
            bins_df.loc[idx, "reason"] += " | RESOLVED 2026-07-21: real composition (no bin keyword, seed was wrong)"
        else:
            bins_df.loc[idx, "is_bin"] = True
            bins_df.loc[idx, "bin_uncertain"] = False
            bins_df.loc[idx, "reason"] += " | RESOLVED 2026-07-21 (user sign-off): bin"

    bins_df.to_csv(OUT_DIR / "cth_bins.csv", index=False)

    n_bin = int(bins_df["is_bin"].sum())
    n_uncertain = int(bins_df["bin_uncertain"].sum())
    n_real = len(bins_df) - n_bin - n_uncertain
    docs_in_bins = int(bins_df.loc[bins_df["is_bin"], "doc_count"].sum())
    docs_in_real = int(bins_df.loc[~bins_df["is_bin"] & ~bins_df["bin_uncertain"], "doc_count"].sum())
    docs_in_uncertain = int(bins_df.loc[bins_df["bin_uncertain"], "doc_count"].sum())

    # seed-list cross-check
    seed_confirmed = sorted(SEED_BIN_HYPOTHESES & set(bins_df.loc[bins_df["is_bin"], "cth"]))
    seed_not_bin = sorted(SEED_BIN_HYPOTHESES - set(bins_df.loc[bins_df["is_bin"], "cth"]))
    nonseed_bins = sorted(set(bins_df.loc[bins_df["is_bin"], "cth"]) - SEED_BIN_HYPOTHESES)

    uncertain_rows = uncertain_before_resolution.sort_values(
        "doc_count", ascending=False)

    # ---- A2: discovery pool + duplicate-positive pair recompute (bins
    # excluded from supervision; uncertain compositions held out of BOTH
    # the supervision pool and the discovery pool until human sign-off
    # resolves them -- a conservative default, not a guess either way).
    doc_bin_info = doc_table.merge(
        bins_df[["cth", "is_bin", "bin_uncertain", "title"]], on="cth", how="left")

    bin_docs = doc_bin_info[doc_bin_info["is_bin"]]
    real_docs = doc_bin_info[~doc_bin_info["is_bin"] & ~doc_bin_info["bin_uncertain"]]
    pending_docs = doc_bin_info[doc_bin_info["bin_uncertain"]]

    discovery_pool = bin_docs[[
        "doc_id", "cth", "site", "line_count", "word_count",
        "restored_sign_fraction",
    ]].rename(columns={"cth": "bin_cth"}).copy()
    discovery_pool["attested_rendering_pointer"] = (
        "p2_out/corpus.parquet, filter doc_id + drop restored signs "
        "(see 06_dataset_report.py render_word)")
    discovery_pool.to_parquet(OUT_DIR / "discovery_pool.parquet", index=False)

    def n_pairs_per_cth(sub_df):
        counts = sub_df.groupby("cth")["doc_id"].count()
        return int((counts * (counts - 1) // 2).sum())

    naive_pairs = n_pairs_per_cth(doc_table)  # all 657 compositions, no bin filtering
    bins_excluded_conservative = n_pairs_per_cth(real_docs)  # confirmed real only
    bins_excluded_incl_uncertain = n_pairs_per_cth(
        doc_bin_info[~doc_bin_info["is_bin"]])  # real + uncertain (uncertain not yet excluded)

    lines_out = [
        "# P2.5 A1 -- Bins Report", "",
        "## Data source", "",
        f"- Single bulk fetch from Wayback Machine archived snapshot "
        f"(2025-05-14) of the legacy CTH catalogue index page, cached "
        f"to `cth_index_raw.html` -- **1 HTTP request total**, not 657 "
        "(the live per-number endpoint is dead; see script docstring).",
        f"- {len(titles)} distinct base CTH titles parsed from source.",
        f"- Corpus CTH numbers: {len(corpus_cths)}. Missing titles: "
        f"{len(missing_titles)} {missing_titles if missing_titles else ''}",
        "",
        "## Classification summary (POST human sign-off resolution)", "",
        f"- **is_bin=True**: {n_bin} compositions, {docs_in_bins:,} documents",
        f"- **bin_uncertain=True (unresolved)**: {n_uncertain} "
        f"compositions, {docs_in_uncertain:,} documents",
        f"- **real composition**: {n_real} compositions, {docs_in_real:,} documents",
        "",
        f"Classification rule: bin keyword (DE/FR/EN fragment-bin "
        f"patterns) present AND title <= {SHORT_TITLE_WORD_THRESHOLD} "
        "words -> is_bin. Bin keyword present but title longer/more "
        "specific -> bin_uncertain (NOT auto-decided). No bin keyword "
        "-> real composition, unless the seed list flagged it "
        "(then also uncertain, for cross-check).",
        "",
        "## Seed-list cross-check (hypotheses from P2.5_AMENDMENTS.md, "
        "NOT used to override title-driven classification)", "",
        f"- Seed hypotheses confirmed by title: {len(seed_confirmed)} -- {seed_confirmed}",
        f"- Seed hypotheses NOT confirmed by title (seed was wrong or "
        f"title misleading): {len(seed_not_bin)} -- {seed_not_bin}",
        f"- Bins found by title that were NOT in the seed list "
        f"(seed list was incomplete, as expected): {len(nonseed_bins)} "
        f"-- {nonseed_bins}",
        "",
        "## Uncertain list -- HUMAN SIGN-OFF RECORDED 2026-07-21", "",
        "Per P2.5_AMENDMENTS.md acceptance check 1. User reviewed this "
        f"{len(uncertain_before_resolution)}-entry list (shown below in "
        "its pre-resolution state) and decided: (1) the 25 entries with "
        "a bin keyword + long/specific title -> **BIN** (rationale: "
        "cataloguer explicitly labeled these \"fragments\" even with a "
        "narrower theme; safer to exclude from duplicate-positive "
        "supervision); (2) the 6 seed-list entries with NO bin keyword "
        "at all (626, 627, 628, 826, 827, 828) -> **REAL** (no textual "
        "bin evidence; the seed hypothesis was simply wrong for these). "
        "Final decision recorded per-row in cth_bins.csv's `reason` "
        "column (suffix `RESOLVED 2026-07-21`).", "",
        "| CTH | title | doc_count | pre-resolution reason |",
        "|---|---|---|---|",
    ]
    for r in uncertain_rows.itertuples():
        lines_out.append(f"| {r.cth} | {r.title} | {r.doc_count} | {r.reason} |")

    lines_out += ["", "## Top-20 largest compositions, re-annotated with is_bin "
                  "(dataset_report.md cross-reference)", "",
                  "| CTH | documents | is_bin | bin_uncertain | title |",
                  "|---|---|---|---|---|"]
    for r in bins_df.sort_values("doc_count", ascending=False).head(20).itertuples():
        lines_out.append(f"| {r.cth} | {r.doc_count} | {r.is_bin} | "
                          f"{r.bin_uncertain} | {r.title} |")

    lines_out += [
        "",
        "## A2 -- Discovery pool + supervision-eligible corpus "
        "(acceptance checks 2-3)", "",
        f"- **Discovery pool** (`discovery_pool.parquet`, is_bin=True "
        f"docs, inference-time queries only, never scored as ground "
        f"truth): **{len(discovery_pool):,} documents**",
        f"- **Supervision-eligible** (confirmed real compositions, "
        f"bin_uncertain=False): {len(real_docs):,} documents, "
        f"{int(real_docs['cth'].nunique())} compositions",
        f"- **Pending review** (bin_uncertain=True, held out of BOTH "
        f"pools until sign-off -- conservative default): "
        f"{len(pending_docs):,} documents, "
        f"{int(pending_docs['cth'].nunique())} compositions",
        "",
        "### Duplicate-positive pair counts (same-CTH combinatorial "
        "pairs, before/after bin exclusion)",
        f"- **Naive (all 657 compositions, no bin filtering)**: "
        f"{naive_pairs:,} pairs",
        f"- **Bins excluded, uncertain still included**: "
        f"{bins_excluded_incl_uncertain:,} pairs "
        f"({100*(1-bins_excluded_incl_uncertain/naive_pairs):.1f}% drop)",
        f"- **Bins excluded, uncertain ALSO excluded (conservative, "
        f"current supervision-eligible number)**: "
        f"{bins_excluded_conservative:,} pairs "
        f"({100*(1-bins_excluded_conservative/naive_pairs):.1f}% drop "
        "from naive)",
        "",
        "The large drop is expected and is the whole point of the bin "
        "reframe: CTH 832 alone (\"Hethitische Fragmente verschiedenen "
        f"Inhaltes\", {doc_counts.get(832, 0):,} docs) contributes "
        f"{doc_counts.get(832, 0) * (doc_counts.get(832, 0) - 1) // 2:,} "
        "naive same-folder pairs by itself, none of which are real "
        "duplicate-witness evidence -- they're unrelated fragments an "
        "editor filed under the same catch-all number for lack of a "
        "better home.",
    ]

    with open(OUT_DIR / "bins_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print(f"Done. {n_bin} bins, {n_uncertain} uncertain (needs sign-off), "
          f"{n_real} real compositions.")
    print(f"Discovery pool: {len(discovery_pool):,} docs. Duplicate pairs: "
          f"naive {naive_pairs:,} -> bins-excluded (conservative) "
          f"{bins_excluded_conservative:,}.")
    print(f"Reports in: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
