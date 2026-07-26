#!/usr/bin/env python3
"""Gate 0 evidence audit for AOxml document/line/word language tags.

This script opens XML payloads only after a unique filename stem maps to
train, dev, or discovery. Test, unmatched, ambiguous-split, and duplicate-
stem payloads remain unopened. It produces aggregate decision evidence; it
does not build a language migration or model input.

Usage:
    python scripts/phase4_gate0_language_audit.py
"""

import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

import corpus_expansion_audit as cea  # noqa: E402
import evidence_policy as ep  # noqa: E402
from phase2_io import split_lookup_fail_closed  # noqa: E402


ZIP_PATH = Path("TLHdig_0.2.0-beta.zip")
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
CONFIG_PATH = Path("configs/language_layers_v2.json")
REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")
OUT_DIR = Path("Phase4/phase4_out")
RESULT_PATH = OUT_DIR / "gate0_language_audit.json"
MANIFEST_PATH = OUT_DIR / "gate0_language_audit_manifest.json"
REPORT_PATH = OUT_DIR / "gate0_language_audit_report.md"

ALLOWED_SPLITS = {"train", "dev", "discovery"}
PROHIBITED_SPLITS = {"test"}
CANONICAL = {"Hit", "Akk", "Sum", "Hat", "Hur", "Luw", "Pal"}
MAPPINGS = {"Hattian": "Hat"}
HPM_GUIDE = "https://www.hethport.uni-wuerzburg.de/HPM/hpm.php?p=hpmguide"


def canonicalize(raw):
    if raw is None:
        return None, "absent"
    if raw == "":
        return None, "explicit_empty"
    if raw in CANONICAL:
        return raw, "valid"
    if raw in MAPPINGS:
        return MAPPINGS[raw], "valid_mapped"
    return None, "unrecognized_or_malformed"


def inspect_root(root):
    """Return aggregate counters for one already-gated AOxml document."""
    doc_counts = Counter()
    line_counts = Counter()
    word_counts = Counter()
    pair_counts = Counter()
    effective_changes = Counter()
    documents_changed = False

    text_el = root.find(".//{*}text")
    doc_raw = (
        text_el.get("{http://www.w3.org/XML/1998/namespace}lang")
        if text_el is not None
        else None
    )
    doc_counts[doc_raw if doc_raw is not None else "<ABSENT>"] += 1

    current_line_raw = None
    for element in root.iter():
        tag = cea.local(element.tag)
        if tag == "lb":
            current_line_raw = element.get("lg")
            line_counts[
                current_line_raw if current_line_raw is not None else "<ABSENT>"
            ] += 1
            continue
        if tag != "w" or "lg" not in element.attrib:
            continue

        word_raw = element.get("lg")
        word_counts[word_raw if word_raw is not None else "<ABSENT>"] += 1
        pair_counts[(
            current_line_raw if current_line_raw is not None else "<ABSENT>",
            word_raw if word_raw is not None else "<ABSENT>",
        )] += 1

        line_canonical, _ = canonicalize(current_line_raw)
        word_canonical, word_status = canonicalize(word_raw)
        if word_status.startswith("valid") and word_canonical != line_canonical:
            effective_changes[(line_canonical or "<UNRESOLVED>", word_canonical)] += 1
            documents_changed = True

    return {
        "document_values": doc_counts,
        "line_values": line_counts,
        "word_values": word_counts,
        "line_word_pairs": pair_counts,
        "valid_word_overrides": effective_changes,
        "document_changed": documents_changed,
    }


def counter_dict(counter):
    return {
        str(key): value
        for key, value in sorted(
            counter.items(), key=lambda item: (-item[1], str(item[0]))
        )
    }


def pair_counter_rows(counter, left_name, right_name):
    return [
        {left_name: key[0], right_name: key[1], "count": value}
        for key, value in sorted(
            counter.items(), key=lambda item: (-item[1], str(item[0]))
        )
    ]


