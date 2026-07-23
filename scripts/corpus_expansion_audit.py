#!/usr/bin/env python3
"""Split-gated TLHdig 0.2 -> 0.3 corpus expansion audit.

The zip central directories are inventoried without payload reads. XML payloads
are opened only when a unique filename stem maps to frozen train, dev, or
discovery. Test, unmatched, split-ambiguous, and duplicate-stem entries remain
unopened.

Usage:
    python scripts/corpus_expansion_audit.py
"""

import hashlib
import json
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import evidence_policy as ep
import phase2_io


CONFIG_PATH = Path("configs") / "corpus_expansion_audit.json"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"
OUT_DIR = Path("corpus_audit_out")
RESULT_PATH = OUT_DIR / "tlhdig_03_delta.json"
MANIFEST_PATH = OUT_DIR / "tlhdig_03_delta_manifest.json"
REPORT_PATH = Path("reports") / "corpus_expansion_tlhdig_03_audit.md"
CTH_RE = re.compile(r"^CTH\s*(\d+)", re.IGNORECASE)
DAMAGE_TAGS = {"del_in", "del_fin", "laes_in", "laes_fin", "gap", "space"}
JOIN_TEXT_TAGS = {"docID", "TxtPubl"}


def digest_file(path, algorithm="sha256"):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local(name):
    return name.rsplit("}", 1)[-1]


def is_junk(name):
    leaf = PurePosixPath(name).name
    return "__MACOSX" in name or leaf.startswith("._")


def cth_from_path(name):
    for part in PurePosixPath(name).parts:
        match = CTH_RE.match(part)
        if match:
            return int(match.group(1))
    return None


def archive_index(path):
    with zipfile.ZipFile(path) as archive:
        infos = list(archive.infolist())
    xml_infos = [
        info for info in infos
        if not info.is_dir()
        and info.filename.lower().endswith(".xml")
        and not is_junk(info.filename)
    ]
    by_stem = defaultdict(list)
    for info in xml_infos:
        by_stem[PurePosixPath(info.filename).stem].append(info)
    duplicates = {
        stem: entries for stem, entries in by_stem.items()
        if len(entries) != 1
    }
    extension_counts = Counter(
        PurePosixPath(info.filename).suffix.lower() or "<none>"
        for info in infos
        if not info.is_dir() and not is_junk(info.filename)
    )
    cth_counts = Counter(
        cth for info in xml_infos
        if (cth := cth_from_path(info.filename)) is not None
    )
    return {
        "infos": infos,
        "xml_infos": xml_infos,
        "by_stem": by_stem,
        "duplicates": duplicates,
        "summary": {
            "archive_bytes": Path(path).stat().st_size,
            "central_directory_entries": len(infos),
            "non_junk_xml_entries": len(xml_infos),
            "unique_filename_stems": len(by_stem),
            "duplicate_filename_stems": len(duplicates),
            "duplicate_xml_entries": sum(
                len(entries) for entries in duplicates.values()),
            "macos_junk_file_entries": sum(
                not info.is_dir() and is_junk(info.filename)
                for info in infos),
            "non_junk_extension_counts":
                dict(sorted(extension_counts.items())),
            "cth_folders": len(cth_counts),
            "cth_folder_document_counts": {
                str(key): value for key, value in sorted(cth_counts.items())
            },
        },
    }


def classify_stem(
        stem,
        split_lookup,
        split_ambiguous_ids,
        duplicate_stems,
        allowed_splits,
        prohibited_splits):
    if stem in duplicate_stems:
        return "QUARANTINE_DUPLICATE_STEM"
    if stem in split_ambiguous_ids:
        return "QUARANTINE_SPLIT_AMBIGUOUS"
    split = split_lookup.get(stem)
    if split is None:
        return "QUARANTINE_UNMATCHED"
    if split in prohibited_splits:
        return "PROTECTED_TEST"
    if split in allowed_splits:
        return f"ALLOWED_{split.upper()}"
    return "QUARANTINE_UNKNOWN_SPLIT"


def gate_counts(index, split_lookup, split_ambiguous, allowed, prohibited):
    counts = Counter()
    for stem, infos in index["by_stem"].items():
        gate = classify_stem(
            stem,
            split_lookup,
            split_ambiguous,
            index["duplicates"],
            allowed,
            prohibited,
        )
        counts[gate] += len(infos)
    return dict(sorted(counts.items()))


