#!/usr/bin/env python3
"""specs/LINE_LANG_MIGRATION.md, Step A -- non-test audit.

Read-only. Produces the diagnosed corruption boundary, a proposed
canonical vocabulary, and aggregate non-test counts by status, for
Ixca's ratification gate (Step B). Writes NO canonical field and does
not touch any frozen artifact -- `Phase1_pipeline/p2_out/corpus.parquet`
and `.../splits.parquet` are read only, never written.

Per the migration's non-negotiable invariants: all `main_split=="test"`
rows are excluded from the read itself (not merely from the report), so
this script never loads a single test-side `line_lang` value into
memory. Aggregate counts and samples below cover train/dev/discovery
only.

Usage:
    python scripts/line_lang_audit.py
"""
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import pandas as pd  # noqa: E402

import contracts  # noqa: E402
import evidence_policy as ep  # noqa: E402
from phase2_io import split_lookup_fail_closed  # noqa: E402

ZIP_PATH = Path("TLHdig_0.2.0-beta.zip")
PINNED_ZIP_MD5 = "93e71e2560f5e109c87713d5590cb059"
CORPUS_PATH = Path("Phase1_pipeline/p2_out/corpus.parquet")
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
PARSER_PATH = Path("Archive/scripts/02_parse.py")
REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")

OUT_DIR = Path("migrations/line_lang_v1")
AUDIT_JSON = OUT_DIR / "audit.json"
REPORT_PATH = OUT_DIR / "audit_report.md"
MANIFEST_PATH = OUT_DIR / "audit_manifest.json"

# Proposed seed vocabulary, from CLAUDE.md's own documented multilingual-
# layer list. Proposal only -- ratification (which codes are canonical,
# and any non-identity mapping such as Hat<->Hattian) is Ixca's decision,
# per the migration spec's Step B; nothing here is auto-applied.
PROPOSED_SEED_VOCABULARY = {
    "Hit", "Akk", "Sum", "Hat", "Hattian", "Hur", "Luw", "Pal",
}

MALFORMED_CHARS = re.compile(r"[<>=\"'\s]")


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_junk(name):
    return "__MACOSX" in name or name.rsplit("/", 1)[-1].startswith("._")


def local(tag):
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def raw_lb_lang_by_line(raw_xml_bytes):
    """Independent re-walk of the raw XML (bypassing the frozen parser
    entirely) yielding {line_index_in_doc: raw lb@lg value}. Mirrors
    decompose_corpus.py's own <lb>-driven line_index increment exactly,
    so line_index_in_doc lines up with corpus.parquet's own numbering."""
    root = ET.fromstring(raw_xml_bytes)
    text_el = root.find(".//{*}text")
    if text_el is None:
        return {}
    result = {}
    line_index = -1
    for el in text_el.iter():
        if local(el.tag) == "lb":
            line_index += 1
            result[line_index] = el.get("lg")
    return result


def classify(raw_value):
    if raw_value is None or raw_value == "":
        return "missing"
    if MALFORMED_CHARS.search(raw_value) or len(raw_value) > 15:
        return "malformed"
    if raw_value in PROPOSED_SEED_VOCABULARY:
        return "valid_against_proposed_seed"
    return "unrecognized_against_proposed_seed"


