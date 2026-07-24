#!/usr/bin/env python3
"""Metadata-first TLHdig 0.3 migration-design analysis.

This pass reconciles archive identifiers from central-directory metadata and
diagnoses only parse failures already found inside the frozen non-test gate.
It does not open test, unmatched, split-ambiguous, or duplicate-stem payloads.
It does not migrate the corpus, change splits, score candidates, or train.

Usage:
    python scripts/corpus_migration_design.py
"""

import json
import re
import sys
import time
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import corpus_expansion_audit as audit
import evidence_policy as ep
import phase2_io


CONFIG_PATH = Path("configs") / "corpus_expansion_audit.json"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"
PRIOR_AUDIT_PATH = (
    Path("corpus_audit_out") / "tlhdig_03_delta.json")
OUT_PATH = (
    Path("corpus_audit_out") / "tlhdig_03_migration_design.json")
MANIFEST_PATH = (
    Path("corpus_audit_out") / "tlhdig_03_migration_design_manifest.json")
REPORT_PATH = (
    Path("reports") / "corpus_expansion_tlhdig_03_migration_design.md")


def format_key(value):
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z]+", "", normalized)


def ascii_letter_skeleton(value):
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(
        char for char in normalized if char.isascii() and char.isalpha())


def numeric_signature(value):
    return tuple(re.findall(r"\d+", value))


def edit_distance(left, right):
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def _unique_in(index, stem):
    return len(index["by_stem"].get(stem, ())) == 1


