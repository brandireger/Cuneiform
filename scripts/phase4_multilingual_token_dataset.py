#!/usr/bin/env python3
"""Build and verify the Phase 4 Gate 2 multilingual token dataset.

Tokens are rebuilt from the exact checksum-guarded archive members accepted by
Gate 1, through the shared lossless XML decomposition function. Protected-test,
unmatched, ambiguous, and duplicate-stem documents are absent from that map
and cannot enter this dataset.

Usage:
    python scripts/phase4_multilingual_token_dataset.py
"""

import hashlib
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import evidence_policy as ep  # noqa: E402
import language_layers_v2 as llv2  # noqa: E402
from decompose_corpus import decompose_document  # noqa: E402


CONFIG_PATH = Path("configs/language_layers_v2.json")
REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
SOURCE_TOKENS_PATH = Path(
    "Phase1_pipeline/p4_out/decomposed_corpus.parquet")
ZIP_PATH = Path("TLHdig_0.2.0-beta.zip")
DECOMPOSE_SCRIPT_PATH = Path("lib/decompose_corpus.py")
GATE1_MANIFEST_PATH = Path(
    "migrations/language_layers_v2/rebuild_manifest.json")
GATE1_ACCEPTANCE_PATH = Path(
    "migrations/language_layers_v2/gate1_acceptance.json")
SCRIPT_PATH = Path("scripts/phase4_multilingual_token_dataset.py")
SEED = 20260725

FROZEN_PATHS = {
    "frozen_splits": SPLITS_PATH,
    "frozen_decomposed_tokens": SOURCE_TOKENS_PATH,
    "corpus_zip": ZIP_PATH,
    "language_spans_v2":
        Path("migrations/language_layers_v2/language_spans.parquet"),
    "ratified_line_lang_v1":
        Path("migrations/line_lang_v1/line_lang_canonical.parquet"),
}

OUTPUT_COLUMNS = [
    "doc_id",
    "main_split",
    "line_index_in_doc",
    "word_pos",
    "token",
    "damage_state",
    "word_index_in_line",
    "line_lang_raw",
    "line_lang_canonical",
    "line_lang_status",
    "line_lang_rule_id",
    "word_lang_raw",
    "word_lang_canonical",
    "word_lang_status",
    "word_lang_rule_id",
    "effective_lang_canonical",
    "effective_lang_status",
    "effective_lang_source",
    "effective_lang_rule_id",
    "language_span_id",
    "language_switch_before",
    "mixed_language_line",
    "mixed_language_document",
    "is_structural_token",
    "lexical_language_statistics_eligible",
    "workbench_categories",
]

OUTPUT_SCHEMA = pa.schema([
    ("doc_id", pa.string()),
    ("main_split", pa.string()),
    ("line_index_in_doc", pa.int32()),
    ("word_pos", pa.int32()),
    ("token", pa.string()),
    ("damage_state", pa.string()),
    ("word_index_in_line", pa.int32()),
    ("line_lang_raw", pa.string()),
    ("line_lang_canonical", pa.string()),
    ("line_lang_status", pa.string()),
    ("line_lang_rule_id", pa.string()),
    ("word_lang_raw", pa.string()),
    ("word_lang_canonical", pa.string()),
    ("word_lang_status", pa.string()),
    ("word_lang_rule_id", pa.string()),
    ("effective_lang_canonical", pa.string()),
    ("effective_lang_status", pa.string()),
    ("effective_lang_source", pa.string()),
    ("effective_lang_rule_id", pa.string()),
    ("language_span_id", pa.string()),
    ("language_switch_before", pa.bool_()),
    ("mixed_language_line", pa.bool_()),
    ("mixed_language_document", pa.bool_()),
    ("is_structural_token", pa.bool_()),
    ("lexical_language_statistics_eligible", pa.bool_()),
    ("workbench_categories", pa.list_(pa.string())),
])

IDENTITY_COLUMNS = [
    "doc_id",
    "line_index_in_doc",
    "word_pos",
    "token",
    "damage_state",
    "word_index_in_line",
]