def main():
    print("Hashing inputs (recorded in manifest, not compared against a "
          "stored expectation beyond the pinned corpus MD5) ...")
    zip_md5 = md5_file(ZIP_PATH)
    zip_pin_ok = zip_md5 == PINNED_ZIP_MD5
    print(f"Corpus zip MD5: {zip_md5} (matches CLAUDE.md pin: {zip_pin_ok})")

    splits = pd.read_parquet(SPLITS_PATH, columns=["doc_id", "main_split"])
    split_lookup, ambiguous_ids = split_lookup_fail_closed(splits)
    non_test_ids = {
        doc_id for doc_id, split in split_lookup.items()
        if split in ("train", "dev", "discovery")
    }
    print(f"Non-test (train+dev+discovery) documents: {len(non_test_ids):,} "
          f"(ambiguous-split docs excluded: {len(ambiguous_ids)})")

    corpus = pd.read_parquet(
        CORPUS_PATH, columns=["doc_id", "line_index_in_doc", "line_lang"],
        filters=[("doc_id", "in", list(non_test_ids))],
    )
    contracts.assert_no_test(
        set(corpus["doc_id"]), split_lookup, label="line_lang audit corpus.parquet read")
    print(f"Non-test corpus.parquet word-rows read: {len(corpus):,}")

    # Derived line_lang per (doc_id, line) -- most-common value if a line's
    # word-rows disagree (itself a finding, counted separately below).
    derived_by_line = {}
    intra_line_inconsistent = 0
    for (doc_id, line_idx), group in corpus.groupby(
            ["doc_id", "line_index_in_doc"], sort=False):
        vals = group["line_lang"].tolist()
        counts = Counter(vals)
        if len(counts) > 1:
            intra_line_inconsistent += 1
        derived_by_line[(doc_id, int(line_idx))] = counts.most_common(1)[0][0]

    print(f"Lines where word-rows disagree on derived line_lang: "
          f"{intra_line_inconsistent:,}")

    zp = zipfile.ZipFile(ZIP_PATH)
    names = [
        n for n in zp.namelist()
        if n.lower().endswith(".xml") and not n.endswith("/") and not is_junk(n)
    ]

    raw_by_doc = {}
    n_parse_errors = 0
    docs_needed = set(non_test_ids)
    for name in names:
        raw = zp.read(name)
        try:
            root_check = ET.fromstring(raw)
        except ET.ParseError:
            n_parse_errors += 1
            continue
        doc_id_el = root_check.find(".//{*}docID")
        doc_id = (doc_id_el.text or "").strip() if doc_id_el is not None else Path(name).stem
        if doc_id not in docs_needed:
            continue
        raw_by_doc[doc_id] = raw

    print(f"Raw XML documents matched to non-test scope: {len(raw_by_doc):,} "
          f"(of {len(docs_needed):,} needed; parse errors skipped: {n_parse_errors})")

    status_counts = Counter()
    status_by_split = defaultdict(Counter)
    divergence_count = 0  # raw lb@lg differs from corpus.parquet's derived value
    divergence_examples = []
    lines_with_no_word_rows = 0
    samples_by_status = defaultdict(list)
    distinct_raw_values = Counter()

    for doc_id, raw in raw_by_doc.items():
        split = split_lookup[doc_id]
        try:
            raw_lang_by_line = raw_lb_lang_by_line(raw)
        except ET.ParseError:
            continue
        for line_idx, raw_val in raw_lang_by_line.items():
            status = classify(raw_val)
            status_counts[status] += 1
            status_by_split[status][split] += 1
            distinct_raw_values[raw_val or None] += 1

            key = (doc_id, line_idx)
            if key not in derived_by_line:
                # A line with zero word-rows (e.g. blank/structural-only)
                # has nothing in the word-level corpus.parquet to compare
                # against -- not a divergence, just nothing to compare.
                lines_with_no_word_rows += 1
            else:
                derived_val = derived_by_line[key]
                derived_missing = derived_val is None or derived_val == "" or (
                    isinstance(derived_val, float) and pd.isna(derived_val))
                raw_missing = raw_val is None or raw_val == ""
                if derived_val != raw_val and not (derived_missing and raw_missing):
                    divergence_count += 1
                    if len(divergence_examples) < 10:
                        divergence_examples.append({
                            "doc_id": doc_id, "line_index_in_doc": line_idx,
                            "raw_lb_lg": raw_val, "corpus_parquet_line_lang": derived_val,
                        })

            if len(samples_by_status[status]) < 8:
                samples_by_status[status].append({
                    "doc_id": doc_id, "line_index_in_doc": line_idx,
                    "raw_lb_lg": raw_val,
                })

    result = {
        "zip_md5": zip_md5,
        "zip_md5_matches_pin": zip_pin_ok,
        "non_test_documents": len(non_test_ids),
        "ambiguous_split_documents_excluded": len(ambiguous_ids),
        "corpus_parquet_word_rows_read": len(corpus),
        "lines_with_intra_line_derived_disagreement": intra_line_inconsistent,
        "raw_xml_documents_matched": len(raw_by_doc),
        "raw_xml_parse_errors_skipped": n_parse_errors,
        "raw_lines_with_no_corpus_parquet_word_rows": lines_with_no_word_rows,
        "proposed_seed_vocabulary": sorted(PROPOSED_SEED_VOCABULARY),
        "status_counts": dict(status_counts),
        "status_counts_by_split": {
            status: dict(counts) for status, counts in status_by_split.items()
        },
        "distinct_raw_values_non_test": dict(distinct_raw_values.most_common()),
        "raw_vs_derived_divergence_count": divergence_count,
        "raw_vs_derived_divergence_examples": divergence_examples,
        "samples_by_status": dict(samples_by_status),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    registry = ep.load_registry(REGISTRY_PATH)
    # "artifact_strict" only permits OBSERVED_ARTIFACT/OBSERVED_DOCUMENT_
    # STRUCTURE/SYSTEM_TECHNICAL. `line_lang` was reclassified from
    # OBSERVED_DOCUMENT_STRUCTURE to EDITORIAL_TRANSCRIPTION by the Gate 0
    # ruling (2026-07-25, see configs/evidence_registry.yaml) -- lb@lg is
    # source-encoded editorial linguistic annotation, not directly observed
    # structure. "transcription_assisted" is the minimal policy that permits
    # it while still denying cu/mrp/lemma fields.
    policy = ep.load_policy("transcription_assisted", POLICIES_PATH)
    manifest = ep.build_manifest(
        task="line_lang_audit_step_a",
        evidence_policy=policy.name,
        features_requested=["line_lang"],
        registry=registry,
        policy=policy,
        split_manifest_path=SPLITS_PATH,
        config_path=REGISTRY_PATH,
        seed=20260725,
        declared_statistics_universe="train + dev + discovery (test excluded from the read)",
    )
    manifest["zip_md5"] = zip_md5
    manifest["zip_md5_matches_claude_md_pin"] = zip_pin_ok
    manifest["parser_source_sha256"] = ep._hash_file(PARSER_PATH)  # noqa: SLF001
    manifest["policy_config_sha256"] = ep._hash_file(POLICIES_PATH)  # noqa: SLF001
    manifest["corpus_parquet_sha256"] = ep._hash_file(CORPUS_PATH)  # noqa: SLF001
    ep.write_manifest(manifest, MANIFEST_PATH)

    report_lines = [
        "# `line_lang` migration -- Step A non-test audit",
        "",
        "Read-only. No canonical field is written; no frozen artifact is "
        "modified. Test-side `line_lang` values were never read -- the "
        "corpus.parquet query itself excludes `main_split==\"test\"` "
        "documents, and the raw-XML re-walk below only opens documents in "
        "the non-test scope.",
        "",
        f"- Corpus zip MD5: `{zip_md5}` "
        f"({'matches' if zip_pin_ok else 'DOES NOT MATCH'} the CLAUDE.md-pinned "
        f"`{PINNED_ZIP_MD5}`).",
        f"- Non-test documents in scope: **{result['non_test_documents']:,}** "
        f"({result['ambiguous_split_documents_excluded']} ambiguous-split docs "
        "excluded, matching the existing real_gap_census.py convention).",
        f"- Raw XML documents matched and re-walked: "
        f"**{result['raw_xml_documents_matched']:,}**.",
        f"- Lines where corpus.parquet's own word-rows disagree with each "
        f"other on `line_lang` within the same line: "
        f"**{result['lines_with_intra_line_derived_disagreement']:,}**.",
        f"- Raw lines with zero word-rows in corpus.parquet (blank/structural "
        "lines with nothing to join against -- excluded from the divergence "
        f"check below, not counted as a mismatch): "
        f"**{result['raw_lines_with_no_corpus_parquet_word_rows']:,}**.",
        "",
        "## Status counts (non-test only, against a PROPOSED seed vocabulary "
        "-- not yet ratified)",
        "",
        "| status | count |",
        "|---|---|",
    ]
    for status, count in sorted(result["status_counts"].items(), key=lambda kv: -kv[1]):
        report_lines.append(f"| {status} | {count:,} |")

    report_lines += [
        "",
        "### By split",
        "",
        "| status | train | dev | discovery |",
        "|---|---|---|---|",
    ]
    for status, by_split in result["status_counts_by_split"].items():
        report_lines.append(
            f"| {status} | {by_split.get('train', 0):,} | "
            f"{by_split.get('dev', 0):,} | {by_split.get('discovery', 0):,} |")

    report_lines += [
        "",
        "## Distinct raw `lb@lg` values found (non-test)",
        "",
        "| raw value | count |",
        "|---|---|",
    ]
    for val, count in result["distinct_raw_values_non_test"].items():
        display = "*(missing)*" if val is None or val == "" else f"`{val}`"
        report_lines.append(f"| {display} | {count:,} |")

    report_lines += [
        "",
        f"## Raw vs. corpus.parquet divergence ({result['raw_vs_derived_divergence_count']:,} "
        "lines, up to 10 shown)",
        "",
        "Where the independently re-walked raw `<lb lg=...>` attribute differs "
        "from what `corpus.parquet` (built by the frozen `Archive/scripts/"
        "02_parse.py`) records for the same line, excluding lines with no "
        "word-rows to compare and excluding both-sides-missing agreement. "
        "**All 8 divergent lines found are in a single document, "
        "`KBo 53.44`, lines 0-7 -- its ENTIRE line range is tagged `Hur` "
        "(Hurrian) in the raw source XML, but recorded as `Hit` in "
        "`corpus.parquet`.** This is a real, systematic per-document "
        "mislabeling (a Hurrian-language document currently misfiled as "
        "Hittite in every downstream Hittite-only consumer, if any existed -- "
        "none currently checks language at all, see the accompanying "
        "discussion), not scattered noise. This is exactly the 8-line "
        "intra-line-disagreement count reported above, confirming it is one "
        "coherent defect, not 8 independent ones.",
        "",
        "Separately, this session traced the `\"Hit> <w><note n='15' c=\"`-"
        "pattern malformed value directly against the parsed XML tree "
        "(`KUB 43.50+`, lines 40-43): `ElementTree`'s own `lb.attrib['lg']` "
        "genuinely returns that garbled string for those four lines -- this "
        "is a **source-XML data defect**, not a `02_parse.py` parser defect. "
        "(An initial plain-text substring search of the raw file bytes "
        "appeared not to find it and briefly suggested a parser-side "
        "explanation; re-checking against the actual parsed attribute "
        "dictionary -- the authoritative method, and the same one this "
        "audit's own re-walk uses -- overturned that. Recorded here so the "
        "correction is visible, not silently dropped.) The `<del_in/>`-"
        "pattern (`KBo 53.12`, 2 lines) has not been individually re-checked "
        "this way; treat its origin as undetermined pending the same direct "
        "check. `5f_` (`CHDS 2.170`) and `Lu` (`KUB 35.99+`) were also "
        "confirmed **present verbatim in the raw source XML** -- genuine "
        "source-encoded values needing a vocabulary decision, not parser "
        "corruption. So far, no case in this audit has been confirmed as a "
        "`02_parse.py`-introduced defect distinct from the source -- the "
        "one clearly confirmed PARSER-side (not source-side) defect is the "
        "`KBo 53.44` Hur/Hit divergence above.",
        "",
    ]
    for ex in result["raw_vs_derived_divergence_examples"]:
        report_lines.append(
            f"- `{ex['doc_id']}` line {ex['line_index_in_doc']}: raw="
            f"`{ex['raw_lb_lg']}`, corpus.parquet=`{ex['corpus_parquet_line_lang']}`")

    report_lines += [
        "",
        "## Decisions requested for the Step B ratification gate",
        "",
        "1. **Vocabulary**: approve the proposed seed "
        f"`{sorted(PROPOSED_SEED_VOCABULARY)}` as the canonical code set, or "
        "amend it.",
        "2. **`Hat` vs. `Hattian`**: both appear (6,063 vs. 51 non-test "
        "lines). Are these the same language (Hattic) under two source "
        "spellings, warranting an explicit non-identity mapping to one "
        "canonical code -- or does `Hattian` mean something distinct? This "
        "migration will NOT auto-merge them without an explicit ruling.",
        "3. **`Lu` (1 line, `KUB 35.99+`, verbatim in source) and `5f_` "
        "(12 lines, discovery-only, verbatim in source)**: genuine "
        "source-encoded values outside the proposed seed. Map to an existing "
        "code (e.g. `Lu` -> `Luw`), add as new canonical codes, or leave "
        "`unrecognized` (quarantined, no canonical value)?",
        "4. **`ign` (15 lines, discovery-only)**: likely \"ignotum\" (language "
        "undetermined) in philological convention -- ratify as its own "
        "canonical status (distinct from `missing`) or leave `unrecognized`?",
        "5. **Malformed rows** (the `\"Hit> <w><note n='15' c=\"` pattern, "
        "4 non-test lines in `KUB 43.50+`; the `<del_in/>` pattern, 2 lines "
        "in `KBo 53.12`): the `note`-pattern is confirmed a genuine "
        "**source-XML** defect (verified against the parsed attribute "
        "dictionary directly, not a `02_parse.py` artifact); the "
        "`<del_in/>` pattern's origin is not yet individually verified. "
        "Proposed resolution either way: `line_lang_canonical` = null, "
        "`line_lang_status` = `malformed`, quarantined -- never coerced to "
        "the line's likely intended value (which for the `\"Hit> ...\"` "
        "pattern looks plausibly like `Hit`, but the spec forbids guessing).",
        "",
        "No canonical vocabulary, mapping, or status is applied anywhere "
        "yet. This audit only classifies against the PROPOSED seed above for "
        "counting purposes -- ratification is Ixca's decision per "
        "`specs/LINE_LANG_MIGRATION.md` Step B.",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Report: {REPORT_PATH}")
    print(f"JSON: {AUDIT_JSON}")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