def reconcile_identifiers(baseline_index, candidate_index):
    """Conservatively identify likely revisions without reading payloads."""
    baseline_only = (
        set(baseline_index["by_stem"])
        - set(candidate_index["by_stem"]))
    candidate_only = (
        set(candidate_index["by_stem"])
        - set(baseline_index["by_stem"]))
    matched_baseline = set()
    matched_candidate = set()
    probable = []
    ambiguous = []
    ambiguous_candidate = set()
    ambiguous_baseline = set()

    def add_probable(category, baseline, candidate):
        matched_baseline.add(baseline)
        matched_candidate.add(candidate)
        probable.append({
            "category": category,
            "baseline_stem": baseline,
            "candidate_stem": candidate,
        })

    # A trailing plus is an editorial join-status marker. Treat a unique
    # one-to-one toggle as a probable identifier revision, never as proof that
    # the underlying XML content is the same.
    for baseline in sorted(baseline_only):
        candidate = (
            baseline[:-1] if baseline.endswith("+") else baseline + "+")
        if candidate not in candidate_only:
            continue
        if (
                _unique_in(baseline_index, baseline)
                and _unique_in(candidate_index, candidate)):
            add_probable(
                "trailing_join_marker_change", baseline, candidate)
        else:
            ambiguous_baseline.add(baseline)
            ambiguous_candidate.add(candidate)
            ambiguous.append({
                "category": "revision_targets_duplicate_candidate_stem",
                "baseline_stems": [baseline],
                "candidate_stems": [candidate],
            })

    # Resolve only one-to-one punctuation/spacing differences among records
    # that were not already paired.
    baseline_keys = defaultdict(list)
    candidate_keys = defaultdict(list)
    for stem in baseline_only - matched_baseline - ambiguous_baseline:
        baseline_keys[format_key(stem)].append(stem)
    for stem in candidate_only - matched_candidate - ambiguous_candidate:
        candidate_keys[format_key(stem)].append(stem)
    for key in sorted(set(baseline_keys) & set(candidate_keys)):
        baseline_group = baseline_keys[key]
        candidate_group = candidate_keys[key]
        if len(baseline_group) != 1 or len(candidate_group) != 1:
            continue
        baseline = baseline_group[0]
        candidate = candidate_group[0]
        if (
                _unique_in(baseline_index, baseline)
                and _unique_in(candidate_index, candidate)):
            add_probable("punctuation_or_spacing_change", baseline, candidate)

    # Mojibake repair is accepted only when the old identifier contains
    # non-ASCII damage, the numeric signature is identical, ASCII letter
    # skeletons are at edit distance <= 1, and the match is bidirectionally
    # unique.
    remaining_baseline = (
        baseline_only - matched_baseline - ambiguous_baseline)
    remaining_candidate = (
        candidate_only - matched_candidate - ambiguous_candidate)
    encoding_pairs = []
    for baseline in sorted(remaining_baseline):
        if baseline.isascii():
            continue
        candidates = [
            candidate for candidate in remaining_candidate
            if numeric_signature(candidate) == numeric_signature(baseline)
            and edit_distance(
                ascii_letter_skeleton(baseline),
                ascii_letter_skeleton(candidate),
            ) <= 1
        ]
        if len(candidates) != 1:
            continue
        candidate = candidates[0]
        reverse = [
            other for other in remaining_baseline
            if not other.isascii()
            and numeric_signature(other) == numeric_signature(candidate)
            and edit_distance(
                ascii_letter_skeleton(other),
                ascii_letter_skeleton(candidate),
            ) <= 1
        ]
        if (
                len(reverse) == 1
                and _unique_in(baseline_index, baseline)
                and _unique_in(candidate_index, candidate)):
            encoding_pairs.append((baseline, candidate))
    for baseline, candidate in encoding_pairs:
        add_probable("encoding_artifact_change", baseline, candidate)

    # Long parenthetical comments were removed from two 0.2 filenames, but
    # both a bare and a plus-marked 0.3 candidate exist. Preserve the
    # one-to-many ambiguity rather than selecting one.
    for baseline in sorted(
            baseline_only - matched_baseline - ambiguous_baseline):
        core = re.sub(r"\s*\([^)]*\)\s*$", "", baseline)
        candidates = sorted({
            candidate
            for candidate in candidate_only
            - matched_candidate
            - ambiguous_candidate
            if candidate in {core, core + "+"}
        })
        if core == baseline or not candidates:
            continue
        ambiguous_baseline.add(baseline)
        ambiguous_candidate.update(candidates)
        ambiguous.append({
            "category": "annotation_suffix_removed_one_to_many",
            "baseline_stems": [baseline],
            "candidate_stems": candidates,
        })

    probable.sort(key=lambda row: (
        row["category"], row["baseline_stem"], row["candidate_stem"]))
    ambiguous.sort(key=lambda row: (
        row["category"], row["baseline_stems"], row["candidate_stems"]))
    unresolved_baseline = sorted(
        baseline_only - matched_baseline - ambiguous_baseline)
    unresolved_candidate = sorted(
        candidate_only - matched_candidate - ambiguous_candidate)
    category_counts = Counter(row["category"] for row in probable)
    return {
        "baseline_only_stems": len(baseline_only),
        "candidate_only_stems": len(candidate_only),
        "probable_revision_pairs": probable,
        "probable_revision_pair_count": len(probable),
        "probable_revision_category_counts":
            dict(sorted(category_counts.items())),
        "ambiguous_revision_groups": ambiguous,
        "ambiguous_baseline_stem_count": len(ambiguous_baseline),
        "ambiguous_candidate_stem_count": len(ambiguous_candidate),
        "unresolved_baseline_stems": unresolved_baseline,
        "unresolved_baseline_stem_count": len(unresolved_baseline),
        "unresolved_candidate_stems": unresolved_candidate,
        "unresolved_candidate_stem_count": len(unresolved_candidate),
        "payloads_read": 0,
    }


def composition_split_lookup(splits):
    grouped = splits.groupby("cth", dropna=False)["main_split"].nunique()
    if (grouped > 1).any():
        raise AssertionError(
            "Frozen split map assigns a CTH composition to multiple splits")
    return dict(
        splits[["cth", "main_split"]]
        .drop_duplicates()
        .itertuples(index=False, name=None))


def prospective_split(stem, candidate_index, cth_splits):
    split_values = {
        cth_splits.get(
            audit.cth_from_path(info.filename),
            "unknown_cth",
        )
        for info in candidate_index["by_stem"][stem]
    }
    if len(split_values) == 1:
        return next(iter(split_values))
    return "mixed_split_or_cth"


def series_prefix(stem):
    match = re.match(r"([^0-9]+)", stem)
    return match.group(1).strip() if match else "<numeric>"


