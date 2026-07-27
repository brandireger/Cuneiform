#!/usr/bin/env python3
"""P4-E: extract unresolved occurrences into the governed workbench zone.

Builds `Phase4/phase4_out/unresolved_occurrences.parquet` from the accepted
Gate 2 multilingual token dataset plus the Gate 1 quarantine, per
`specs/UNRESOLVED_EVIDENCE_WORKBENCH.md`.

Design decisions worth stating, because each is a place where a convenient
default would have been wrong:

- **An occurrence is a contiguous RUN**, not a token. 159,673 illegible and
  152,634 partially-preserved tokens are not 312,307 separate questions for an
  expert; a run of four illegible signs is one lacuna. Runs are cut whenever
  the category set changes, so a run is homogeneous by construction.

- **`restored` is not a workbench category.** Editorial restoration is a
  scholarly hypothesis already typed as `EDITORIAL_RESTORATION` and governed by
  the evidence policy. It is not unresolved evidence, and filing it here would
  quietly reframe 765,291 editorial proposals as open questions.

- **`LEXICAL_UNKNOWN` is deliberately not populated.** The contract requires a
  governed detector and forbids inferring it from a tokenizer OOV. No such
  detector has been ratified, so the category stays empty rather than being
  faked with a frequency threshold. This is reported, not silently skipped.

- **`cu` is never read.** It renders editor-restored content as real glyphs
  (CLAUDE.md), so it is not cleanroom-safe even for display fields.

Test-side material cannot appear: the Gate 2 dataset contains none, and the
contract re-checks `main_split` per occurrence.

Usage:
    python scripts/phase4_unresolved_extraction.py
"""
import hashlib
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import pandas as pd  # noqa: E402

import evidence_policy as ep  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import unresolved_evidence as ue  # noqa: E402

SEED = 20260726
POLICY_NAME = "transcription_assisted"

TOKENS_V2_PATH = Path("Phase4/phase4_out/multilingual_tokens_v2.parquet")
GATE1_SPANS_PATH = Path("migrations/language_layers_v2/language_spans.parquet")
GATE1_QUARANTINE_PATH = Path(
    "migrations/language_layers_v2/quarantined_source_anomalies.jsonl")
GATE2_MANIFEST_PATH = Path(
    "Phase4/phase4_out/gate2_token_dataset_manifest.json")
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
EDGES_PATH = Path("Phase1_pipeline/p2_out/edges.parquet")
CONFIG_PATH = Path("configs/language_layers_v2.json")
REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")

OUT_DIR = Path("Phase4/phase4_out")
OCCURRENCES_PATH = OUT_DIR / "unresolved_occurrences.parquet"
MANIFEST_PATH = OUT_DIR / "unresolved_extraction_manifest.json"
REPORT_PATH = OUT_DIR / "unresolved_workbench_report.md"

CONTEXT_TOKENS = 6

# Uncertainty and correction markers carried in the transliteration itself.
# `?` marks an uncertain reading, `!` an editorial correction; both are
# editorial uncertainty, which is what UNCERTAIN_TRANSCRIPTION names.
UNCERTAINTY_MARKERS = ("?", "!")

# Governed rare-form detector, ratified 2026-07-27.
#
# RARE_FORM is a claim about this corpus, not about Hittitology: the detector
# can establish that a form is attested at most RARE_FORM_MAX_COUNT times in
# the declared universe, nothing more. LEXICAL_UNKNOWN remains reserved for
# expert assertion and is never set here.
#
# The frequency universe is deliberately narrow: non-structural tokens whose
# damage state is `attested` or `laes`, over the governed non-test universe.
# Restored tokens are excluded because they are editorial proposals -- letting
# them inflate a count would hide genuinely rare attested forms behind
# scholarly reconstruction, the opposite of "let the artifacts speak".
# Illegible `x` placeholders are excluded because they are not readings.
RARE_FORM_DETECTOR = "attested_frequency_at_most_1_in_governed_non_test_universe"
RARE_FORM_MAX_COUNT = 1
RARE_FORM_COUNTED_DAMAGE_STATES = ("attested", "laes")