def scan_allowed_payloads(
        path,
        index,
        split_lookup,
        split_ambiguous,
        allowed_splits,
        prohibited_splits):
    counters = {
        "payload_read_gate_counts": Counter(),
        "parsed_documents": 0,
        "parse_error_count": 0,
        "parse_error_samples": [],
        "line_elements": 0,
        "tag_instances": Counter(),
        "tag_documents": Counter(),
        "attribute_instances": Counter(),
        "attribute_documents": Counter(),
        "root_tags": Counter(),
        "line_language_counts": Counter(),
        "damage_tag_instances": Counter(),
        "authoritative_join_documents": 0,
        "raw_sha256_by_stem": {},
        "cth_by_stem": {},
    }
    with zipfile.ZipFile(path) as archive:
        for stem, infos in sorted(index["by_stem"].items()):
            gate = classify_stem(
                stem,
                split_lookup,
                split_ambiguous,
                index["duplicates"],
                allowed_splits,
                prohibited_splits,
            )
            if not gate.startswith("ALLOWED_"):
                continue
            if len(infos) != 1:
                raise AssertionError(
                    "Corpus audit gate allowed a duplicate filename stem")
            info = infos[0]
            raw = archive.read(info)
            counters["payload_read_gate_counts"][gate] += 1
            counters["raw_sha256_by_stem"][stem] = hashlib.sha256(
                raw).hexdigest()
            counters["cth_by_stem"][stem] = cth_from_path(info.filename)
            try:
                root = ET.fromstring(raw)
            except ET.ParseError as error:
                counters["parse_error_count"] += 1
                if len(counters["parse_error_samples"]) < 25:
                    counters["parse_error_samples"].append({
                        "archive_entry_path": info.filename,
                        "error": str(error),
                    })
                continue

            counters["parsed_documents"] += 1
            counters["root_tags"][local(root.tag)] += 1
            document_tags = set()
            document_attrs = set()
            authoritative_join = False
            for element in root.iter():
                tag = local(element.tag)
                document_tags.add(tag)
                counters["tag_instances"][tag] += 1
                if tag == "lb":
                    counters["line_elements"] += 1
                    language = element.attrib.get("lg")
                    if language:
                        counters["line_language_counts"][language] += 1
                    if "+" in element.attrib.get("txtid", ""):
                        authoritative_join = True
                if tag in DAMAGE_TAGS:
                    counters["damage_tag_instances"][tag] += 1
                if (
                        tag in JOIN_TEXT_TAGS
                        and "+" in (element.text or "")):
                    authoritative_join = True
                for attribute in element.attrib:
                    key = f"{tag}@{local(attribute)}"
                    document_attrs.add(key)
                    counters["attribute_instances"][key] += 1
            counters["tag_documents"].update(document_tags)
            counters["attribute_documents"].update(document_attrs)
            counters["authoritative_join_documents"] += int(
                authoritative_join)

    forbidden_reads = [
        gate for gate in counters["payload_read_gate_counts"]
        if not gate.startswith("ALLOWED_")
    ]
    if forbidden_reads:
        raise AssertionError(
            f"Corpus audit read forbidden gates: {forbidden_reads}")
    return counters


def serialize_scan(scan):
    return {
        "payload_read_gate_counts":
            dict(sorted(scan["payload_read_gate_counts"].items())),
        "payloads_read": sum(scan["payload_read_gate_counts"].values()),
        "parsed_documents": scan["parsed_documents"],
        "parse_error_count": scan["parse_error_count"],
        "parse_error_samples": scan["parse_error_samples"],
        "line_elements": scan["line_elements"],
        "tag_instances": dict(sorted(scan["tag_instances"].items())),
        "tag_documents": dict(sorted(scan["tag_documents"].items())),
        "attribute_instances":
            dict(sorted(scan["attribute_instances"].items())),
        "attribute_documents":
            dict(sorted(scan["attribute_documents"].items())),
        "root_tags": dict(sorted(scan["root_tags"].items())),
        "line_language_counts":
            dict(sorted(scan["line_language_counts"].items())),
        "damage_tag_instances":
            dict(sorted(scan["damage_tag_instances"].items())),
        "authoritative_join_documents":
            scan["authoritative_join_documents"],
    }