def characterize_unresolved_candidates(
        unresolved_stems, candidate_index, cth_splits):
    stem_split_counts = Counter()
    entry_split_counts = Counter()
    series_counts = Counter()
    series_split_counts = Counter()
    for stem in unresolved_stems:
        split = prospective_split(stem, candidate_index, cth_splits)
        stem_split_counts[split] += 1
        entry_split_counts[split] += len(candidate_index["by_stem"][stem])
        series = series_prefix(stem)
        series_counts[series] += 1
        series_split_counts[(series, split)] += 1

    total = len(unresolved_stems)
    discovery = stem_split_counts["discovery"]
    known_non_test_real = (
        stem_split_counts["train"] + stem_split_counts["dev"])
    top_series = []
    for series, count in series_counts.most_common(12):
        top_series.append({
            "series": series,
            "stems": count,
            "prospective_split_counts": {
                split: series_split_counts[(series, split)]
                for split in sorted({
                    key_split
                    for key_series, key_split in series_split_counts
                    if key_series == series
                })
            },
        })
    return {
        "unresolved_candidate_stems": total,
        "stem_counts_by_prospective_cth_split":
            dict(sorted(stem_split_counts.items())),
        "entry_counts_by_prospective_cth_split":
            dict(sorted(entry_split_counts.items())),
        "discovery_bin_stems": discovery,
        "discovery_bin_percent": (
            round(100 * discovery / total, 2) if total else None),
        "known_train_stem_upper_bound": stem_split_counts["train"],
        "known_dev_stem_upper_bound": stem_split_counts["dev"],
        "known_non_test_real_composition_upper_bound":
            known_non_test_real,
        "protected_test_stems": stem_split_counts["test"],
        "top_series": top_series,
        "interpretation": (
            "Counts are filename/CTH-path metadata only. They are upper "
            "bounds, not verified usable documents; unresolved payloads "
            "were not opened."),
    }


def duplicate_topology(index, cth_splits):
    topology_counts = Counter()
    split_signature_counts = Counter()
    test_involving = 0
    for infos in index["duplicates"].values():
        cths = {
            audit.cth_from_path(info.filename) for info in infos}
        splits = {
            cth_splits.get(cth, "unknown_cth") for cth in cths}
        if len(cths) == 1:
            topology = "same_cth"
        elif len(splits) == 1:
            topology = "cross_cth_same_split"
        else:
            topology = "cross_split_or_unknown"
        topology_counts[topology] += 1
        signature = " + ".join(sorted(splits))
        split_signature_counts[signature] += 1
        test_involving += int("test" in splits)
    return {
        "duplicate_filename_stems": len(index["duplicates"]),
        "topology_counts": dict(sorted(topology_counts.items())),
        "split_signature_counts":
            dict(sorted(split_signature_counts.items())),
        "test_involving_duplicate_stems": test_involving,
        "payloads_read": 0,
        "migration_rule": (
            "Canonicalize duplicate identifiers before splitting; all archive "
            "entries sharing an identifier must remain quarantined until "
            "their catalog relation is adjudicated."),
    }


def _inside_quoted_attribute(line, offset):
    quote = None
    for char in line[:offset]:
        if quote is None and char in {'"', "'"}:
            quote = char
        elif char == quote:
            quote = None
    return quote is not None


def classify_parse_failure(raw, error):
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    line_number, column = error.position
    line = lines[line_number - 1] if 0 < line_number <= len(lines) else ""
    message = str(error)

    if "<AO:-LineNrExpl" in line:
        return {
            "category": "invalid_qname_ao_dash_linenr",
            "structural_detail": {
                "invalid_element_occurrences":
                    text.count("<AO:-LineNrExpl"),
            },
        }
    if (
            "invalid token" in message
            and column < len(line)
            and line[column:column + 2] == "</"
            and _inside_quoted_attribute(line, column)):
        return {
            "category": "unescaped_markup_inside_attribute",
            "structural_detail": {
                "token_kind": "closing_element_markup",
            },
        }
    if (
            "<AO:TxtPubl>" in line
            and "</TxtPubl>" in line):
        return {
            "category": "namespace_prefix_mismatch",
            "structural_detail": {
                "opening_name": "AO:TxtPubl",
                "closing_name": "TxtPubl",
            },
        }
    if (
            "mismatched tag" in message
            and line.count("<sGr>") > line.count("</sGr>")
            and "</w>" in line):
        return {
            "category": "unclosed_inline_element_before_word_close",
            "structural_detail": {
                "unclosed_element": "sGr",
            },
        }
    unclosed_damage_words = 0
    marker = "<w><del_in/><del_fin/>"
    for match in re.finditer(re.escape(marker), text):
        following_boundaries = [
            offset for offset in (
                text.find("<lb", match.end()),
                text.find("</text>", match.end()),
            )
            if offset >= 0
        ]
        if not following_boundaries:
            continue
        boundary = min(following_boundaries)
        if "</w>" not in text[match.end():boundary]:
            unclosed_damage_words += 1
    if (
            "mismatched tag" in message
            and unclosed_damage_words > 0):
        return {
            "category": "unclosed_empty_damage_word_at_line_boundary",
            "structural_detail": {
                "unclosed_word_occurrences": unclosed_damage_words,
            },
        }
    return {
        "category": "unclassified_parse_failure",
        "structural_detail": {},
    }