def digest_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_hash(occurrences):
    """Content hash over the stable identity of every occurrence.

    Not a file hash. Parquet footer metadata and this run's `created_utc`
    both change between builds, so identical extractions produce different
    bytes; Gate 1 and Gate 2 report a logical hash for the same reason.
    Provenance is deliberately excluded -- WHEN an occurrence was extracted
    is not part of WHAT it is, and including it would make the determinism
    check unfalsifiable.
    """
    digest = hashlib.sha256()
    for item in sorted(occurrences, key=lambda o: o["occurrence_id"]):
        stable = {
            key: item[key] for key in
            ("occurrence_id", "categories", "status", "location", "language",
             "display", "context", "evidence_classes", "assistance_layers",
             "ground_truth_status")
        }
        digest.update(json.dumps(
            stable, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


def build_attested_frequency(frame):
    """token -> attested/laes occurrence count over the declared universe.

    Fit over the whole governed non-test universe, never over a query-derived
    subset, per CLAUDE.md's corpus-statistics rule.
    """
    counted = frame[
        (~frame["is_structural_token"])
        & (frame["damage_state"].isin(RARE_FORM_COUNTED_DAMAGE_STATES))
    ]
    return Counter(counted["token"])


def has_encoding_anomaly(token):
    """Private-use, surrogate, unassigned, or stray control characters.

    Deterministic and source-driven: it asks whether the character can be
    represented and named, never whether the reading looks plausible.
    """
    for char in token:
        category = unicodedata.category(char)
        if category in ("Co", "Cs", "Cn"):
            return True
        if category.startswith("C") and char not in "\t":
            return True
    return False


def token_categories(row, vocabulary, frequency):
    """Every workbench category that applies to one token, kept distinct."""
    categories = set()
    if row.damage_state == "illegible_x":
        categories.add("ILLEGIBLE_SIGN")
    elif row.damage_state == "laes":
        categories.add("PARTIALLY_PRESERVED_READING")

    token = row.token
    if any(marker in token for marker in UNCERTAINTY_MARKERS):
        categories.add("UNCERTAIN_TRANSCRIPTION")
    if has_encoding_anomaly(token):
        categories.add("SYMBOL_OR_ENCODING_ANOMALY")
    # An engineering vocabulary miss, recorded as exactly that. It is never
    # promoted to LEXICAL_UNKNOWN, which would be a claim about Hittitology.
    if not row.is_structural_token and token not in vocabulary:
        categories.add("TOKENIZER_OOV")
    # Rare in this corpus -- an invitation to look, not a lexical verdict.
    # Only tokens that are themselves readings can be rare; an illegible
    # placeholder or a purely restored form has no attested identity to be
    # rare about.
    if (not row.is_structural_token
            and row.damage_state in RARE_FORM_COUNTED_DAMAGE_STATES
            and 0 < frequency.get(token, 0) <= RARE_FORM_MAX_COUNT):
        categories.add("RARE_FORM")

    source_categories = row.workbench_categories
    if source_categories is not None:
        categories.update(source_categories)

    # An unresolved effective language must always be reportable AS a
    # language anomaly. Gate 2 supplies workbench_categories only for
    # explicit word-tag anomalies, so a token whose LINE tag is absent,
    # malformed, or unrecognized -- and which therefore has nothing valid to
    # inherit -- would otherwise carry no category at all and vanish.
    if not row.is_structural_token and pd.isna(row.effective_lang_canonical) \
            and not (categories & ue.LANGUAGE_CATEGORIES):
        status = (row.word_lang_status
                  if row.word_lang_status in ue.LANGUAGE_STATUS_CATEGORY
                  and row.word_lang_status != "missing"
                  else row.line_lang_status)
        category = ue.LANGUAGE_STATUS_CATEGORY.get(status)
        if category is None:
            raise AssertionError(
                f"Unresolved token with unmappable language status "
                f"(word={row.word_lang_status!r}, line={row.line_lang_status!r})")
        categories.add(category)
    return frozenset(categories)


def build_runs(frame, vocabulary, frequency):
    """Group each line's tokens into contiguous same-category runs."""
    runs = []
    for (doc_id, line_index), group in frame.groupby(
            ["doc_id", "line_index_in_doc"], sort=True):
        rows = list(group.itertuples(index=False))
        tokens = [row.token for row in rows]
        current = None
        for position, row in enumerate(rows):
            categories = token_categories(row, vocabulary, frequency)
            if not categories:
                current = None
                continue
            if current is not None and current["categories"] == categories \
                    and current["end"] == position - 1:
                current["end"] = position
                continue
            current = {
                "doc_id": doc_id,
                "line_index_in_doc": int(line_index),
                "categories": categories,
                "start": position,
                "end": position,
                "row": row,
                "line_tokens": tokens,
            }
            runs.append(current)
    return runs


def occurrence_id(doc_id, line_index, start, end, categories):
    """Stable, content-addressed identity for one occurrence.

    Keyed on location plus category set, so a rebuild from the same pinned
    corpus reproduces the same ids and an expert annotation stays bound to the
    thing it was made about.
    """
    payload = json.dumps(
        [doc_id, line_index, start, end, sorted(categories)],
        ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def load_fragment_map():
    """(doc_id, line_index_in_doc) -> fragment_id, where an edge record says.

    Absent means the line is not covered by a fragment record; the location
    field is nullable rather than defaulted to the document id, which would
    assert a fragment identity the edge table does not support.
    """
    edges = pd.read_parquet(
        EDGES_PATH, columns=["fragment_id", "parent_doc", "lines"])
    owner = {}
    for row in edges.itertuples(index=False):
        for record in json.loads(row.lines):
            owner[(row.parent_doc, int(record["line_index_in_doc"]))] = \
                row.fragment_id
    return owner


def source_payload_map():
    """doc_id -> (archive_member, payload_sha256) from the Gate 1 spans."""
    spans = pd.read_parquet(
        GATE1_SPANS_PATH,
        columns=["doc_id", "source_archive_member", "source_payload_sha256"])
    spans = spans.drop_duplicates("doc_id")
    return {
        row.doc_id: (row.source_archive_member, row.source_payload_sha256)
        for row in spans.itertuples(index=False)
    }


def main():
    for path in (TOKENS_V2_PATH, GATE1_SPANS_PATH, GATE1_QUARANTINE_PATH):
        if not path.exists():
            raise SystemExit(
                f"{path} not found. Run the Gate 1/Gate 2 builders first.")

    tokenizer = ht.Tokenizer.load()
    vocabulary = set(tokenizer.vocab)

    print("Loading the accepted Gate 2 token dataset ...")
    frame = pd.read_parquet(TOKENS_V2_PATH, columns=[
        "doc_id", "main_split", "line_index_in_doc", "word_pos", "token",
        "damage_state", "word_index_in_line", "line_lang_canonical",
        "line_lang_status", "word_lang_canonical", "word_lang_status",
        "effective_lang_canonical",
        "effective_lang_status", "effective_lang_source",
        "mixed_language_line", "mixed_language_document",
        "is_structural_token", "workbench_categories",
    ]).sort_values(["doc_id", "line_index_in_doc", "word_pos"])

    leaked = sorted(set(frame["main_split"]) - set(ue.PERMITTED_SPLITS))
    if leaked:
        raise AssertionError(
            f"Gate 2 dataset carries non-permitted split(s) {leaked}; "
            "refusing to extract")

    fragment_map = load_fragment_map()
    payloads = source_payload_map()
    split_by_doc = dict(zip(frame["doc_id"], frame["main_split"]))

    provenance = ue.build_provenance(
        split_manifest_hash=digest_file(SPLITS_PATH),
        language_layer_hash=digest_file(TOKENS_V2_PATH),
        config_hash=digest_file(CONFIG_PATH),
        git_commit=ep._git_commit(),
        seed=SEED,
        evidence_policy=POLICY_NAME,
    )

    frequency = build_attested_frequency(frame)
    print(f"Attested-form frequency universe: {len(frequency):,} distinct "
          f"tokens; {sum(1 for c in frequency.values() if c <= RARE_FORM_MAX_COUNT):,} "
          f"at or below the rare-form threshold ({RARE_FORM_MAX_COUNT}).")

    print("Grouping tokens into contiguous same-category runs ...")
    runs = build_runs(frame, vocabulary, frequency)
    print(f"  runs: {len(runs):,}")

    occurrences = []
    category_counts = Counter()
    split_counts = Counter()
    language_counts = Counter()
    unresolved_language_occurrences = 0

    for run in runs:
        row = run["row"]
        doc_id = run["doc_id"]
        line_index = run["line_index_in_doc"]
        start, end = run["start"], run["end"]
        line_tokens = run["line_tokens"]
        archive_member, payload_sha = payloads.get(doc_id, (None, None))
        if archive_member is None:
            # Every Gate 2 document comes from an admitted Gate 1 member, so
            # this cannot happen; fail closed rather than emit an occurrence
            # with no checksum anchor.
            raise AssertionError(
                f"No Gate 1 source payload for {doc_id!r}")

        categories = run["categories"]
        occurrence = ue.build_occurrence(
            occurrence_id=occurrence_id(
                doc_id, line_index, start, end, categories),
            categories=categories,
            location=ue.build_location(
                doc_id=doc_id,
                fragment_id=fragment_map.get((doc_id, line_index)),
                line_index_in_doc=line_index,
                word_index_in_line=(
                    None if pd.isna(row.word_index_in_line)
                    else int(row.word_index_in_line)),
                token_start=start,
                token_end=end,
                main_split=row.main_split,
                source_archive_member=archive_member,
                source_payload_sha256=payload_sha,
            ),
            language=ue.build_language_assignment(
                # Gate 0 decision 5: document language is provenance only and
                # is never an effective-language fallback, so it is not
                # materialized as a per-token field and is recorded as null
                # here rather than back-filled from a weaker source.
                document=None,
                line=(None if pd.isna(row.line_lang_canonical)
                      else row.line_lang_canonical),
                word=(None if pd.isna(row.word_lang_canonical)
                      else row.word_lang_canonical),
                effective=(None if pd.isna(row.effective_lang_canonical)
                           else row.effective_lang_canonical),
                effective_status=row.effective_lang_status,
                effective_source=row.effective_lang_source,
            ),
            display={
                "tokens": line_tokens[start:end + 1],
                "damage_state": row.damage_state,
                "token_count": end - start + 1,
            },
            context={
                "left": line_tokens[max(0, start - CONTEXT_TOKENS):start],
                "right": line_tokens[end + 1:end + 1 + CONTEXT_TOKENS],
                "full_line": line_tokens,
                "mixed_language_line": bool(row.mixed_language_line),
                "mixed_language_document": bool(row.mixed_language_document),
                "rare_form_detector": (
                    RARE_FORM_DETECTOR if "RARE_FORM" in categories else None),
                # Never set by extraction: only a trained specialist can
                # assert that a form is unknown to Hittitology. Named so its
                # absence is a stated fact, not an oversight.
                "lexical_unknown_detector": None,
            },
            evidence_classes=["EDITORIAL_TRANSCRIPTION"],
            assistance_layers=[],
            provenance=provenance,
        )
        occurrences.append(occurrence)
        for category in occurrence["categories"]:
            category_counts[category] += 1
        split_counts[row.main_split] += 1
        language_counts[occurrence["language"]["effective"] or "<UNRESOLVED>"] += 1
        if occurrence["language"]["effective"] is None:
            unresolved_language_occurrences += 1

    # ---- Gate 1 parser anomalies (word-language attributes recorded outside
    # the primary <text>). These have no enclosing line or token span, which
    # is why contract 1.0.1 made those location fields nullable.
    quarantine_added = 0
    for record in (
            json.loads(line) for line in
            GATE1_QUARANTINE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()):
        split = record.get("main_split") or split_by_doc.get(record["doc_id"])
        if split not in ue.PERMITTED_SPLITS:
            continue
        occurrence = ue.build_occurrence(
            occurrence_id=f"gate1-anomaly-{record['anomaly_id'][:24]}",
            categories=[record["category"]],
            location=ue.build_location(
                doc_id=record["doc_id"],
                fragment_id=None,
                line_index_in_doc=None,
                word_index_in_line=None,
                token_start=None,
                token_end=None,
                main_split=split,
                source_archive_member=record["source_archive_member"],
                source_payload_sha256=record["source_payload_sha256"],
            ),
            language=ue.build_language_assignment(
                document=None,
                line=None,
                word=record.get("language_canonical"),
                effective=None,
                effective_status=(
                    "UNRESOLVED_EXPLICIT_WORD_TAG"
                    if record.get("language_status") != "valid" else "MISSING"),
                effective_source="UNRESOLVED",
            ),
            display={
                "anomaly_type": record["anomaly_type"],
                "language_raw": record.get("language_raw"),
                "document_word_index": record.get("document_word_index"),
            },
            context={
                "note": (
                    "Explicit word-language attribute outside the primary "
                    "<text> element; no enclosing line or token span exists "
                    "in the parsed structure."),
                "lexical_unknown_detector": None,
            },
            evidence_classes=[record["evidence_class"]],
            assistance_layers=[],
            provenance=provenance,
        )
        occurrences.append(occurrence)
        category_counts[record["category"]] += 1
        split_counts[split] += 1
        quarantine_added += 1

    print(f"  occurrences: {len(occurrences):,} "
          f"({quarantine_added} from the Gate 1 quarantine)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame([
        {
            "occurrence_id": item["occurrence_id"],
            "categories": item["categories"],
            "status": item["status"],
            "doc_id": item["location"]["doc_id"],
            "fragment_id": item["location"]["fragment_id"],
            "line_index_in_doc": item["location"]["line_index_in_doc"],
            "token_start": item["location"]["token_start"],
            "token_end": item["location"]["token_end"],
            "main_split": item["location"]["main_split"],
            "source_archive_member": item["location"]["source_archive_member"],
            "source_payload_sha256": item["location"]["source_payload_sha256"],
            "effective_language": item["language"]["effective"],
            "effective_lang_status": item["language"]["effective_status"],
            "mixed_language_line": item["context"].get("mixed_language_line"),
            "record": json.dumps(item, ensure_ascii=False, sort_keys=True),
        }
        for item in occurrences
    ]).sort_values("occurrence_id").reset_index(drop=True)
    table.to_parquet(OCCURRENCES_PATH, index=False)

    duplicate_ids = int(table["occurrence_id"].duplicated().sum())
    if duplicate_ids:
        raise AssertionError(
            f"{duplicate_ids} duplicate occurrence_id(s); identity is not "
            "stable and expert annotations could not bind reliably")

    # Acceptance check: every unresolved lexical token in the Gate 2 dataset
    # must be covered by some occurrence. The first extraction pass silently
    # dropped 71 of them (their line carried no language attribute, a state
    # the 1.0.0 category vocabulary could not name), which is exactly the
    # "never silently discarded because it is unresolved" rule the charter
    # sets. A count that merely looks plausible is not evidence of coverage.
    unresolved_tokens = {
        (row.doc_id, int(row.line_index_in_doc), int(row.word_pos))
        for row in frame.itertuples(index=False)
        if not row.is_structural_token
        and pd.isna(row.effective_lang_canonical)
    }
    covered = set()
    for item in occurrences:
        location = item["location"]
        if location["token_start"] is None:
            continue
        for word_pos in range(
                location["token_start"], location["token_end"] + 1):
            covered.add((
                location["doc_id"], location["line_index_in_doc"], word_pos))
    uncovered = unresolved_tokens - covered
    if uncovered:
        raise AssertionError(
            f"{len(uncovered)} unresolved lexical token(s) are not covered by "
            f"any occurrence, e.g. {sorted(uncovered)[:3]} -- unresolved "
            "material may never be silently dropped")
    print(f"  unresolved lexical tokens covered: {len(unresolved_tokens):,}/"
          f"{len(unresolved_tokens):,}")

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(POLICY_NAME, POLICIES_PATH)
    manifest = ep.build_manifest(
        task="phase4_p4e_unresolved_evidence_extraction",
        evidence_policy=policy.name,
        features_requested=[
            "token", "damage_state", "line_lang_canonical",
            "word_lang_canonical", "effective_lang_canonical",
        ],
        registry=registry,
        policy=policy,
        dataset_manifest_path=GATE2_MANIFEST_PATH,
        split_manifest_path=SPLITS_PATH,
        config_path=CONFIG_PATH,
        seed=SEED,
        declared_statistics_universe=(
            "unresolved occurrences over the accepted Gate 2 non-test "
            "multilingual token dataset (train + dev + discovery) plus the "
            "Gate 1 source-anomaly quarantine; protected test excluded by "
            "construction"),
    )
    manifest["workbench"] = {
        "contract_version": ue.CONTRACT_VERSION,
        "occurrence_count": len(occurrences),
        "runs_from_tokens": len(runs),
        "quarantine_occurrences": quarantine_added,
        "category_counts": dict(sorted(category_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "effective_language_counts": dict(sorted(language_counts.items())),
        "unresolved_language_occurrences": unresolved_language_occurrences,
        "protected_test_occurrences": 0,
        "rare_form_detector": {
            "name": RARE_FORM_DETECTOR,
            "max_count": RARE_FORM_MAX_COUNT,
            "counted_damage_states": list(RARE_FORM_COUNTED_DAMAGE_STATES),
            "declared_universe": (
                "non-structural attested/laes tokens over the governed "
                "non-test universe (train + dev + discovery); restored and "
                "illegible tokens excluded"),
            "distinct_tokens_in_universe": len(frequency),
        },
        "categories_not_populated": {
            "LEXICAL_UNKNOWN": (
                "Reserved for expert assertion (ratified 2026-07-27). A "
                "frequency detector can establish that a form is rare in this "
                "corpus; it cannot establish that a form is unknown to "
                "Hittitology. Extraction therefore never sets it -- it is "
                "reachable only through expert adjudication. RARE_FORM "
                "carries the corpus-frequency signal instead."),
        },
        "excluded_by_design": {
            "restored": (
                "Editorial restoration is an EDITORIAL_RESTORATION scholarly "
                "hypothesis governed by the evidence policy, not unresolved "
                "evidence; 765,291 restored tokens are deliberately not "
                "workbench occurrences."),
            "cu": "Not read: it renders restored content as real glyphs.",
        },
        "occurrences_logical_sha256": logical_hash(occurrences),
        "occurrences_file_sha256": digest_file(OCCURRENCES_PATH),
        "file_hash_is_not_stable": (
            "Parquet footer metadata and this run's created_utc differ "
            "between builds; compare occurrences_logical_sha256 to check "
            "reproducibility."),
    }
    ep.write_manifest(manifest, MANIFEST_PATH)

    lines = [
        "# Phase 4 P4-E — unresolved evidence extraction",
        "",
        f"**Contract:** `unresolved_evidence_contract` "
        f"v{ue.CONTRACT_VERSION}. Every record is `NOT_CORPUS_TRUTH`.",
        "",
        f"- Occurrences: **{len(occurrences):,}** "
        f"({len(runs):,} contiguous token runs plus {quarantine_added} Gate 1 "
        "source anomalies).",
        "- Protected-test occurrences: **0** (the Gate 2 universe contains "
        "none and the contract re-checks each split).",
        f"- Occurrences with an unresolved effective language: "
        f"**{unresolved_language_occurrences:,}**.",
        f"- Logical SHA-256 (content, excluding run timestamp): "
        f"`{logical_hash(occurrences)}`.",
        "",
        "## Occurrences by category",
        "",
        "| category | occurrences |",
        "|---|---:|",
    ]
    for category in ue.CATEGORIES:
        lines.append(f"| `{category}` | {category_counts.get(category, 0):,} |")
    lines += [
        "",
        "An occurrence may carry several categories, so the column sums to "
        "more than the occurrence count. Categories are never merged: a "
        "`TOKENIZER_OOV` is an engineering vocabulary miss and is not "
        "evidence that the word is unknown to Hittitology.",
        "",
        "## By split",
        "",
        "| split | occurrences |",
        "|---|---:|",
    ]
    for split, count in sorted(split_counts.items()):
        lines.append(f"| `{split}` | {count:,} |")
    lines += [
        "",
        "Dev-split occurrences are extractable but annotations on them may "
        "not influence a dev metric that claims to be held out.",
        "",
        "## By effective language",
        "",
        "| language | occurrences |",
        "|---|---:|",
    ]
    for language, count in sorted(
            language_counts.items(), key=lambda item: -item[1]):
        lines.append(f"| `{language}` | {count:,} |")
    lines += [
        "",
        "## Deliberately not populated",
        "",
        "- **`LEXICAL_UNKNOWN`** — the contract requires a governed detector "
        "and forbids inferring the category from a tokenizer OOV. No such "
        "detector has been ratified, so the category is empty. Approximating "
        "it with a frequency threshold would assert a claim about Hittite "
        "lexis that this pipeline cannot support. **Requires an Ixca "
        "decision** before it can be filled.",
        "- **`restored` spans** — editorial restorations are scholarly "
        "hypotheses typed `EDITORIAL_RESTORATION`, not unresolved evidence. "
        "Filing 765,291 of them here would reframe editorial proposals as "
        "open questions.",
        "- **`cu`** — never read; it renders restored content as real glyphs "
        "and is not cleanroom-safe even as a display field.",
        "",
        "## Boundaries",
        "",
        "- Expert annotations are append-only, hash-bound, and quarantined; "
        "`EXPERT_SUPPORTED` means one recorded expert supports a hypothesis, "
        "not corpus truth or consensus.",
        "- No annotation enters training without a separate adjudication and "
        "export gate.",
        "- Similarity values carry `scores_are_probabilities: false`.",
        "",
        f"Artifacts: `{OCCURRENCES_PATH}` (gitignored, regenerable), "
        f"`{MANIFEST_PATH}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OCCURRENCES_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}.")


if __name__ == "__main__":
    main()