def main():
    splits = pd.read_parquet(SPLITS_PATH, columns=["doc_id", "main_split"])
    split_lookup, ambiguous = split_lookup_fail_closed(splits)
    index = cea.archive_index(ZIP_PATH)

    gate_counts = Counter()
    payload_reads = Counter()
    parse_errors = Counter()
    doc_values = Counter()
    line_values = Counter()
    word_values = Counter()
    line_word_pairs = Counter()
    valid_word_overrides = Counter()
    changed_documents = 0

    with zipfile.ZipFile(ZIP_PATH) as archive:
        for stem, infos in sorted(index["by_stem"].items()):
            gate = cea.classify_stem(
                stem,
                split_lookup,
                ambiguous,
                index["duplicates"],
                ALLOWED_SPLITS,
                PROHIBITED_SPLITS,
            )
            gate_counts[gate] += len(infos)
            if not gate.startswith("ALLOWED_"):
                continue
            if len(infos) != 1:
                raise AssertionError("Gate allowed a non-unique archive stem")

            payload_reads[gate] += 1
            raw = archive.read(infos[0])
            try:
                root = ET.fromstring(raw)
            except ET.ParseError:
                parse_errors[gate] += 1
                continue

            inspected = inspect_root(root)
            doc_values.update(inspected["document_values"])
            line_values.update(inspected["line_values"])
            word_values.update(inspected["word_values"])
            line_word_pairs.update(inspected["line_word_pairs"])
            valid_word_overrides.update(inspected["valid_word_overrides"])
            changed_documents += int(inspected["document_changed"])

    if payload_reads.get("PROTECTED_TEST", 0):
        raise AssertionError("Protected test payload was read")
    if any(not gate.startswith("ALLOWED_") for gate in payload_reads):
        raise AssertionError("A quarantined payload was read")

    result = {
        "label": "GATE 0 DECISION EVIDENCE - not a model result",
        "statistics_universe": (
            "unique filename stems mapped to frozen train + dev + discovery; "
            "test, unmatched, split-ambiguous, and duplicate stems unopened"
        ),
        "archive_summary": index["summary"],
        "gate_counts": counter_dict(gate_counts),
        "payload_read_gate_counts": counter_dict(payload_reads),
        "parse_errors_by_allowed_gate": counter_dict(parse_errors),
        "document_xml_lang_counts": counter_dict(doc_values),
        "line_lb_lg_counts": counter_dict(line_values),
        "word_w_lg_counts": counter_dict(word_values),
        "line_word_language_pairs": pair_counter_rows(
            line_word_pairs, "line_raw", "word_raw"
        ),
        "valid_word_override_pairs": pair_counter_rows(
            valid_word_overrides, "line_canonical", "word_canonical"
        ),
        "valid_word_override_count": sum(valid_word_overrides.values()),
        "documents_with_valid_word_override": changed_documents,
        "explicit_empty_word_language_count": word_values.get("", 0),
        "hpm_guide": HPM_GUIDE,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("transcription_assisted", POLICIES_PATH)
    manifest = ep.build_manifest(
        task="phase4_gate0_language_semantics_audit",
        evidence_policy=policy.name,
        features_requested=["doc_lang_raw", "line_lang_raw", "word_lang_raw"],
        registry=registry,
        policy=policy,
        dataset_manifest_path=ZIP_PATH,
        split_manifest_path=SPLITS_PATH,
        config_path=CONFIG_PATH,
        seed=20260725,
        declared_statistics_universe=result["statistics_universe"],
    )
    manifest["payload_read_gate_counts"] = counter_dict(payload_reads)
    manifest["protected_test_payloads_read"] = 0
    manifest["hpm_guide"] = HPM_GUIDE
    ep.write_manifest(manifest, MANIFEST_PATH)

    top_pairs = result["valid_word_override_pairs"][:12]
    report = [
        "# Phase 4 Gate 0 language audit",
        "",
        "**GATE 0 DECISION EVIDENCE — not a model result.**",
        "",
        "XML payloads were opened only after a unique filename stem mapped to "
        "frozen train, dev, or discovery. Test, unmatched, ambiguous, and "
        "duplicate-stem payloads remained unopened.",
        "",
        f"- Allowed payloads opened: **{sum(payload_reads.values()):,}**.",
        "- Protected test payloads opened: **0**.",
        f"- Parse errors among allowed payloads: **{sum(parse_errors.values()):,}**.",
        f"- Explicit `w@lg` values: **{sum(word_values.values()):,}**.",
        f"- Valid word overrides differing from the line default: "
        f"**{result['valid_word_override_count']:,}** across "
        f"**{changed_documents:,}** documents.",
        f"- Explicit empty `w@lg` values: "
        f"**{result['explicit_empty_word_language_count']:,}**.",
        "",
        "## Primary-source semantics",
        "",
        f"The [official HPM guide]({HPM_GUIDE}) states that the paragraph "
        "style identifies the language of the whole line, while character "
        "language styles mark inserted words or incomplete quotations in "
        "another language. This supports word override, otherwise line "
        "inheritance. Document `xml:lang` is not needed as fallback.",
        "",
        "## Largest valid word overrides",
        "",
        "| line | word | count |",
        "|---|---|---:|",
    ]
    for row in top_pairs:
        report.append(
            f"| `{row['line_canonical']}` | `{row['word_canonical']}` | "
            f"{row['count']:,} |"
        )
    report += [
        "",
        "## Gate 0 implications",
        "",
        "- Valid explicit word language overrides the line default.",
        "- Absence of `w@lg` inherits the valid line language.",
        "- Explicit empty `w@lg` is preserved as an anomaly and may inherit "
        "a valid line only with `RESOLVED_WITH_SOURCE_ANOMALY` status.",
        "- Malformed/unrecognized explicit word tags remain unresolved.",
        "- Document language is retained for provenance but is not a fallback.",
        "- Language annotations are `EDITORIAL_TRANSCRIPTION` evidence.",
    ]
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(f"Report: {REPORT_PATH}")
    print(f"Result: {RESULT_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