def diagnose_allowed_parse_errors(
        archive_path,
        index,
        requested_stems,
        split_lookup,
        split_ambiguous,
        allowed_splits,
        prohibited_splits):
    diagnostics = []
    read_gates = Counter()
    skipped_gates = Counter()
    with zipfile.ZipFile(archive_path) as archive:
        for stem in sorted(requested_stems):
            infos = index["by_stem"].get(stem, ())
            gate = audit.classify_stem(
                stem,
                split_lookup,
                split_ambiguous,
                index["duplicates"],
                allowed_splits,
                prohibited_splits,
            )
            if not gate.startswith("ALLOWED_"):
                skipped_gates[gate] += len(infos) or 1
                continue
            if len(infos) != 1:
                raise AssertionError(
                    "Parser diagnostics allowed a duplicate filename stem")
            raw = archive.read(infos[0])
            read_gates[gate] += 1
            try:
                ET.fromstring(raw)
            except ET.ParseError as error:
                classification = classify_parse_failure(raw, error)
                diagnostics.append({
                    "stem": stem,
                    "gate": gate,
                    "error": str(error),
                    **classification,
                })
            else:
                diagnostics.append({
                    "stem": stem,
                    "gate": gate,
                    "error": None,
                    "category": "no_longer_reproduces",
                    "structural_detail": {},
                })
    if any(not gate.startswith("ALLOWED_") for gate in read_gates):
        raise AssertionError("Parser diagnostics read a prohibited payload")
    return {
        "diagnostics": diagnostics,
        "category_counts": dict(sorted(Counter(
            row["category"] for row in diagnostics).items())),
        "payload_read_gate_counts": dict(sorted(read_gates.items())),
        "payloads_read": sum(read_gates.values()),
        "skipped_without_payload_read":
            dict(sorted(skipped_gates.items())),
    }