def compare_allowed(baseline_scan, candidate_scan):
    common = (
        set(baseline_scan["raw_sha256_by_stem"])
        & set(candidate_scan["raw_sha256_by_stem"])
    )
    changed = {
        stem for stem in common
        if baseline_scan["raw_sha256_by_stem"][stem]
        != candidate_scan["raw_sha256_by_stem"][stem]
    }
    moved = {
        stem for stem in common
        if baseline_scan["cth_by_stem"].get(stem)
        != candidate_scan["cth_by_stem"].get(stem)
    }
    baseline_tags = set(baseline_scan["tag_instances"])
    candidate_tags = set(candidate_scan["tag_instances"])
    baseline_attrs = set(baseline_scan["attribute_instances"])
    candidate_attrs = set(candidate_scan["attribute_instances"])
    return {
        "common_allowed_unique_stems": len(common),
        "byte_identical_documents": len(common - changed),
        "byte_changed_documents": len(changed),
        "byte_changed_percent": (
            round(100 * len(changed) / len(common), 2) if common else None),
        "cth_folder_moved_documents": len(moved),
        "cth_folder_move_samples": sorted(moved)[:25],
        "tags_added_in_candidate": sorted(candidate_tags - baseline_tags),
        "tags_absent_from_candidate": sorted(baseline_tags - candidate_tags),
        "attributes_added_in_candidate":
            sorted(candidate_attrs - baseline_attrs),
        "attributes_absent_from_candidate":
            sorted(baseline_attrs - candidate_attrs),
    }


def archive_overlap(baseline_index, candidate_index):
    baseline = set(baseline_index["by_stem"])
    candidate = set(candidate_index["by_stem"])
    return {
        "shared_filename_stems": len(baseline & candidate),
        "baseline_only_filename_stems": len(baseline - candidate),
        "candidate_only_filename_stems": len(candidate - baseline),
        "baseline_only_samples": sorted(baseline - candidate)[:50],
        "candidate_only_samples": sorted(candidate - baseline)[:50],
    }


