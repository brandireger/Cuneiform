#!/usr/bin/env python3
"""Build and verify the Gate 1 word-aware language-span migration.

Protected test, unmatched, ambiguous, and duplicate-stem XML payloads are
never opened. The migration records document and line language attributes,
plus explicit word-language spans; words without ``w@lg`` inherit at Gate 2
through the shared ``language_layers_v2.resolve_word_language`` function.

Usage:
    python scripts/phase4_language_layers_v2.py
"""

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

import corpus_expansion_audit as cea  # noqa: E402
import evidence_policy as ep  # noqa: E402
import language_layers_v2 as llv2  # noqa: E402
from phase2_io import split_lookup_fail_closed  # noqa: E402

import pandas as pd  # noqa: E402


ZIP_PATH = Path("TLHdig_0.2.0-beta.zip")
PINNED_ZIP_MD5 = "93e71e2560f5e109c87713d5590cb059"
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
CONFIG_PATH = Path("configs/language_layers_v2.json")
REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")
SCRIPT_PATH = Path("scripts/phase4_language_layers_v2.py")
GATE0_AUDIT_PATH = Path(
    "Phase4/phase4_out/gate0_language_audit.json")

FROZEN_PATHS = {
    "corpus_zip": ZIP_PATH,
    "frozen_splits": SPLITS_PATH,
    "frozen_corpus": Path("Phase1_pipeline/p2_out/corpus.parquet"),
    "frozen_decomposed_tokens":
        Path("Phase1_pipeline/p4_out/decomposed_corpus.parquet"),
    "ratified_line_lang_v1":
        Path("migrations/line_lang_v1/line_lang_canonical.parquet"),
}

ALLOWED_SPLITS = {"train", "dev", "discovery"}
PROHIBITED_SPLITS = {"test"}
SOURCE_LEVELS = ("DOCUMENT", "LINE", "WORD")
ALLOWED_SOURCE_STATUSES = llv2.SOURCE_STATUSES
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SEED = 20260725

OUTPUT_COLUMNS = [
    "doc_id",
    "main_split",
    "language_level",
    "line_index_in_doc",
    "word_index_in_line",
    "language_attribute_present",
    "language_raw",
    "language_canonical",
    "language_status",
    "language_rule_id",
    "line_lang_canonical",
    "line_lang_status",
    "effective_lang_canonical",
    "effective_lang_status",
    "effective_lang_source",
    "effective_lang_rule_id",
    "workbench_category",
    "source_archive_member",
    "source_payload_sha256",
]

OUTPUT_SCHEMA = pa.schema([
    ("doc_id", pa.string()),
    ("main_split", pa.string()),
    ("language_level", pa.string()),
    ("line_index_in_doc", pa.int32()),
    ("word_index_in_line", pa.int32()),
    ("language_attribute_present", pa.bool_()),
    ("language_raw", pa.string()),
    ("language_canonical", pa.string()),
    ("language_status", pa.string()),
    ("language_rule_id", pa.string()),
    ("line_lang_canonical", pa.string()),
    ("line_lang_status", pa.string()),
    ("effective_lang_canonical", pa.string()),
    ("effective_lang_status", pa.string()),
    ("effective_lang_source", pa.string()),
    ("effective_lang_rule_id", pa.string()),
    ("workbench_category", pa.string()),
    ("source_archive_member", pa.string()),
    ("source_payload_sha256", pa.string()),
])