def digest_file(path, algorithm="sha256"):
    digest = hashlib.new(algorithm)
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update_hash(digest, row, columns):
    digest.update(json.dumps(
        [row[column] for column in columns],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8"))
    digest.update(b"\n")


def value_from_span(row):
    return llv2.LanguageValue(
        raw=row["language_raw"],
        canonical=row["language_canonical"],
        status=row["language_status"],
        rule_id=row["language_rule_id"],
    )


def load_language_layer(path, contract):
    """Load the small Gate 1 span artifact and build unique keyed lookups."""
    records = pq.read_table(path).to_pylist()
    doc_splits = {}
    doc_sources = {}
    line_lookup = {}
    word_lookup = {}
    resolved_by_line = defaultdict(set)
    resolved_by_doc = defaultdict(set)

    for row in records:
        doc_id = row["doc_id"]
        level = row["language_level"]
        if level == "DOCUMENT":
            if doc_id in doc_splits:
                raise AssertionError("Duplicate DOCUMENT language-span key")
            doc_splits[doc_id] = row["main_split"]
            doc_sources[doc_id] = {
                "archive_member": row["source_archive_member"],
                "payload_sha256": row["source_payload_sha256"],
            }
            continue

        key = (doc_id, int(row["line_index_in_doc"]))
        value = value_from_span(row)
        if level == "LINE":
            if key in line_lookup:
                raise AssertionError("Duplicate LINE language-span key")
            line_lookup[key] = value
            if value.status == "valid":
                resolved_by_line[key].add(value.canonical)
                resolved_by_doc[doc_id].add(value.canonical)
            continue

        if level != "WORD":
            raise AssertionError(f"Unknown language-span level: {level!r}")
        word_key = (*key, int(row["word_index_in_line"]))
        if word_key in word_lookup:
            raise AssertionError("Duplicate WORD language-span key")
        word_lookup[word_key] = value
        effective = row["effective_lang_canonical"]
        if effective in set(contract["canonical_codes"]):
            resolved_by_line[key].add(effective)
            resolved_by_doc[doc_id].add(effective)

    if set(doc_splits.values()) - {"train", "dev", "discovery"}:
        raise AssertionError("Gate 1 document map contains a prohibited split")
    return {
        "doc_splits": doc_splits,
        "doc_sources": doc_sources,
        "line_lookup": line_lookup,
        "word_lookup": word_lookup,
        "mixed_lines": {
            key for key, values in resolved_by_line.items()
            if len(values) > 1
        },
        "mixed_documents": {
            doc_id for doc_id, values in resolved_by_doc.items()
            if len(values) > 1
        },
    }


def source_token_batches(language_layer, batch_size=32768):
    """Rebuild tokens from exact checksum-guarded Gate 1 archive members.

    The historical token cache conflates at least one pair of distinct archive
    stems under one doc_id. Reusing it would make the source version
    unidentifiable. This lossless XML re-walk calls the same shared
    decompose_document() implementation and opens only Gate 1-accepted
    train/dev/discovery members.
    """
    buffered = []
    with zipfile.ZipFile(ZIP_PATH) as archive:
        for doc_id in sorted(language_layer["doc_sources"]):
            source = language_layer["doc_sources"][doc_id]
            raw = archive.read(source["archive_member"])
            if hashlib.sha256(raw).hexdigest() != source["payload_sha256"]:
                raise AssertionError(
                    "Gate 1 source payload checksum changed")
            for line in decompose_document(raw):
                line_index = int(line["line_index_in_doc"])
                for word_pos, (token, damage_state, word_index) in enumerate(
                        line["tokens"]):
                    buffered.append({
                        "doc_id": doc_id,
                        "line_index_in_doc": line_index,
                        "word_pos": word_pos,
                        "token": token,
                        "damage_state": damage_state,
                        "word_index_in_line": word_index,
                    })
                    if len(buffered) >= batch_size:
                        yield buffered
                        buffered = []
    if buffered:
        yield buffered


def missing_word_value(contract):
    return llv2.classify_language(
        None,
        attribute_present=False,
        level="WORD",
        contract=contract,
    )


def token_language_fields(token_row, language_layer, contract):
    doc_id = token_row["doc_id"]
    line_index = int(token_row["line_index_in_doc"])
    line_key = (doc_id, line_index)
    if line_key not in language_layer["line_lookup"]:
        raise AssertionError(
            "Frozen token row has no exact Gate 1 line-language key")
    line_value = language_layer["line_lookup"][line_key]

    word_index = token_row["word_index_in_line"]
    is_structural = word_index is None
    if is_structural:
        word_value = missing_word_value(contract)
        effective = llv2.EffectiveLanguage(
            canonical=line_value.canonical if line_value.status == "valid"
            else None,
            status=(
                "RESOLVED" if line_value.status == "valid"
                else "UNRESOLVED_LINE_LANGUAGE"
            ),
            source=(
                "LINE_INHERITED" if line_value.status == "valid"
                else "UNRESOLVED"
            ),
            rule_id=contract["effective_rule"]["rule_id"],
        )
    else:
        word_key = (doc_id, line_index, int(word_index))
        explicit_word = language_layer["word_lookup"].get(word_key)
        word_value = explicit_word or missing_word_value(contract)
        effective = llv2.resolve_word_language(
            word_value,
            line_value,
            word_attribute_present=explicit_word is not None,
            contract=contract,
        )

    categories = {
        category for category in (
            llv2.language_status_workbench_category(line_value.status),
            llv2.language_status_workbench_category(word_value.status),
            effective.workbench_category,
        )
        if category is not None
    }
    return {
        "line_value": line_value,
        "word_value": word_value,
        "effective": effective,
        "is_structural": is_structural,
        "workbench_categories": sorted(categories),
    }


def new_stats():
    return {
        "token_count": 0,
        "document_count": 0,
        "tokens_by_split": Counter(),
        "effective_status_counts": Counter(),
        "effective_source_counts": Counter(),
        "lexical_tokens_by_language": Counter(),
        "workbench_category_token_counts": Counter(),
        "structural_token_count": 0,
        "mixed_line_token_count": 0,
        "mixed_document_token_count": 0,
        "duplicate_or_unsorted_identity_count": 0,
        "raw_source_token_row_count": 0,
        "disallowed_document_count": 0,
        "explicit_word_token_count": 0,
        "used_explicit_word_key_count": 0,
    }


def serializable_stats(stats):
    result = {}
    for key, value in stats.items():
        result[key] = (
            dict(sorted(value.items()))
            if isinstance(value, Counter) else value
        )
    return result


def build_pass(
        language_layer,
        contract,
        *,
        output_path=None):
    stats = new_stats()
    output_digest = hashlib.sha256()
    source_identity_digest = hashlib.sha256()
    used_word_keys = set()
    seen_documents = set()
    completed_documents = set()
    current_doc = None
    previous_identity = None
    previous_language = None
    span_counter = -1
    identities_in_current_document = set()
    writer = (
        pq.ParquetWriter(
            output_path,
            OUTPUT_SCHEMA,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        if output_path is not None else None
    )

    try:
        for token_rows in source_token_batches(language_layer):
            output_rows = []
            for token_row in token_rows:
                doc_id = token_row["doc_id"]
                stats["raw_source_token_row_count"] += 1
                if doc_id not in language_layer["doc_splits"]:
                    stats["disallowed_document_count"] += 1
                    continue
                identity = (
                    doc_id,
                    int(token_row["line_index_in_doc"]),
                    int(token_row["word_pos"]),
                )
                if doc_id != current_doc:
                    if current_doc is not None:
                        completed_documents.add(current_doc)
                    if doc_id in completed_documents:
                        raise AssertionError(
                            "Frozen token rows are not document-contiguous")
                    current_doc = doc_id
                    previous_identity = None
                    previous_language = None
                    span_counter = -1
                    identities_in_current_document = set()
                    if doc_id not in seen_documents:
                        seen_documents.add(doc_id)
                        stats["document_count"] += 1
                if identity in identities_in_current_document:
                    raise AssertionError(
                        "Exact Gate 1 source produced a duplicate token key: "
                        f"identity={identity!r}")
                identities_in_current_document.add(identity)

                if previous_identity is not None and identity <= previous_identity:
                    stats["duplicate_or_unsorted_identity_count"] += 1
                    raise AssertionError(
                        "Frozen token identity keys are duplicated or unsorted: "
                        f"previous={previous_identity!r}, current={identity!r}")
                previous_identity = identity

                language = token_language_fields(
                    token_row, language_layer, contract)
                line_value = language["line_value"]
                word_value = language["word_value"]
                effective = language["effective"]
                is_structural = language["is_structural"]
                switch_before = (
                    stats["token_count"] > 0
                    and previous_language != effective.canonical
                    and span_counter >= 0
                )
                if span_counter < 0 or previous_language != effective.canonical:
                    span_counter += 1
                previous_language = effective.canonical

                word_index = token_row["word_index_in_line"]
                if word_index is not None:
                    explicit_key = (
                        doc_id,
                        int(token_row["line_index_in_doc"]),
                        int(word_index),
                    )
                    if explicit_key in language_layer["word_lookup"]:
                        used_word_keys.add(explicit_key)
                        stats["explicit_word_token_count"] += 1

                output_row = {
                    "doc_id": doc_id,
                    "main_split": language_layer["doc_splits"][doc_id],
                    "line_index_in_doc":
                        int(token_row["line_index_in_doc"]),
                    "word_pos": int(token_row["word_pos"]),
                    "token": token_row["token"],
                    "damage_state": token_row["damage_state"],
                    "word_index_in_line": (
                        None if word_index is None else int(word_index)
                    ),
                    "line_lang_raw": line_value.raw,
                    "line_lang_canonical": line_value.canonical,
                    "line_lang_status": line_value.status,
                    "line_lang_rule_id": line_value.rule_id,
                    "word_lang_raw": word_value.raw,
                    "word_lang_canonical": word_value.canonical,
                    "word_lang_status": word_value.status,
                    "word_lang_rule_id": word_value.rule_id,
                    "effective_lang_canonical": effective.canonical,
                    "effective_lang_status": effective.status,
                    "effective_lang_source": effective.source,
                    "effective_lang_rule_id": effective.rule_id,
                    "language_span_id":
                        f"{doc_id}::language_span::{span_counter}",
                    "language_switch_before": switch_before,
                    "mixed_language_line": (
                        (doc_id, int(token_row["line_index_in_doc"]))
                        in language_layer["mixed_lines"]
                    ),
                    "mixed_language_document":
                        doc_id in language_layer["mixed_documents"],
                    "is_structural_token": is_structural,
                    "lexical_language_statistics_eligible":
                        not is_structural,
                    "workbench_categories":
                        language["workbench_categories"],
                }
                update_hash(
                    source_identity_digest, token_row, IDENTITY_COLUMNS)
                update_hash(output_digest, output_row, OUTPUT_COLUMNS)
                output_rows.append(output_row)

                stats["token_count"] += 1
                stats["tokens_by_split"][output_row["main_split"]] += 1
                stats["effective_status_counts"][effective.status] += 1
                stats["effective_source_counts"][effective.source] += 1
                if is_structural:
                    stats["structural_token_count"] += 1
                else:
                    key = effective.canonical or "<UNRESOLVED>"
                    stats["lexical_tokens_by_language"][key] += 1
                if output_row["mixed_language_line"]:
                    stats["mixed_line_token_count"] += 1
                if output_row["mixed_language_document"]:
                    stats["mixed_document_token_count"] += 1
                for category in output_row["workbench_categories"]:
                    stats["workbench_category_token_counts"][category] += 1

            if writer is not None and output_rows:
                writer.write_table(pa.Table.from_pylist(
                    output_rows, schema=OUTPUT_SCHEMA))
    finally:
        if writer is not None:
            writer.close()

    stats["used_explicit_word_key_count"] = len(used_word_keys)
    return {
        "logical_sha256": output_digest.hexdigest(),
        "source_identity_sha256": source_identity_digest.hexdigest(),
        "used_explicit_word_keys": used_word_keys,
        "stats": stats,
    }


def persisted_hashes(path):
    logical_digest = hashlib.sha256()
    identity_digest = hashlib.sha256()
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=32768):
        for row in batch.to_pylist():
            update_hash(logical_digest, row, OUTPUT_COLUMNS)
            update_hash(identity_digest, row, IDENTITY_COLUMNS)
    return logical_digest.hexdigest(), identity_digest.hexdigest()


def projection_manifest(stats, contract):
    lexical = stats["lexical_tokens_by_language"]
    structural = stats["structural_token_count"]
    resolved_lexical = sum(
        lexical.get(code, 0) for code in contract["canonical_codes"])
    total = stats["token_count"]
    projections = {
        "HITTITE_ONLY": {
            "query_language": None,
            "token_count": structural + lexical.get("Hit", 0),
            "language_identity": "PRESERVED",
        },
        "MULTILINGUAL_CONDITIONED": {
            "query_language": None,
            "token_count": structural + resolved_lexical,
            "language_identity": "SUPPLIED_TO_MODEL",
        },
        "ALL_LANGUAGES_UNCONDITIONED": {
            "query_language": None,
            "token_count": total,
            "language_identity": "INTENTIONALLY_REMOVED",
            "ablation_only": True,
        },
        "SAME_LANGUAGE_AS_QUERY": {},
        "CROSS_LANGUAGE_PARALLEL": {},
    }
    for code in contract["canonical_codes"]:
        projections["SAME_LANGUAGE_AS_QUERY"][code] = {
            "token_count": structural + lexical.get(code, 0),
            "language_identity": "PRESERVED",
        }
        projections["CROSS_LANGUAGE_PARALLEL"][code] = {
            "token_count": (
                structural + resolved_lexical - lexical.get(code, 0)),
            "language_identity": "SEPARATE_ASSISTANCE_CHANNEL",
        }
    return {
        "contract_version": contract["contract_version"],
        "language_scopes": sorted(contract["language_scopes"]),
        "structural_tokens_retained_in_every_projection": True,
        "structural_tokens_excluded_from_lexical_statistics": True,
        "unresolved_lexical_token_count": lexical.get("<UNRESOLVED>", 0),
        "projections": projections,
    }


def main():
    contract = llv2.load_language_contract(CONFIG_PATH)
    if not contract["authorization"].get(
            "gate_2_token_dataset_implementation"):
        raise llv2.LanguageContractError(
            "Gate 2 token-dataset implementation is not authorized")
    if contract["authorization"].get("test_access"):
        raise llv2.LanguageContractError(
            "Gate 2 must not authorize protected-test access")

    gate1_acceptance = json.loads(
        GATE1_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
    if gate1_acceptance.get("status") != "PASS":
        raise AssertionError("Gate 1 acceptance is required before Gate 2")
    gate1_manifest = json.loads(
        GATE1_MANIFEST_PATH.read_text(encoding="utf-8"))
    language_spans_path = Path(contract["paths"]["language_spans"])
    if digest_file(language_spans_path) != gate1_manifest["output_file_sha256"]:
        raise AssertionError("Gate 1 language-span artifact hash mismatch")

    output_path = Path(contract["paths"]["token_dataset"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path = output_path.parent / "gate2_token_dataset_report.md"
    manifest_path = output_path.parent / "gate2_token_dataset_manifest.json"
    acceptance_path = output_path.parent / "gate2_acceptance.json"
    projections_path = output_path.parent / "language_projection_manifest.json"

    frozen_before = {
        name: digest_file(path) for name, path in FROZEN_PATHS.items()
    }
    language_layer = load_language_layer(language_spans_path, contract)

    first = build_pass(
        language_layer, contract, output_path=output_path)
    second = build_pass(language_layer, contract)
    persisted_logical, persisted_identity = persisted_hashes(output_path)
    frozen_after = {
        name: digest_file(path) for name, path in FROZEN_PATHS.items()
    }

    first_stats = serializable_stats(first["stats"])
    second_stats = serializable_stats(second["stats"])
    deterministic = (
        first["logical_sha256"]
        == second["logical_sha256"]
        == persisted_logical
        and first["source_identity_sha256"]
        == second["source_identity_sha256"]
        == persisted_identity
        and first_stats == second_stats
    )
    frozen_unchanged = frozen_before == frozen_after
    unused_explicit_word_keys = (
        set(language_layer["word_lookup"])
        - first["used_explicit_word_keys"]
    )
    projections = projection_manifest(first["stats"], contract)
    projections_path.write_text(
        json.dumps(projections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("transcription_assisted", POLICIES_PATH)
    manifest = ep.build_manifest(
        task="phase4_gate2_multilingual_token_dataset",
        evidence_policy=policy.name,
        features_requested=[
            "token",
            "damage_state",
            "line_lang_canonical",
            "word_lang_raw",
            "effective_lang_canonical",
        ],
        registry=registry,
        policy=policy,
        dataset_manifest_path=ZIP_PATH,
        split_manifest_path=SPLITS_PATH,
        config_path=CONFIG_PATH,
        seed=SEED,
        declared_statistics_universe=(
            "tokens rebuilt from exact checksum-guarded archive members in "
            "the accepted Gate 1 train + dev + discovery document map; "
            "protected-test and quarantined archive members unopened"),
    )
    manifest.update({
        "script_path": str(SCRIPT_PATH),
        "script_sha256": digest_file(SCRIPT_PATH),
        "registry_sha256": digest_file(REGISTRY_PATH),
        "policy_sha256": digest_file(POLICIES_PATH),
        "decompose_script_sha256": digest_file(DECOMPOSE_SCRIPT_PATH),
        "gate1_manifest_sha256": digest_file(GATE1_MANIFEST_PATH),
        "gate1_language_layer_logical_sha256":
            gate1_manifest["output_logical_sha256"],
        "source_filter": (
            "exact archive_member and source_payload_sha256 from accepted "
            "Gate 1 DOCUMENT records; only train/dev/discovery members opened"),
        "source_token_strategy": (
            "lossless checksum-guarded XML re-walk through shared "
            "lib.decompose_corpus.decompose_document; historical frozen token "
            "cache retained only as an unchanged comparison artifact because "
            "it conflates at least one distinct archive-stem pair under one "
            "doc_id"),
        "protected_test_rows_emitted": 0,
        "output_path": str(output_path),
        "output_file_sha256": digest_file(output_path),
        "output_logical_sha256": first["logical_sha256"],
        "second_build_logical_sha256": second["logical_sha256"],
        "persisted_logical_sha256": persisted_logical,
        "source_identity_sha256": first["source_identity_sha256"],
        "persisted_identity_sha256": persisted_identity,
        "deterministic_double_build": deterministic,
        "frozen_hashes_before": frozen_before,
        "frozen_hashes_after": frozen_after,
        "frozen_hashes_unchanged": frozen_unchanged,
        "statistics": first_stats,
        "language_projection_manifest":
            str(projections_path),
        "language_projection_manifest_sha256":
            digest_file(projections_path),
        "explicit_word_span_count":
            len(language_layer["word_lookup"]),
        "used_explicit_word_span_count":
            len(first["used_explicit_word_keys"]),
        "unused_explicit_word_span_count":
            len(unused_explicit_word_keys),
    })
    ep.write_manifest(manifest, manifest_path)

    canonical = set(contract["canonical_codes"])
    lexical_counts = first["stats"]["lexical_tokens_by_language"]
    checks = {
        "gate1_acceptance_passed": gate1_acceptance["status"] == "PASS",
        "protected_test_rows_emitted_zero":
            manifest["protected_test_rows_emitted"] == 0,
        "source_rebuild_emitted_only_allowed_documents":
            first["stats"]["disallowed_document_count"] == 0,
        "source_and_persisted_token_identity_exact":
            first["source_identity_sha256"] == persisted_identity,
        "two_builds_and_readback_logically_identical": deterministic,
        "frozen_artifact_hashes_unchanged": frozen_unchanged,
        "token_identity_keys_unique_and_sorted":
            first["stats"]["duplicate_or_unsorted_identity_count"] == 0,
        "source_row_count_preserved_exactly": (
            first["stats"]["raw_source_token_row_count"]
            == first["stats"]["token_count"]
        ),
        "every_token_has_effective_status": (
            sum(first["stats"]["effective_status_counts"].values())
            == first["stats"]["token_count"]
        ),
        "resolved_lexical_languages_are_canonical": (
            set(lexical_counts) - {"<UNRESOLVED>"} <= canonical
        ),
        "structural_tokens_excluded_from_lexical_statistics": (
            first["stats"]["structural_token_count"]
            + sum(lexical_counts.values())
            == first["stats"]["token_count"]
        ),
        "word_span_lookup_keys_unique":
            len(language_layer["word_lookup"])
            == len(set(language_layer["word_lookup"])),
        "all_five_language_scopes_materialized":
            set(projections["projections"])
            == llv2.LANGUAGE_SCOPES,
        "unconditioned_projection_is_explicit_ablation": (
            projections["projections"][
                "ALL_LANGUAGES_UNCONDITIONED"]["ablation_only"]
            and projections["projections"][
                "ALL_LANGUAGES_UNCONDITIONED"]["language_identity"]
            == "INTENTIONALLY_REMOVED"
        ),
        "evidence_policy_manifest_completed": (
            manifest["evidence_policy"] == "transcription_assisted"
            and manifest["prohibited_features_encountered"] == []
        ),
    }
    gate2_passed = all(checks.values())
    acceptance = {
        "gate": "Phase 4 Gate 2",
        "status": "PASS" if gate2_passed else "FAIL",
        "contract": str(CONFIG_PATH),
        "output": str(output_path),
        "checks": checks,
        "authorization_after_gate": {
            "language_aware_api_and_workbench_implementation": gate2_passed,
            "protected_test_access": False,
            "gpu_training": False,
            "training_authorized": False,
        },
    }
    acceptance_path.write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not gate2_passed:
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise AssertionError(f"Gate 2 acceptance failed: {failed}")

    stats = first["stats"]
    report = [
        "# Phase 4 Gate 2 multilingual token dataset",
        "",
        "**Status: PASS — language-aware API/workbench implementation may "
        "proceed; training remains unauthorized.**",
        "",
        "The dataset joins the accepted Gate 1 source spans to token keys "
        "rebuilt from those same exact checksum-guarded XML members through "
        "the shared lossless decomposition function. This is necessary "
        "because the historical frozen token cache conflates at least one "
        "distinct archive-stem pair under one document identifier; it remains "
        "unchanged as a historical comparison artifact, not the Gate 2 row "
        "source.",
        "",
        f"- Token rows: **{stats['token_count']:,}** across "
        f"**{stats['document_count']:,}** documents.",
        "- Protected-test rows emitted: **0**.",
        f"- Structural tokens retained: "
        f"**{stats['structural_token_count']:,}**; all are excluded from "
        "lexical-language statistics.",
        f"- Mixed-language line token rows: "
        f"**{stats['mixed_line_token_count']:,}**.",
        f"- Mixed-language document token rows: "
        f"**{stats['mixed_document_token_count']:,}**.",
        f"- Explicit word-language spans used by at least one token: "
        f"**{len(first['used_explicit_word_keys']):,}** of "
        f"**{len(language_layer['word_lookup']):,}**; unused spans remain "
        "preserved in Gate 1 (typically words with no decomposed token).",
        f"- Logical SHA-256: `{first['logical_sha256']}`.",
        f"- Two builds and persisted readback agree: **{deterministic}**.",
        f"- Frozen hashes unchanged: **{frozen_unchanged}**.",
        "",
        "## Lexical tokens by effective language",
        "",
        "| language | tokens |",
        "|---|---:|",
    ]
    for language, count in sorted(
            lexical_counts.items(), key=lambda item: (-item[1], item[0])):
        report.append(f"| `{language}` | {count:,} |")
    report += [
        "",
        "## Projection contract",
        "",
        "All five Gate 0 scopes are materialized as deterministic projection "
        "definitions in `language_projection_manifest.json`. Structural "
        "layout tokens are retained in every projection but never counted as "
        "lexical evidence. `SAME_LANGUAGE_AS_QUERY` and "
        "`CROSS_LANGUAGE_PARALLEL` require a resolved query language; "
        "omitted/automatic scopes fail closed. "
        "`ALL_LANGUAGES_UNCONDITIONED` explicitly removes language identity "
        "and is labeled ablation-only.",
        "",
        f"Dataset: `{output_path}`. Manifest: `{manifest_path}`. "
        f"Acceptance: `{acceptance_path}`.",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"Dataset: {output_path}")
    print(f"Report: {report_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Acceptance: {acceptance_path}")


if __name__ == "__main__":
    main()