def write_report(summary, elapsed):
    baseline = summary["baseline"]
    candidate = summary["candidate"]
    delta = summary["allowed_non_test_delta"]
    overlap = summary["central_directory_overlap"]
    recommendation = summary["recommendation"]
    lines = [
        "# TLHdig 0.3 corpus expansion audit",
        "",
        f"**[{summary['report_label']}]**",
        "",
        "## Cleanroom boundary",
        "",
        f"Candidate checksum: PASS. Payload reads were limited to unique "
        f"filename stems mapped to frozen train/dev/discovery. "
        f"{candidate['gate_counts'].get('PROTECTED_TEST', 0):,} candidate "
        "test entries and "
        f"{candidate['gate_counts'].get('QUARANTINE_UNMATCHED', 0):,} "
        "unmatched candidate entries were not opened. Frozen splits, the "
        "0.2 archive, and all training artifacts were unchanged.",
        "",
        "## Central-directory findings",
        "",
        "| | TLHdig 0.2 | TLHdig 0.3 |",
        "|---|---:|---:|",
        f"| non-junk XML entries | "
        f"{baseline['inventory']['non_junk_xml_entries']:,} | "
        f"{candidate['inventory']['non_junk_xml_entries']:,} |",
        f"| unique filename stems | "
        f"{baseline['inventory']['unique_filename_stems']:,} | "
        f"{candidate['inventory']['unique_filename_stems']:,} |",
        f"| CTH folders | {baseline['inventory']['cth_folders']:,} | "
        f"{candidate['inventory']['cth_folders']:,} |",
        f"| duplicate filename stems | "
        f"{baseline['inventory']['duplicate_filename_stems']:,} | "
        f"{candidate['inventory']['duplicate_filename_stems']:,} |",
        "",
        f"Shared stems: {overlap['shared_filename_stems']:,}; candidate-only "
        f"stems: {overlap['candidate_only_filename_stems']:,}; baseline-only "
        f"stems: {overlap['baseline_only_filename_stems']:,}. Candidate-only "
        "means unmatched by filename, not yet proven new.",
        "",
        "## Split-gated non-test delta",
        "",
        f"Among {delta['common_allowed_unique_stems']:,} safely comparable "
        f"documents, {delta['byte_changed_documents']:,} "
        f"({delta['byte_changed_percent']}%) changed bytes and "
        f"{delta['byte_identical_documents']:,} were identical. Parse errors "
        f"changed from {baseline['payload_scan']['parse_error_count']:,} to "
        f"{candidate['payload_scan']['parse_error_count']:,}; parsed `<lb>` "
        f"counts changed from {baseline['payload_scan']['line_elements']:,} "
        f"to {candidate['payload_scan']['line_elements']:,}.",
        "",
        f"Schema additions: tags "
        f"`{', '.join(delta['tags_added_in_candidate']) or 'none'}`; "
        f"attributes "
        f"`{', '.join(delta['attributes_added_in_candidate']) or 'none'}`. "
        f"Tags absent from the comparable candidate set: "
        f"`{', '.join(delta['tags_absent_from_candidate']) or 'none'}`.",
        "",
        "## Recommendation",
        "",
        f"**{recommendation['decision']}** — {recommendation['reason']}",
        "",
        f"Cost: {elapsed:.1f}s compute; budget ≤"
        f"{summary['time_budget_hours']}h. No scoring or training occurred, "
        "so a content-sensitivity tracer was not applicable.",
        "",
        "**Falsifier:** this migration recommendation would be wrong if "
        "identifier resolution shows that most quarantined candidate-only "
        "entries duplicate protected or existing material, or if a full "
        "non-test parser rebuild exposes semantic schema incompatibilities "
        "not visible in this inventory.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    baseline_path = Path(config["baseline"]["path"])
    candidate_path = Path(config["candidate"]["path"])
    splits_path = Path(config["frozen_split_path"])

    checksums = {
        "baseline_md5": digest_file(baseline_path, "md5"),
        "candidate_md5": digest_file(candidate_path, "md5"),
        "candidate_sha256": digest_file(candidate_path, "sha256"),
    }
    expected = {
        "baseline_md5": config["baseline"]["expected_md5"],
        "candidate_md5": config["candidate"]["expected_md5"],
        "candidate_sha256": config["candidate"]["expected_sha256"],
    }
    if checksums != expected:
        raise AssertionError(
            f"Corpus audit checksum mismatch: {checksums} != {expected}")

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(config["evidence_policy"], POLICIES_PATH)
    control_fields = [
        "doc_id",
        "main_split",
        "archive_entry_path",
        "raw_xml_sha256",
        "parse_status",
    ]
    semantic_fields = [
        "xml_tag_name",
        "xml_attribute_name",
        "cth",
        "line_lang",
    ]
    ep.validate_fields(control_fields, registry, policy)
    ep.validate_semantic_features(semantic_fields, registry, policy)

    splits = pd.read_parquet(
        splits_path, columns=["doc_id", "main_split"])
    split_lookup, split_ambiguous = phase2_io.split_lookup_fail_closed(splits)
    allowed = set(config["payload_read_allowed_splits"])
    prohibited = set(config["payload_read_prohibited_splits"])
    if allowed & prohibited or prohibited != {"test"}:
        raise AssertionError("Corpus audit split policy is unsafe")

    baseline_index = archive_index(baseline_path)
    candidate_index = archive_index(candidate_path)
    baseline_gates = gate_counts(
        baseline_index, split_lookup, split_ambiguous, allowed, prohibited)
    candidate_gates = gate_counts(
        candidate_index, split_lookup, split_ambiguous, allowed, prohibited)

    baseline_scan = scan_allowed_payloads(
        baseline_path,
        baseline_index,
        split_lookup,
        split_ambiguous,
        allowed,
        prohibited,
    )
    candidate_scan = scan_allowed_payloads(
        candidate_path,
        candidate_index,
        split_lookup,
        split_ambiguous,
        allowed,
        prohibited,
    )
    delta = compare_allowed(baseline_scan, candidate_scan)
    overlap = archive_overlap(baseline_index, candidate_index)

    parse_errors_improved = (
        candidate_scan["parse_error_count"]
        < baseline_scan["parse_error_count"]
    )
    candidate_only = overlap["candidate_only_filename_stems"]
    if candidate_only > 0 or parse_errors_improved:
        decision = "OPEN A CONTROLLED 0.3 MIGRATION-DESIGN PASS"
        reason = (
            "0.3 contains filename-level candidate additions and/or improves "
            "non-test parseability. Do not replace 0.2 yet: first resolve "
            "quarantined identifiers, define new splits, and run a versioned "
            "parser rebuild."
        )
    else:
        decision = "KEEP 0.2 PINNED; DO NOT OPEN MIGRATION"
        reason = (
            "The split-gated audit found neither candidate additions nor "
            "non-test parseability improvement."
        )

    summary = {
        "audit": config["audit_name"],
        "report_label": config["report_label"],
        "time_budget_hours": config["time_budget_hours"],
        "evidence_policy": policy.name,
        "test_side_accessed": False,
        "test_payloads_read": 0,
        "unmatched_payloads_read": 0,
        "corpus_migration_performed": False,
        "split_change_performed": False,
        "training_performed": False,
        "checksums": checksums,
        "baseline": {
            "version": config["baseline"]["version"],
            "doi": config["baseline"]["doi"],
            "inventory": baseline_index["summary"],
            "gate_counts": baseline_gates,
            "payload_scan": serialize_scan(baseline_scan),
        },
        "candidate": {
            "version": config["candidate"]["version"],
            "doi": config["candidate"]["doi"],
            "license": config["candidate"]["license"],
            "inventory": candidate_index["summary"],
            "gate_counts": candidate_gates,
            "payload_scan": serialize_scan(candidate_scan),
        },
        "central_directory_overlap": overlap,
        "allowed_non_test_delta": delta,
        "recommendation": {
            "decision": decision,
            "reason": reason,
            "migration_authorized_by_this_audit": False,
            "next_required_step":
                "identifier resolution and versioned migration design",
        },
        "input_hashes": {
            "config": digest_file(CONFIG_PATH),
            "evidence_registry": digest_file(REGISTRY_PATH),
            "splits": digest_file(splits_path),
            "baseline_archive_sha256":
                digest_file(baseline_path, "sha256"),
            "candidate_archive_sha256": checksums["candidate_sha256"],
        },
    }

    for archive_name in ("baseline", "candidate"):
        read_gates = summary[archive_name]["payload_scan"][
            "payload_read_gate_counts"]
        if any(not gate.startswith("ALLOWED_") for gate in read_gates):
            raise AssertionError("Corpus audit read a prohibited payload gate")

    manifest = ep.build_manifest(
        task="tlhdig_02_to_03_split_gated_corpus_audit",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=candidate_path,
        split_manifest_path=splits_path,
        config_path=CONFIG_PATH,
        seed=int(config["seed"]),
        declared_statistics_universe=(
            "zip central-directory metadata for TLHdig 0.2 and 0.3; XML "
            "payload/schema statistics only for unique filename stems mapped "
            "to frozen train/dev/discovery; test, unmatched, split-ambiguous, "
            "and duplicate-stem payloads never opened"),
    )
    manifest.update({
        "control_fields_requested": control_fields,
        "control_fields_used_only_for_ingress_and_bookkeeping": True,
        "test_side_accessed": False,
        "test_payloads_read": 0,
        "unmatched_payloads_read": 0,
        "corpus_migration_performed": False,
        "split_change_performed": False,
        "training_performed": False,
        "scoring_performed": False,
        "tracer_applicable": False,
        "input_hashes": summary["input_hashes"],
        "payload_read_gate_counts": {
            "baseline": summary["baseline"]["payload_scan"][
                "payload_read_gate_counts"],
            "candidate": summary["candidate"]["payload_scan"][
                "payload_read_gate_counts"],
        },
    })

    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ep.write_manifest(manifest, MANIFEST_PATH)
    elapsed = time.perf_counter() - started
    write_report(summary, elapsed)
    print(
        "Corpus expansion audit complete: "
        f"candidate_only={candidate_only}, "
        f"changed_non_test={delta['byte_changed_documents']}, "
        f"parse_errors={baseline_scan['parse_error_count']}->"
        f"{candidate_scan['parse_error_count']}.")
    print(f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}.")


if __name__ == "__main__":
    main()