def write_report(result, elapsed):
    reconciliation = result["identifier_reconciliation"]
    additions = result["unresolved_candidate_characterization"]
    duplicates = result["candidate_duplicate_topology"]
    parser = result["parser_diagnostics"]
    split_counts = additions["stem_counts_by_prospective_cth_split"]
    category_counts = parser["category_counts"]
    lines = [
        "# TLHdig 0.3 migration-design findings",
        "",
        "**[AUDIT — no corpus migration, split change, scoring, or training]**",
        "",
        "## Decision",
        "",
        "**KEEP TLHdig 0.2 PINNED; PREPARE A VERSIONED 0.3 INGESTION "
        "PROTOTYPE, NOT A DIRECT REPLACEMENT.** The expansion is material, "
        "but most candidate additions are discovery-bin records and 0.3 "
        "contains identifier collisions that cross frozen split classes.",
        "",
        "## Identifier reconciliation",
        "",
        f"Of {reconciliation['candidate_only_stems']:,} candidate-only "
        f"filename stems, {reconciliation['probable_revision_pair_count']:,} "
        "are conservative one-to-one identifier revisions and "
        f"{reconciliation['ambiguous_candidate_stem_count']:,} more belong "
        "to unresolved revision groups. "
        f"{reconciliation['unresolved_candidate_stem_count']:,} remain "
        "plausible additions. No payload was opened for this reconciliation.",
        "",
        "Probable revisions: "
        f"{reconciliation['probable_revision_category_counts']}. These are "
        "identity hypotheses from filenames, not content equivalence claims.",
        "",
        "## Where the plausible additions fall",
        "",
        f"Prospective CTH-folder split counts: `{split_counts}`. "
        f"{additions['discovery_bin_stems']:,} "
        f"({additions['discovery_bin_percent']}%) fall in discovery bins and "
        "cannot become supervised labels under the standing bin rule. The "
        "upper bound in known real non-test compositions is "
        f"{additions['known_non_test_real_composition_upper_bound']:,} stems "
        f"({additions['known_train_stem_upper_bound']:,} train; "
        f"{additions['known_dev_stem_upper_bound']:,} dev), while "
        f"{additions['protected_test_stems']:,} map prospectively to protected "
        "test compositions and remain unopened.",
        "",
        "The largest unresolved series are: "
        + ", ".join(
            f"{row['series']} ({row['stems']:,})"
            for row in additions["top_series"][:6])
        + ".",
        "",
        "## Duplicate-identifier barrier",
        "",
        f"TLHdig 0.3 has {duplicates['duplicate_filename_stems']:,} duplicate "
        "filename stems. "
        f"{duplicates['topology_counts'].get('cross_split_or_unknown', 0):,} "
        "span multiple frozen split classes or an unknown CTH, and "
        f"{duplicates['test_involving_duplicate_stems']:,} involve a test "
        "composition. A migration must canonicalize identifier groups before "
        "creating a new versioned split; naïve folder inheritance would risk "
        "leakage.",
        "",
        "## XML regression diagnosis",
        "",
        f"All {parser['payloads_read']:,} reads were unique allowed non-test "
        "parse failures. Test, unmatched, and duplicate-stem payload reads "
        "remained zero. Root causes: "
        f"`{category_counts}`.",
        "",
        "Eight failures use the invalid QName `AO:-LineNrExpl`; the others "
        "are an unescaped closing tag inside an attribute, an unclosed `sGr`, "
        "a namespace-prefix mismatch, and seven unclosed empty-damage word "
        "elements in the one persistent 0.2/0.3 failure. Do not use a "
        "permissive recovery parser: apply checksum-guarded, document-specific "
        "repairs or obtain corrected upstream XML so damage-state order cannot "
        "be silently altered.",
        "",
        "## Next gate",
        "",
        "Build a separate 0.3 ingestion prototype that (1) constructs "
        "canonical identifier groups, (2) quarantines every cross-CTH group, "
        "(3) applies reviewed checksum-guarded XML repairs, and (4) reports "
        "how many of the 281 prospective train additions are actually "
        "parseable and Hittite-bearing. Do not touch the current 0.2 datasets "
        "or frozen splits during that prototype.",
        "",
        f"Cost: {elapsed:.1f}s; no model/content-sensitivity tracer was "
        "applicable.",
        "",
        "Corpus sources: Müller, Prechel, Rieken & Schwemer, TLHdig Beta "
        "0.2.0, DOI 10.5281/zenodo.15459134 (CC BY 4.0); TLHdig Beta 0.3, "
        "DOI 10.5281/zenodo.20328284 (CC BY 4.0).",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR_AUDIT_PATH.read_text(encoding="utf-8"))
    baseline_path = Path(config["baseline"]["path"])
    candidate_path = Path(config["candidate"]["path"])
    splits_path = Path(config["frozen_split_path"])

    if audit.digest_file(
            candidate_path, "md5") != config["candidate"]["expected_md5"]:
        raise AssertionError("TLHdig 0.3 checksum mismatch")
    if prior["test_payloads_read"] != 0 or prior["unmatched_payloads_read"] != 0:
        raise AssertionError("Prior audit violated the cleanroom boundary")

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(config["evidence_policy"], POLICIES_PATH)
    control_fields = [
        "doc_id",
        "main_split",
        "archive_entry_path",
        "parse_status",
    ]
    semantic_fields = ["cth", "xml_tag_name", "xml_attribute_name"]
    ep.validate_fields(control_fields, registry, policy)
    ep.validate_semantic_features(semantic_fields, registry, policy)

    splits = pd.read_parquet(
        splits_path, columns=["doc_id", "cth", "main_split"])
    split_lookup, split_ambiguous = phase2_io.split_lookup_fail_closed(
        splits[["doc_id", "main_split"]])
    cth_splits = composition_split_lookup(splits)
    allowed = set(config["payload_read_allowed_splits"])
    prohibited = set(config["payload_read_prohibited_splits"])
    if allowed & prohibited or prohibited != {"test"}:
        raise AssertionError("Migration-design split policy is unsafe")

    baseline_index = audit.archive_index(baseline_path)
    candidate_index = audit.archive_index(candidate_path)
    reconciliation = reconcile_identifiers(
        baseline_index, candidate_index)
    additions = characterize_unresolved_candidates(
        reconciliation["unresolved_candidate_stems"],
        candidate_index,
        cth_splits,
    )
    baseline_duplicates = duplicate_topology(
        baseline_index, cth_splits)
    candidate_duplicates = duplicate_topology(
        candidate_index, cth_splits)
    requested_errors = prior["candidate"]["payload_scan"][
        "parse_error_stems"]
    parser_diagnostics = diagnose_allowed_parse_errors(
        candidate_path,
        candidate_index,
        requested_errors,
        split_lookup,
        split_ambiguous,
        allowed,
        prohibited,
    )
    if parser_diagnostics["payloads_read"] != len(requested_errors):
        raise AssertionError(
            "Not every prior allowed parse failure was safely re-diagnosed")
    if (
            parser_diagnostics["category_counts"].get(
                "unclassified_parse_failure", 0)
            or parser_diagnostics["category_counts"].get(
                "no_longer_reproduces", 0)):
        raise AssertionError("Parser diagnostic taxonomy is incomplete")

    result = {
        "audit": "TLHdig 0.3 identifier and parser migration design",
        "report_label":
            "AUDIT — not a corpus migration or citable model result",
        "evidence_policy": policy.name,
        "test_side_accessed": False,
        "test_payloads_read": 0,
        "unmatched_payloads_read": 0,
        "duplicate_stem_payloads_read": 0,
        "corpus_migration_performed": False,
        "split_change_performed": False,
        "training_performed": False,
        "scoring_performed": False,
        "identifier_reconciliation": reconciliation,
        "unresolved_candidate_characterization": additions,
        "baseline_duplicate_topology": baseline_duplicates,
        "candidate_duplicate_topology": candidate_duplicates,
        "parser_diagnostics": parser_diagnostics,
        "recommendation": {
            "decision": (
                "KEEP 0.2 PINNED; BUILD A SEPARATE VERSIONED 0.3 "
                "INGESTION PROTOTYPE"),
            "direct_replacement_authorized": False,
            "external_corpus_ingestion_authorized": False,
            "next_gate": (
                "canonical identifier groups plus checksum-guarded XML "
                "repair registry, then parseability/language inventory of "
                "prospective non-test additions"),
        },
        "input_hashes": {
            "config": audit.digest_file(CONFIG_PATH),
            "prior_audit": audit.digest_file(PRIOR_AUDIT_PATH),
            "splits": audit.digest_file(splits_path),
            "baseline_archive_sha256":
                audit.digest_file(baseline_path),
            "candidate_archive_sha256":
                audit.digest_file(candidate_path),
        },
    }

    manifest = ep.build_manifest(
        task="tlhdig_03_identifier_and_parser_migration_design",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=candidate_path,
        split_manifest_path=splits_path,
        config_path=CONFIG_PATH,
        seed=int(config["seed"]),
        corpus_version="TLHdig 0.2.0-beta vs 0.3-beta",
        declared_statistics_universe=(
            "zip central-directory metadata for all non-junk XML entries; "
            "payload diagnostics only for the 12 unique train/dev/discovery "
            "parse failures recorded by the prior split-gated audit; test, "
            "unmatched, split-ambiguous, and duplicate-stem payloads never "
            "opened"),
    )
    manifest.update({
        "control_fields_requested": control_fields,
        "control_fields_used_only_for_ingress_and_bookkeeping": True,
        "test_side_accessed": False,
        "test_payloads_read": 0,
        "unmatched_payloads_read": 0,
        "duplicate_stem_payloads_read": 0,
        "corpus_migration_performed": False,
        "split_change_performed": False,
        "training_performed": False,
        "scoring_performed": False,
        "tracer_applicable": False,
        "input_hashes": result["input_hashes"],
        "payload_read_gate_counts":
            parser_diagnostics["payload_read_gate_counts"],
    })

    OUT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ep.write_manifest(manifest, MANIFEST_PATH)
    elapsed = time.perf_counter() - started
    write_report(result, elapsed)
    print(
        "TLHdig 0.3 migration-design audit complete: "
        f"probable_revisions="
        f"{reconciliation['probable_revision_pair_count']}, "
        f"plausible_additions="
        f"{reconciliation['unresolved_candidate_stem_count']}, "
        f"cross_split_duplicates="
        f"{candidate_duplicates['topology_counts'].get('cross_split_or_unknown', 0)}, "
        f"parse_failures={parser_diagnostics['payloads_read']}.")
    print(f"Wrote {OUT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}.")


if __name__ == "__main__":
    main()
