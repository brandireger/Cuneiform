#!/usr/bin/env python3
"""
07_metadata_patch.py -- P2.5 Amendment A5: metadata patches applied to
02_parse.py's outputs in place, plus provenance verification.

Usage:
    python 07_metadata_patch.py TLHdig_0.2.0-beta.zip

A5.1/A5.2: re-derives side/column/on_physical_edge from the existing
`line_label` text (already captured in corpus.parquet -- no need to
re-read the XML) using a fuller pattern set than 02_parse.py's
original parser had, then patches corpus.parquet in place and
re-generates edges.parquet (by re-running 04_edges.py's logic against
the patched corpus, extended to use on_physical_edge as a strong
signal that a fragment is NOT broken at that boundary).

A5.3: verifies the DAAM/Kp provenance hypothesis from
P2.5_AMENDMENTS.md BEFORE applying it, per instruction. Finding
(WebSearch, see provenance_patch.md for citations): DAAM =
"Documenta Antiqua Asiae Minoris", a MULTI-SITE series -- the
amendment's single-site hypothesis (DAAM -> Kayalipinar/Samuha) was
only half right. DAAM volume 1 = Kayalipinar/Samuha (Rieken 2019);
DAAM volume 2 = Ortakoy/Sapinuwa (Schwemer & Suel 2021); DAAM volumes
3-4 = Hattusa/Bogazkoy museum tablets (Bozgun 2025, Cilingir Cesur
2025). Site is applied PER VOLUME NUMBER, not as a blanket prefix
mapping. Kp confirmed as a Kayalipinar variant of the already-known
KpT prefix (high confidence, direct extension of an established
mapping). Both applied. Remaining unknown prefixes get a proposals
CSV at the amendment's specified 0.6-0.7 confidence, left UNAPPLIED.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

P2_OUT = Path("p2_out")
P25_OUT = Path("p25_out")

ROMAN_RE = re.compile(r"\b([IVX]{1,4})[?!]?\b")
ROMAN_LOWER_RE = re.compile(r"\b(i{1,3}|iv|v|vi)[?!]?\b")

# ---- A5.3 provenance patch: verified via WebSearch, see docstring/report
DAAM_VOLUME_SITE = {
    1: "Kayalipinar/Samuha",
    2: "Ortakoy/Sapinuwa",
    3: "Hattusa",
    4: "Hattusa",
}
DAAM_RE = re.compile(r"^DAAM\s+(\d+)\.")
KP_RE = re.compile(r"^Kp\b")

# proposals only -- NOT applied to site/site_split, per spec
PREFIX_PROPOSALS = [
    ("CHDS", "Hattusa", 0.7, "Chicago Hittite Dictionary Supplements -- "
     "confirmed via WebSearch to publish 'Unpublished Bo-Fragments' "
     "(Bo = Boghazkoy prefix), i.e. Hattusa-origin fragments held/"
     "catalogued by the U. Chicago CHD project, not an excavation-"
     "findspot siglum itself."),
    ("DBH", "Hattusa", 0.65, "Dresdner Beitraege zur Hethitologie -- "
     "German publication series historically focused on Boghazkoy "
     "material; not independently re-verified per-volume here."),
    ("FHL", "Hattusa", 0.5, "No definitive series identification found "
     "via WebSearch; appears in bibliographies alongside other "
     "Boghazkoy-fragment sigla but evidence is weak -- lower "
     "confidence than the others in this list."),
    ("VSNF", "Hattusa", 0.65, "Vorderasiatische Schriftdenkmaeler Neue "
     "Folge -- Berlin museum (Vorderasiatisches Museum) publication "
     "series; VAT-collection-adjacent, predominantly Boghazkoy-origin "
     "holdings historically."),
    ("HFAC", "Hattusa", 0.7, "Hittite Fragments in American Collections "
     "(Beckman) -- published private/museum US holdings, predominantly "
     "Boghazkoy-origin material that entered the antiquities market/"
     "collections."),
    ("Privat", "Hattusa", 0.55, "Generic 'private collection' label -- "
     "plausibly Boghazkoy-origin by base rate (most dispersed Hittite "
     "tablets in private hands trace to early Boghazkoy excavations/"
     "antiquities market) but no specific verification performed."),
    ("VAT", "Hattusa", 0.65, "Vorderasiatische Tontafeln -- Berlin "
     "Vorderasiatisches Museum inventory prefix; largely Boghazkoy-"
     "origin historical holdings."),
    ("HHCTO", "unknown", 0.3, "No identification found; insufficient "
     "evidence for a confidence-bearing proposal."),
    ("Gurney", "Hattusa", 0.55, "O.R. Gurney published-collection "
     "siglum (British); plausibly Boghazkoy-origin by base rate, not "
     "independently verified."),
    ("Dispersa", "Hattusa", 0.5, "Likely a 'dispersed tablets' catalog "
     "label; plausibly Boghazkoy-origin by base rate, not verified."),
    ("FHG", "unknown", 0.3, "No identification found; insufficient "
     "evidence."),
    ("HHT", "unknown", 0.3, "No identification found; insufficient "
     "evidence."),
    ("Durham", "Hattusa", 0.5, "UK museum/university collection siglum; "
     "plausibly Boghazkoy-origin by base rate, not verified."),
    ("AMUM", "Hattusa", 0.55, "Possibly Anadolu Medeniyetleri Muezesi "
     "(Museum of Anatolian Civilisations, Ankara) -- this museum holds "
     "substantial Boghazkoy excavation material (cf. DAAM 3/4 Bo-range "
     "tablets), but the prefix expansion itself is not confirmed."),
    ("München", "Hattusa", 0.6, "Munich museum collection siglum; "
     "plausibly Boghazkoy-origin historical holdings, not verified."),
    ("AAA3", "unknown", 0.3, "No identification found; insufficient "
     "evidence."),
    ("UK", "unknown", 0.3, "Ambiguous short prefix; no confident "
     "identification found."),
]


def parse_side_column_edge(label):
    if not label:
        return None, None, None, False
    s = str(label).strip()
    uncertain = "?" in s or "!" in s

    on_physical_edge = None
    if re.search(r"\bu\.\s*Rd\.?", s):
        on_physical_edge = "lower"
    elif re.search(r"\bo\.\s*Rd\.?", s):
        on_physical_edge = "upper"
    elif re.search(r"\blk\.\s*Rd\.?", s):
        on_physical_edge = "left"
    elif re.search(r"\b(r|re)\.\s*Rd\.?", s):
        on_physical_edge = "right"

    side = None
    if re.search(r"\bSeite\s*A\b", s):
        side = "side_A"
    elif re.search(r"\bSeite\s*B\b", s):
        side = "side_B"
    elif re.search(r"\bVs\.?", s) or re.search(r"\bobv\.?", s, re.IGNORECASE):
        side = "obverse"
    elif re.search(r"\bRs\.?", s) or re.search(r"\brev\.?", s, re.IGNORECASE):
        side = "reverse"

    column = None
    if re.search(r"\b(lk|li|l)\.\s*(Kol|col)\.?", s, re.IGNORECASE):
        column = "left"
    elif re.search(r"\b(r|re)\.\s*(Kol|col)\.?", s, re.IGNORECASE):
        column = "right"
    else:
        rm = ROMAN_RE.search(s)
        if rm:
            column = rm.group(1)
        else:
            pm = re.search(r"\((I|II|III|IV|V|VI)\)", s)
            if pm:
                column = pm.group(1)
            else:
                lm = ROMAN_LOWER_RE.search(s)
                if lm:
                    column = lm.group(1).upper()

    return side, column, on_physical_edge, uncertain


def patch_corpus_side_column():
    corpus = pd.read_parquet(P2_OUT / "corpus.parquet")
    # idempotency: a prior run of this script may have already added
    # these columns -- drop them first so the merge below doesn't
    # collide and produce _x/_y suffixed duplicates.
    corpus = corpus.drop(columns=[
        "on_physical_edge", "reading_uncertain",
        "on_physical_edge_x", "on_physical_edge_y",
        "reading_uncertain_x", "reading_uncertain_y",
    ], errors="ignore")
    # 02_parse.py's original SIDE_MAP fell back to the literal string
    # "other" (not null/NaN) for any side_raw it didn't recognize --
    # that counts as unmapped too, not "already resolved".
    unmapped_mask_before = corpus["side"].isna() | (corpus["side"] == "other")
    before_unmapped = int(unmapped_mask_before.sum())

    unique_lines = corpus[["doc_id", "line_index_in_doc", "line_label"]].drop_duplicates()
    parsed = unique_lines["line_label"].apply(
        lambda lbl: pd.Series(parse_side_column_edge(lbl),
                               index=["side2", "column2", "on_physical_edge", "reading_uncertain"]))
    unique_lines = pd.concat([unique_lines, parsed], axis=1)

    corpus = corpus.merge(
        unique_lines[["doc_id", "line_index_in_doc", "side2", "column2",
                       "on_physical_edge", "reading_uncertain"]],
        on=["doc_id", "line_index_in_doc"], how="left")

    unmapped_mask = corpus["side"].isna() | (corpus["side"] == "other")
    corpus["side"] = corpus["side"].where(~unmapped_mask, corpus["side2"])
    unmapped_col_mask = corpus["column"].isna()
    corpus["column"] = corpus["column"].where(~unmapped_col_mask, corpus["column2"])
    corpus = corpus.drop(columns=["side2", "column2"])

    after_unmapped = int((corpus["side"].isna() | (corpus["side"] == "other")).sum())
    corpus.to_parquet(P2_OUT / "corpus.parquet", index=False)

    n_edge_lines = int(corpus["on_physical_edge"].notna().sum())
    return before_unmapped, after_unmapped, n_edge_lines, len(corpus)


def patch_provenance():
    doc_table = pd.read_parquet(P2_OUT / "doc_table.parquet")
    before_provincial = int(doc_table["site"].isin(
        {"Masat/Tapikka", "Ortakoy/Sapinuwa", "Kusakli/Sarissa",
         "Kayalipinar/Samuha", "Ugarit", "Emar", "Alalakh"}).sum())

    def repatch(row):
        doc_id = row["doc_id"]
        if row["site"] != "unknown":
            return row["site"]
        m = DAAM_RE.match(doc_id)
        if m:
            vol = int(m.group(1))
            return DAAM_VOLUME_SITE.get(vol, row["site"])
        if KP_RE.match(doc_id):
            return "Kayalipinar/Samuha"
        return row["site"]

    doc_table["site"] = doc_table.apply(repatch, axis=1)
    doc_table.to_parquet(P2_OUT / "doc_table.parquet", index=False)

    after_provincial = int(doc_table["site"].isin(
        {"Masat/Tapikka", "Ortakoy/Sapinuwa", "Kusakli/Sarissa",
         "Kayalipinar/Samuha", "Ugarit", "Emar", "Alalakh"}).sum())
    n_daam = int(doc_table["doc_id"].str.match(r"^DAAM\s+\d+\.").sum())
    n_kp = int(doc_table["doc_id"].str.match(r"^Kp\b").sum())
    return before_provincial, after_provincial, n_daam, n_kp


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python 07_metadata_patch.py /path/to/TLHdig_0.2.0-beta.zip")
    zip_path = sys.argv[1]
    P25_OUT.mkdir(exist_ok=True)

    before_unmapped, after_unmapped, n_edge_lines, n_rows = patch_corpus_side_column()
    before_prov, after_prov, n_daam, n_kp = patch_provenance()

    with open(P25_OUT / "prefix_mapping_proposals.csv", "w", newline="", encoding="utf-8") as f:
        import csv
        w = csv.writer(f)
        w.writerow(["prefix", "proposed_site", "confidence", "evidence", "applied"])
        for pfx, site, conf, evidence in PREFIX_PROPOSALS:
            w.writerow([pfx, site, conf, evidence, "FALSE -- unapplied, expert review required"])

    lines_out = [
        "# P2.5 A5 -- Metadata Patch Report", "",
        "## A5.1/A5.2 -- side/column/physical-edge remap "
        "(corpus.parquet patched in place)", "",
        f"- Word-token rows: {n_rows:,}",
        f"- `side` unmapped before patch: {before_unmapped:,} rows "
        f"-> after: {after_unmapped:,} rows "
        f"({100*(before_unmapped-after_unmapped)/before_unmapped:.1f}% recovered)"
        if before_unmapped else "- side already fully mapped",
        f"- New `on_physical_edge` field: {n_edge_lines:,} word-token "
        "rows sit on a line marked as a physical tablet edge "
        "(u./o./lk./r. Rd.) -- these lines are direct evidence the "
        "fragment is NOT broken at that boundary, strengthening the "
        "top/bottom-edge-lost heuristic in edges.parquet.",
        "", "## A5.3 -- Provenance patch (DAAM/Kp)", "",
        "**Amendment hypothesis was only half right.** WebSearch "
        "verification found DAAM (\"Documenta Antiqua Asiae Minoris\") "
        "is a MULTI-SITE series, not single-site:",
        "- DAAM 1 = *Keilschrifttafeln aus Kayalipinar 1* (Rieken 2019) "
        "-> Kayalipinar/Samuha",
        "- DAAM 2 = *The Akkadian and Sumerian Texts from Ortakoy-"
        "Sapinuwa* (Schwemer & Suel 2021) -> Ortakoy/Sapinuwa "
        "(contradicts the amendment's blanket Kayalipinar hypothesis)",
        "- DAAM 3 = *Bogazkoy Tablets in the Museum of Anatolian "
        "Civilisations* (Bozgun 2025) -> Hattusa",
        "- DAAM 4 = *Bogazkoy Tablets ... (Bo 9032-9097)* (Cilingir "
        "Cesur 2025) -> Hattusa",
        "- Applied PER VOLUME NUMBER (parsed from `DAAM N.M` docIDs), "
        "not as a blanket prefix mapping.",
        "- `Kp` confirmed as a Kayalipinar/Samuha variant siglum "
        "(direct extension of the already-known `KpT` prefix already "
        "in SITE_PREFIXES) -- high confidence, applied.",
        f"- DAAM docs repatched: {n_daam}. Kp docs repatched: {n_kp}.",
        f"- **Provincial-site document count: {before_prov} -> "
        f"{after_prov}** (target range from the amendment: ~201 -> "
        f"~365; actual result below/above that estimate should be "
        "read against the fact that not all DAAM volumes are "
        "provincial -- vols 3-4 add to Hattusa, not provincial).",
        "",
        "## Remaining unknown prefixes -- proposals, UNAPPLIED", "",
        "Per spec: proposed at ~0.6-0.7 confidence (some lower where "
        "evidence was weak), NOT applied to site/site_split. Expert "
        "review or Konkordanz verification required before use. Full "
        "table in `prefix_mapping_proposals.csv`.", "",
        "| prefix | proposed site | confidence | evidence |",
        "|---|---|---|---|",
    ]
    for pfx, site, conf, evidence in PREFIX_PROPOSALS:
        lines_out.append(f"| {pfx} | {site} | {conf} | {evidence} |")

    with open(P25_OUT / "provenance_patch.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print(f"Corpus patched: side unmapped {before_unmapped}->{after_unmapped}, "
          f"{n_edge_lines} physical-edge lines.")
    print(f"Provenance patched: provincial docs {before_prov}->{after_prov}.")

    print("Re-running 04_edges.py against the patched corpus...")
    result = subprocess.run(
        [sys.executable, "04_edges.py", zip_path],
        capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    print(f"Reports in: {P25_OUT.resolve()}")


if __name__ == "__main__":
    main()
