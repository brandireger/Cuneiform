#!/usr/bin/env python3
"""specs/LINE_LANG_MIGRATION.md, Step C -- versioned deterministic rebuild.

Ratified 2026-07-25 (Ixca), following the Step A audit
(migrations/line_lang_v1/audit_report.md):

  - Canonical vocabulary (7 codes): Hit, Akk, Sum, Hat, Hur, Luw, Pal.
  - Ratified non-identity mapping: Hattian -> Hat (same language, two
    source spellings).
  - Lu, 5f_, ign (and anything else lexically clean but outside the
    above) are quarantined as `unrecognized` -- canonical=null. Not
    guessed at; revisit with more context later.
  - Malformed values (XML-markup-like content) are quarantined as
    `malformed` -- canonical=null, never coerced to a likely value.

Applies the ratified rule MECHANICALLY to every document in the pinned
corpus, all splits included -- but never prints, samples, or otherwise
exposes test-side values; only combined (not split-broken-out) totals
and non-test (train/dev/discovery) per-split breakdowns are reported,
per the migration spec's Step C instruction.

Writes only to migrations/line_lang_v1/ (a new, non-reused path); does
not touch Phase1_pipeline/p2_out/corpus.parquet, splits.parquet, or any
other frozen artifact.

Usage:
    python scripts/line_lang_rebuild.py
"""
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import pandas as pd  # noqa: E402

import evidence_policy as ep  # noqa: E402
from phase2_io import split_lookup_fail_closed  # noqa: E402

ZIP_PATH = Path("TLHdig_0.2.0-beta.zip")
PINNED_ZIP_MD5 = "93e71e2560f5e109c87713d5590cb059"
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")

OUT_DIR = Path("migrations/line_lang_v1")
CANONICAL_PARQUET = OUT_DIR / "line_lang_canonical.parquet"
REPORT_PATH = OUT_DIR / "rebuild_report.md"
MANIFEST_PATH = OUT_DIR / "rebuild_manifest.json"

RATIFIED_VOCABULARY = ("Hit", "Akk", "Sum", "Hat", "Hur", "Luw", "Pal")
RATIFIED_MAPPINGS = {"Hattian": "Hat"}
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


def classify_and_map(raw_value):
    if raw_value is None or raw_value == "":
        return "missing", None, "missing_v1"
    if MALFORMED_CHARS.search(raw_value) or len(raw_value) > 15:
        return "malformed", None, "malformed_quarantine_v1"
    if raw_value in RATIFIED_VOCABULARY:
        return "valid", raw_value, "identity_v1"
    if raw_value in RATIFIED_MAPPINGS:
        return "valid", RATIFIED_MAPPINGS[raw_value], "hattian_to_hat_v1"
    return "unrecognized", None, "unrecognized_quarantine_v1"