def digest_file(path, algorithm="sha256"):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_row(
        *,
        doc_id,
        main_split,
        level,
        line_index,
        word_index,
        attribute_present,
        value,
        line_value,
        effective,
        archive_member,
        payload_sha256):
    return {
        "doc_id": doc_id,
        "main_split": main_split,
        "language_level": level,
        "line_index_in_doc": line_index,
        "word_index_in_line": word_index,
        "language_attribute_present": attribute_present,
        "language_raw": value.raw,
        "language_canonical": value.canonical,
        "language_status": value.status,
        "language_rule_id": value.rule_id,
        "line_lang_canonical":
            line_value.canonical if line_value is not None else None,
        "line_lang_status":
            line_value.status if line_value is not None else None,
        "effective_lang_canonical":
            effective.canonical if effective is not None else None,
        "effective_lang_status":
            effective.status if effective is not None else None,
        "effective_lang_source":
            effective.source if effective is not None else None,
        "effective_lang_rule_id":
            effective.rule_id if effective is not None else None,
        "workbench_category": (
            effective.workbench_category
            if effective is not None and effective.workbench_category
            else llv2.language_status_workbench_category(value.status)
        ),
        "source_archive_member": archive_member,
        "source_payload_sha256": payload_sha256,
    }


def extract_outside_primary_word_anomalies(
        root,
        text_el,
        *,
        doc_id,
        main_split,
        archive_member,
        payload_sha256,
        contract):
    primary_element_ids = (
        {id(element) for element in text_el.iter()}
        if text_el is not None else set()
    )
    anomalies = []
    document_word_index = -1
    for element in root.iter():
        if cea.local(element.tag) != "w":
            continue
        document_word_index += 1
        if "lg" not in element.attrib or id(element) in primary_element_ids:
            continue
        value = llv2.classify_language(
            element.get("lg"),
            attribute_present=True,
            level="WORD",
            contract=contract,
        )
        stable_material = (
            f"{doc_id}\0{document_word_index}\0{payload_sha256}").encode(
                "utf-8")
        anomalies.append({
            "record_type": "source_language_anomaly",
            "anomaly_id": hashlib.sha256(stable_material).hexdigest(),
            "category": "PARSER_ANOMALY",
            "anomaly_type":
                "explicit_word_language_outside_primary_text",
            "doc_id": doc_id,
            "main_split": main_split,
            "document_word_index": document_word_index,
            "language_raw": value.raw,
            "language_canonical": value.canonical,
            "language_status": value.status,
            "language_rule_id": value.rule_id,
            "evidence_class": "EDITORIAL_TRANSCRIPTION",
            "source_archive_member": archive_member,
            "source_payload_sha256": payload_sha256,
            "ground_truth_status": "NOT_CORPUS_TRUTH",
        })
    return anomalies


def extract_document_rows(
        root,
        *,
        doc_id,
        main_split,
        archive_member,
        payload_sha256,
        contract):
    """Extract document/line/explicit-word spans in deterministic XML order."""
    rows = []
    source_counts = Counter({"DOCUMENT": 1})
    text_el = root.find(".//{*}text")
    doc_present = text_el is not None and XML_LANG in text_el.attrib
    doc_raw = text_el.get(XML_LANG) if doc_present else None
    doc_value = llv2.classify_language(
        doc_raw,
        attribute_present=doc_present,
        level="DOCUMENT",
        contract=contract,
    )
    rows.append(make_row(
        doc_id=doc_id,
        main_split=main_split,
        level="DOCUMENT",
        line_index=None,
        word_index=None,
        attribute_present=doc_present,
        value=doc_value,
        line_value=None,
        effective=None,
        archive_member=archive_member,
        payload_sha256=payload_sha256,
    ))
    anomalies = extract_outside_primary_word_anomalies(
        root,
        text_el,
        doc_id=doc_id,
        main_split=main_split,
        archive_member=archive_member,
        payload_sha256=payload_sha256,
        contract=contract,
    )
    if text_el is None:
        return rows, source_counts, anomalies

    line_index = -1
    word_index = -1
    current_line = llv2.classify_language(
        None,
        attribute_present=False,
        level="LINE",
        contract=contract,
    )

    for element in text_el.iter():
        tag = cea.local(element.tag)
        if tag == "lb":
            source_counts["LINE"] += 1
            line_index += 1
            word_index = -1
            line_present = "lg" in element.attrib
            current_line = llv2.classify_language(
                element.get("lg") if line_present else None,
                attribute_present=line_present,
                level="LINE",
                contract=contract,
            )
            rows.append(make_row(
                doc_id=doc_id,
                main_split=main_split,
                level="LINE",
                line_index=line_index,
                word_index=None,
                attribute_present=line_present,
                value=current_line,
                line_value=current_line,
                effective=None,
                archive_member=archive_member,
                payload_sha256=payload_sha256,
            ))
            continue
        if tag != "w":
            continue

        word_index += 1
        if "lg" not in element.attrib:
            continue
        source_counts["WORD"] += 1
        word_value = llv2.classify_language(
            element.get("lg"),
            attribute_present=True,
            level="WORD",
            contract=contract,
        )
        effective = llv2.resolve_word_language(
            word_value,
            current_line,
            word_attribute_present=True,
            contract=contract,
        )
        rows.append(make_row(
            doc_id=doc_id,
            main_split=main_split,
            level="WORD",
            line_index=line_index,
            word_index=word_index,
            attribute_present=True,
            value=word_value,
            line_value=current_line,
            effective=effective,
            archive_member=archive_member,
            payload_sha256=payload_sha256,
        ))
    return rows, source_counts, anomalies