def main():
    zip_md5 = md5_file(ZIP_PATH)
    zip_pin_ok = zip_md5 == PINNED_ZIP_MD5
    print(f"Corpus zip MD5: {zip_md5} (matches CLAUDE.md pin: {zip_pin_ok})")

    splits = pd.read_parquet(SPLITS_PATH, columns=["doc_id", "main_split"])
    split_lookup, ambiguous_ids = split_lookup_fail_closed(splits)

    zp = zipfile.ZipFile(ZIP_PATH)
    names = [
        n for n in zp.namelist()
        if n.lower().endswith(".xml") and not n.endswith("/") and not is_junk(n)
    ]

    rows = []
    n_docs = 0
    n_parse_errors = 0
    status_counts_all = Counter()
    status_counts_non_test = {"train": Counter(), "dev": Counter(), "discovery": Counter()}

    for name in names:
        raw = zp.read(name)
        try:
            root_check = ET.fromstring(raw)
        except ET.ParseError:
            n_parse_errors += 1
            continue
        doc_id_el = root_check.find(".//{*}docID")
        doc_id = (doc_id_el.text or "").strip() if doc_id_el is not None else Path(name).stem
        try:
            raw_lang_by_line = raw_lb_lang_by_line(raw)
        except ET.ParseError:
            n_parse_errors += 1
            continue
        n_docs += 1
        split = split_lookup.get(doc_id, "unknown_or_ambiguous")
        for line_idx, raw_val in raw_lang_by_line.items():
            status, canonical, rule_id = classify_and_map(raw_val)
            rows.append({
                "doc_id": doc_id, "line_index_in_doc": line_idx,
                "line_lang_raw": raw_val, "line_lang_canonical": canonical,
                "line_lang_status": status, "line_lang_rule_id": rule_id,
            })
            status_counts_all[status] += 1
            if split in status_counts_non_test:
                status_counts_non_test[split][status] += 1

    df = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CANONICAL_PARQUET, index=False)

    print(f"Documents processed: {n_docs:,} (parse errors skipped: {n_parse_errors})")
    print(f"Total lines (all splits, combined -- not split-broken-out): {len(df):,}")
    print(f"Status counts (all splits, combined): {dict(status_counts_all)}")
    print(f"Wrote {CANONICAL_PARQUET}")

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("artifact_strict", POLICIES_PATH)
    manifest = ep.build_manifest(
        task="line_lang_rebuild_step_c",
        evidence_policy=policy.name,
        features_requested=["line_lang"],
        registry=registry,
        policy=policy,
        split_manifest_path=SPLITS_PATH,
        config_path=REGISTRY_PATH,
        seed=20260725,
        declared_statistics_universe=(
            "all documents, all splits (mechanical rule application only; "
            "test-side values never printed, sampled, or ranked)"),
    )
    manifest["zip_md5"] = zip_md5
    manifest["zip_md5_matches_claude_md_pin"] = zip_pin_ok
    manifest["ratified_vocabulary"] = list(RATIFIED_VOCABULARY)
    manifest["ratified_mappings"] = RATIFIED_MAPPINGS
    manifest["documents_processed"] = n_docs
    manifest["parse_errors_skipped"] = n_parse_errors
    manifest["total_lines_all_splits_combined"] = len(df)
    manifest["status_counts_all_splits_combined"] = dict(status_counts_all)
    manifest["status_counts_by_non_test_split"] = {
        split: dict(counts) for split, counts in status_counts_non_test.items()
    }
    ep.write_manifest(manifest, MANIFEST_PATH)

    report_lines = [
        "# `line_lang` migration -- Step C deterministic rebuild",
        "",
        "Ratified 2026-07-25 (Ixca): 7-code canonical vocabulary "
        "(`Hit, Akk, Sum, Hat, Hur, Luw, Pal`), `Hattian -> Hat` mapped, "
        "`Lu`/`5f_`/`ign` (and anything else outside the vocabulary) "
        "quarantined as `unrecognized`, XML-markup-like values quarantined "
        "as `malformed`. Applied mechanically to every document in the "
        "pinned corpus, all splits -- test-side values were never printed, "
        "sampled, or ranked; only combined (not test-isolated) totals and "
        "non-test per-split breakdowns appear below.",
        "",
        f"- Corpus zip MD5: `{zip_md5}` "
        f"({'matches' if zip_pin_ok else 'DOES NOT MATCH'} the pinned "
        f"`{PINNED_ZIP_MD5}`).",
        f"- Documents processed: **{n_docs:,}** (parse errors skipped: "
        f"{n_parse_errors}, matching the corpus-wide known parse-error count).",
        f"- Total lines written (all splits combined): **{len(df):,}**.",
        "",
        "## Status counts, all splits combined",
        "",
        "| status | count |",
        "|---|---|",
    ]
    for status, count in sorted(status_counts_all.items(), key=lambda kv: -kv[1]):
        report_lines.append(f"| {status} | {count:,} |")

    report_lines += [
        "",
        "## Status counts by non-test split",
        "",
        "| split | valid | missing | malformed | unrecognized |",
        "|---|---|---|---|---|",
    ]
    for split, counts in status_counts_non_test.items():
        report_lines.append(
            f"| {split} | {counts.get('valid', 0):,} | {counts.get('missing', 0):,} | "
            f"{counts.get('malformed', 0):,} | {counts.get('unrecognized', 0):,} |")

    report_lines += [
        "",
        "## Output contract",
        "",
        f"`{CANONICAL_PARQUET}`: one row per (`doc_id`, `line_index_in_doc`), "
        "columns `line_lang_raw` (verbatim source value, null only if "
        "absent), `line_lang_canonical` (ratified code or null), "
        "`line_lang_status` (`valid`/`missing`/`malformed`/`unrecognized`), "
        "`line_lang_rule_id` (stable rule identifier). Downstream consumers "
        "must request `line_lang_canonical` explicitly and must not treat "
        "`line_lang_raw` as canonical.",
        "",
        "This is a NEW artifact under a versioned directory -- it does not "
        "modify `Phase1_pipeline/p2_out/corpus.parquet`, `splits.parquet`, "
        "or any other frozen artifact. Rollback is selection-based: ignore "
        "this directory and nothing else needs to change.",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Report: {REPORT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