def new_stats():
    return {
        "gate_counts": Counter(),
        "payload_read_gate_counts": Counter(),
        "parse_errors_by_allowed_gate": Counter(),
        "parsed_documents": 0,
        "source_counts_by_level": Counter(),
        "output_counts_by_level": Counter(),
        "status_counts_by_level": {
            level: Counter() for level in SOURCE_LEVELS
        },
        "status_counts_by_split": {
            split: Counter() for split in sorted(ALLOWED_SPLITS)
        },
        "effective_status_counts": Counter(),
        "effective_source_counts": Counter(),
        "workbench_category_counts": Counter(),
        "source_anomaly_counts": Counter(),
        "duplicate_output_keys": 0,
    }


def row_key(row):
    return (
        row["doc_id"],
        row["language_level"],
        row["line_index_in_doc"],
        row["word_index_in_line"],
    )


def update_logical_hash(digest, row):
    encoded = json.dumps(
        [row[column] for column in OUTPUT_COLUMNS],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest.update(encoded)
    digest.update(b"\n")


def update_json_record_hash(digest, record):
    digest.update(json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8"))
    digest.update(b"\n")


def build_pass(contract, split_lookup, ambiguous, archive_index, *, collect):
    stats = new_stats()
    rows = [] if collect else None
    anomaly_records = [] if collect else None
    keys = set()
    logical_digest = hashlib.sha256()
    anomaly_digest = hashlib.sha256()

    with zipfile.ZipFile(ZIP_PATH) as archive:
        for stem, infos in sorted(archive_index["by_stem"].items()):
            gate = cea.classify_stem(
                stem,
                split_lookup,
                ambiguous,
                archive_index["duplicates"],
                ALLOWED_SPLITS,
                PROHIBITED_SPLITS,
            )
            stats["gate_counts"][gate] += len(infos)
            if not gate.startswith("ALLOWED_"):
                continue
            if len(infos) != 1:
                raise AssertionError("Gate allowed a non-unique archive stem")

            stats["payload_read_gate_counts"][gate] += 1
            info = infos[0]
            raw = archive.read(info)
            payload_sha256 = hashlib.sha256(raw).hexdigest()
            try:
                root = ET.fromstring(raw)
            except ET.ParseError:
                stats["parse_errors_by_allowed_gate"][gate] += 1
                continue

            doc_id_el = root.find(".//{*}docID")
            source_doc_id = (
                (doc_id_el.text or "").strip()
                if doc_id_el is not None else stem
            )
            if source_doc_id != stem:
                raise AssertionError(
                    "Archive stem disagrees with source docID after the "
                    "split gate; refusing to migrate ambiguous content")

            main_split = gate.removeprefix("ALLOWED_").lower()
            doc_rows, source_counts, doc_anomalies = extract_document_rows(
                root,
                doc_id=stem,
                main_split=main_split,
                archive_member=info.filename,
                payload_sha256=payload_sha256,
                contract=contract,
            )
            stats["parsed_documents"] += 1
            stats["source_counts_by_level"].update(source_counts)
            stats["source_anomaly_counts"][
                "explicit_word_language_outside_primary_text"
            ] += len(doc_anomalies)
            stats["workbench_category_counts"]["PARSER_ANOMALY"] += len(
                doc_anomalies)
            for anomaly in doc_anomalies:
                update_json_record_hash(anomaly_digest, anomaly)
                if collect:
                    anomaly_records.append(anomaly)
            for row in doc_rows:
                level = row["language_level"]
                key = row_key(row)
                if key in keys:
                    stats["duplicate_output_keys"] += 1
                keys.add(key)
                stats["output_counts_by_level"][level] += 1
                stats["status_counts_by_level"][level][
                    row["language_status"]] += 1
                stats["status_counts_by_split"][main_split][
                    row["language_status"]] += 1
                if row["effective_lang_status"] is not None:
                    stats["effective_status_counts"][
                        row["effective_lang_status"]] += 1
                    stats["effective_source_counts"][
                        row["effective_lang_source"]] += 1
                if row["workbench_category"] is not None:
                    stats["workbench_category_counts"][
                        row["workbench_category"]] += 1
                update_logical_hash(logical_digest, row)
                if collect:
                    rows.append(row)

    if stats["payload_read_gate_counts"].get("PROTECTED_TEST", 0):
        raise AssertionError("Protected test payload was read")
    if any(
            not gate.startswith("ALLOWED_")
            for gate in stats["payload_read_gate_counts"]):
        raise AssertionError("A quarantined payload was read")
    return (
        rows,
        anomaly_records,
        stats,
        logical_digest.hexdigest(),
        anomaly_digest.hexdigest(),
    )


def serializable_stats(stats):
    result = {}
    for key, value in stats.items():
        if isinstance(value, Counter):
            result[key] = dict(sorted(value.items()))
        elif isinstance(value, dict):
            result[key] = {
                nested_key: dict(sorted(nested_value.items()))
                if isinstance(nested_value, Counter) else nested_value
                for nested_key, nested_value in sorted(value.items())
            }
        else:
            result[key] = value
    return result


def parquet_logical_hash(path):
    digest = hashlib.sha256()
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=8192):
        for row in batch.to_pylist():
            update_logical_hash(digest, row)
    return digest.hexdigest()


def validate_rows(rows, stats, contract):
    canonical = set(contract["canonical_codes"])
    checks = {
        "one_document_record_per_parsed_document":
            stats["output_counts_by_level"]["DOCUMENT"]
            == stats["parsed_documents"],
        "source_to_output_level_counts_exact":
            stats["source_counts_by_level"]
            == stats["output_counts_by_level"],
        "output_keys_unique": stats["duplicate_output_keys"] == 0,
        "all_source_statuses_allowed": all(
            row["language_status"] in ALLOWED_SOURCE_STATUSES for row in rows),
        "valid_rows_use_only_canonical_codes": all(
            row["language_canonical"] in canonical
            for row in rows if row["language_status"] == "valid"),
        "nonvalid_rows_have_null_canonical": all(
            row["language_canonical"] is None
            for row in rows if row["language_status"] != "valid"),
        "word_rows_are_explicit_attributes": all(
            row["language_attribute_present"]
            for row in rows if row["language_level"] == "WORD"),
        "effective_rows_are_word_rows": all(
            row["language_level"] == "WORD"
            for row in rows if row["effective_lang_status"] is not None),
        "unresolved_effective_rows_have_null_canonical": all(
            row["effective_lang_canonical"] is None
            for row in rows
            if (
                row["effective_lang_status"] is not None
                and row["effective_lang_status"].startswith("UNRESOLVED")
            )),
        "resolved_effective_rows_have_canonical_language": all(
            row["effective_lang_canonical"] in canonical
            for row in rows
            if row["effective_lang_status"] in {
                "RESOLVED", "RESOLVED_WITH_SOURCE_ANOMALY"
            }),
    }
    return checks


def markdown_status_table(status_counts_by_level):
    statuses = sorted(ALLOWED_SOURCE_STATUSES)
    lines = [
        "| level | " + " | ".join(statuses) + " |",
        "|---|" + "---:|" * len(statuses),
    ]
    for level in SOURCE_LEVELS:
        counts = status_counts_by_level[level]
        lines.append(
            f"| {level} | "
            + " | ".join(f"{counts.get(status, 0):,}" for status in statuses)
            + " |"
        )
    return lines


def main():
    contract = llv2.load_language_contract(CONFIG_PATH)
    output_dir = Path(contract["paths"]["migration_root"])
    language_spans_path = Path(contract["paths"]["language_spans"])
    if language_spans_path.parent != output_dir:
        raise llv2.LanguageContractError(
            "Language-spans path must live under the ratified migration root")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "rebuild_manifest.json"
    acceptance_path = output_dir / "gate1_acceptance.json"
    report_path = output_dir / "rebuild_report.md"
    verification_path = output_dir / "verification_report.md"

    frozen_hashes_before = {
        name: digest_file(path) for name, path in FROZEN_PATHS.items()
    }
    zip_md5 = digest_file(ZIP_PATH, "md5")
    if zip_md5 != PINNED_ZIP_MD5:
        raise AssertionError("Pinned corpus ZIP MD5 does not match")

    splits = pd.read_parquet(SPLITS_PATH, columns=["doc_id", "main_split"])
    split_lookup, ambiguous = split_lookup_fail_closed(splits)
    archive_index = cea.archive_index(ZIP_PATH)
    gate0_audit = json.loads(
        GATE0_AUDIT_PATH.read_text(encoding="utf-8"))
    gate0_explicit_word_language_count = int(
        gate0_audit["explicit_empty_word_language_count"]
        + sum(
            row["count"]
            for row in gate0_audit["line_word_language_pairs"]
            if row["word_raw"] != ""
        )
    )

    (
        rows,
        anomaly_records,
        first_stats,
        first_logical_hash,
        first_anomaly_hash,
    ) = build_pass(
        contract, split_lookup, ambiguous, archive_index, collect=True)
    first_serialized_stats = serializable_stats(first_stats)
    row_checks = validate_rows(rows, first_stats, contract)
    if not all(row_checks.values()):
        failed = sorted(name for name, passed in row_checks.items() if not passed)
        raise AssertionError(f"Gate 1 row validation failed: {failed}")

    table = pa.Table.from_pylist(rows, schema=OUTPUT_SCHEMA)
    pq.write_table(
        table,
        language_spans_path,
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )
    persisted_logical_hash = parquet_logical_hash(language_spans_path)

    quarantine_path = output_dir / "quarantined_source_anomalies.jsonl"
    with open(quarantine_path, "w", encoding="utf-8", newline="\n") as output:
        for anomaly in anomaly_records:
            output.write(json.dumps(
                anomaly,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ))
            output.write("\n")

    (
        _,
        _,
        second_stats,
        second_logical_hash,
        second_anomaly_hash,
    ) = build_pass(
        contract, split_lookup, ambiguous, archive_index, collect=False)
    second_serialized_stats = serializable_stats(second_stats)

    frozen_hashes_after = {
        name: digest_file(path) for name, path in FROZEN_PATHS.items()
    }
    frozen_unchanged = frozen_hashes_before == frozen_hashes_after
    deterministic = (
        first_logical_hash == second_logical_hash == persisted_logical_hash
        and first_anomaly_hash == second_anomaly_hash
        and first_serialized_stats == second_serialized_stats
    )

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("transcription_assisted", POLICIES_PATH)
    manifest = ep.build_manifest(
        task="phase4_gate1_language_layers_v2_migration",
        evidence_policy=policy.name,
        features_requested=[
            "doc_lang_raw", "line_lang_raw", "word_lang_raw"],
        registry=registry,
        policy=policy,
        dataset_manifest_path=ZIP_PATH,
        split_manifest_path=SPLITS_PATH,
        config_path=CONFIG_PATH,
        seed=SEED,
        declared_statistics_universe=(
            "unique filename stems mapped to frozen train + dev + discovery; "
            "test, unmatched, split-ambiguous, and duplicate stems unopened"),
    )
    manifest.update({
        "script_path": str(SCRIPT_PATH),
        "script_sha256": digest_file(SCRIPT_PATH),
        "registry_sha256": digest_file(REGISTRY_PATH),
        "policy_sha256": digest_file(POLICIES_PATH),
        "gate0_audit_sha256": digest_file(GATE0_AUDIT_PATH),
        "zip_md5": zip_md5,
        "zip_md5_matches_pin": True,
        "language_contract_version": contract["contract_version"],
        "effective_language_rule_id":
            contract["effective_rule"]["rule_id"],
        "canonical_codes": contract["canonical_codes"],
        "canonical_mappings": contract["canonical_mappings"],
        "protected_test_payloads_read": 0,
        "frozen_hashes_before": frozen_hashes_before,
        "frozen_hashes_after": frozen_hashes_after,
        "frozen_hashes_unchanged": frozen_unchanged,
        "output_path": str(language_spans_path),
        "output_file_sha256": digest_file(language_spans_path),
        "output_logical_sha256": first_logical_hash,
        "second_build_logical_sha256": second_logical_hash,
        "persisted_logical_sha256": persisted_logical_hash,
        "quarantine_path": str(quarantine_path),
        "quarantine_file_sha256": digest_file(quarantine_path),
        "quarantine_logical_sha256": first_anomaly_hash,
        "second_build_quarantine_logical_sha256": second_anomaly_hash,
        "quarantine_record_count": len(anomaly_records),
        "deterministic_double_build": deterministic,
        "statistics": first_serialized_stats,
        "gate0_explicit_word_language_count":
            gate0_explicit_word_language_count,
    })
    ep.write_manifest(manifest, manifest_path)

    acceptance_checks = {
        **row_checks,
        "protected_test_payloads_read_zero":
            manifest["protected_test_payloads_read"] == 0,
        "frozen_artifact_hashes_unchanged": frozen_unchanged,
        "two_builds_and_persisted_table_logically_identical": deterministic,
        "evidence_policy_manifest_completed": (
            manifest["evidence_policy"] == "transcription_assisted"
            and manifest["prohibited_features_encountered"] == []
        ),
        "parse_errors_fully_accounted": (
            sum(first_stats["parse_errors_by_allowed_gate"].values())
            + first_stats["parsed_documents"]
            == sum(first_stats["payload_read_gate_counts"].values())
        ),
        "non_primary_language_attributes_quarantined": (
            first_stats["source_anomaly_counts"].get(
                "explicit_word_language_outside_primary_text", 0)
            == first_stats["workbench_category_counts"].get(
                "PARSER_ANOMALY", 0)
            == len(anomaly_records)
        ),
        "gate0_word_language_census_reconciled": (
            first_stats["output_counts_by_level"]["WORD"]
            + first_stats["source_anomaly_counts"].get(
                "explicit_word_language_outside_primary_text", 0)
            == gate0_explicit_word_language_count
        ),
    }
    gate1_passed = all(acceptance_checks.values())
    acceptance = {
        "gate": "Phase 4 Gate 1",
        "status": "PASS" if gate1_passed else "FAIL",
        "contract": str(CONFIG_PATH),
        "output": str(language_spans_path),
        "checks": acceptance_checks,
        "authorization_after_gate": {
            "gate_2_token_dataset_implementation": gate1_passed,
            "protected_test_access": False,
            "training_dataset_export": False,
            "gpu_training": False,
        },
    }
    acceptance_path.write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not gate1_passed:
        raise AssertionError("Gate 1 acceptance checks did not all pass")

    level_counts = first_stats["output_counts_by_level"]
    # Hoisted out of the f-string below: a newline inside a replacement
    # field is PEP 701 (Python 3.12+) syntax and a SyntaxError on the
    # 3.11 CI runners.
    outside_primary_text = first_stats["source_anomaly_counts"].get(
        "explicit_word_language_outside_primary_text", 0)
    report = [
        "# Phase 4 Gate 1 language-layer v2 rebuild",
        "",
        "**Status: PASS — Gate 2 token-dataset implementation authorized.**",
        "",
        "This migration opened only unique archive stems mapped to frozen "
        "train, dev, or discovery. Protected test, unmatched, ambiguous, and "
        "duplicate-stem payloads remained unopened. No token training dataset "
        "or model input was produced.",
        "",
        f"- Allowed payloads opened per build: "
        f"**{sum(first_stats['payload_read_gate_counts'].values()):,}**.",
        "- Protected-test payloads opened: **0**.",
        f"- Parsed documents: **{first_stats['parsed_documents']:,}**.",
        f"- Parse-error payloads quarantined: "
        f"**{sum(first_stats['parse_errors_by_allowed_gate'].values()):,}**.",
        f"- Output rows: **{len(rows):,}** "
        f"({level_counts['DOCUMENT']:,} document, "
        f"{level_counts['LINE']:,} line, "
        f"{level_counts['WORD']:,} explicit word spans).",
        f"- Explicit word-language attributes outside the primary parser "
        f"`<text>`: **{outside_primary_text:,}**, routed "
        f"to `PARSER_ANOMALY`.",
        f"- Gate 0 explicit `w@lg` census reconciled: "
        f"**{gate0_explicit_word_language_count:,}** total.",
        f"- Logical table SHA-256: `{first_logical_hash}`.",
        f"- Frozen artifact hashes unchanged: **{frozen_unchanged}**.",
        f"- Two independent builds and persisted-table readback agree: "
        f"**{deterministic}**.",
        "",
        "## Source status accounting",
        "",
        *markdown_status_table(first_stats["status_counts_by_level"]),
        "",
        "## Workbench routing counts",
        "",
        "| category | count |",
        "|---|---:|",
    ]
    for category, count in sorted(
            first_stats["workbench_category_counts"].items()):
        report.append(f"| `{category}` | {count:,} |")
    report += [
        "",
        "The artifact preserves raw values and source checksums. Canonical "
        "values are null for missing, explicit-empty, malformed, and "
        "unrecognized source values. Explicit-empty word tags may still "
        "receive an effective line language under the named anomaly-bearing "
        "Gate 0 rule; malformed and unrecognized explicit word tags remain "
        "unresolved.",
        "",
        f"Output: `{language_spans_path}`. Manifest: `{manifest_path}`. "
        f"Acceptance record: `{acceptance_path}`. Quarantine log: "
        f"`{quarantine_path}`.",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")

    verification = [
        "# Phase 4 Gate 1 verification",
        "",
        "All Gate 1 acceptance checks passed:",
        "",
    ]
    for name, passed in acceptance_checks.items():
        verification.append(f"- `{name}`: **{passed}**")
    verification += [
        "",
        "Gate 2 implementation may now join this span artifact to the frozen "
        "decomposed token keys. Protected-test access, training-dataset "
        "export, and GPU training remain unauthorized.",
    ]
    verification_path.write_text(
        "\n".join(verification), encoding="utf-8")

    print(f"Output: {language_spans_path}")
    print(f"Report: {report_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Acceptance: {acceptance_path}")


if __name__ == "__main__":
    main()
