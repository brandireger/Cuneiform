#!/usr/bin/env python3
"""P4-E2: build a reviewable queue from the ratified workbench artifacts.

The workbench data layer is complete but not usable by a person. Clustering is
Zipfian: the largest same-language proposal has 95,530 members across 17,353
documents and its whole shared sequence is `x`, the illegible placeholder. A UI
that simply listed clusters would open on that. This script is the layer that
turns ratified evidence into a finite amount of work, under a policy that is
named, versioned, and reported rather than improvised in the view code.

Three commitments the rest of Phase 4 already makes, kept here:

- **Nothing ratified is mutated.** Occurrences, cluster proposals, and their
  hashes are read-only inputs. Selection happens here, in the export, so the
  accepted `occurrences_logical_sha256` and `candidates_logical_sha256` stay
  exactly what they were. A queue is a view, never a new source of truth.

- **The subset is declared, not implied.** Every exclusion is counted and
  written to the manifest and the report. An interface that shows 150 of 4,566
  clusters must say so on screen, and it cannot say so unless the export tells
  it what it dropped.

- **Full canonical records travel with the queue.** The event contract binds an
  expert action to `canonical_sha256(reviewed_record)`. If the browser hashed a
  trimmed display object, that binding would point at nothing on disk. So the
  payload carries whole records and the UI trims only for display.

Usage:
    python scripts/phase4_workbench_review_export.py
    python scripts/phase4_workbench_review_export.py --max-clusters 40
"""
import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import pandas as pd  # noqa: E402

import evidence_policy as ep  # noqa: E402
import unresolved_evidence as ue  # noqa: E402

SEED = 20260727
POLICY_NAME = "transcription_assisted"

# ---------------------------------------------------------------- queue policy
#
# Versioned deliberately. If any value below changes, the queue an expert
# worked from changes, and a reader of their annotations needs to be able to
# tell which queue produced them.
QUEUE_POLICY = "contentful_sequence_length_v1"

# Characters that carry no sign value: the illegible placeholder `x`, the
# indeterminate-length filler `_`, and editorial parentheses/periods. A token
# that is nothing but these encodes the ABSENCE of a reading rather than a
# reading, so grouping on it says only "both are unreadable" -- which is not
# evidence an expert can compare, and is exactly what produces the
# 95,530-member `x` cluster. A character test rather than a token list because
# the placeholders combine: `x`, `x x`, `)x`, `(_)`, `x x x x x( )x` are all
# the same nothing. Excluded from the QUEUE, never from the extraction.
CONTENTLESS_CHARS = frozenset("x_(). ")

# Shared-sequence evidence gets its force from specificity. Two documents
# sharing a five-sign damaged phrase is a parallel worth an expert's time;
# 3,542 documents sharing the single sign `a` is a frequency artifact wearing
# the same clothes. Single-sign clusters are therefore held out of the queue by
# default -- the second Zipfian floor, one level up from `x`.
MIN_SEQUENCE_LENGTH = 2

# An expert reviews a sample of a large cluster; the UI must never imply the
# whole cluster was seen. The cap is on DISPLAY, and `member_count` always
# reports the true size beside it.
MAX_MEMBERS_DISPLAYED = 12

# Browser payload bound, sized to a review session rather than to the corpus:
# a specialist working carefully gets through tens of clusters in a sitting,
# not thousands, and the payload carries whole records plus surrounding lines.
# Not a claim that the rest is uninteresting -- raise it with --max-clusters.
MAX_CLUSTERS_PER_CHANNEL = 60

# Lines of surrounding context per side. The occurrence record carries its own
# line only; the spec asks for surrounding lines, so they are rebuilt here from
# the same governed Gate 2 dataset rather than from a second source.
CONTEXT_LINES = 2

OUT_DIR = Path("Phase4/phase4_out")
UI_DIR = OUT_DIR / "workbench_ui_out"
OCCURRENCES_PATH = OUT_DIR / "unresolved_occurrences.parquet"
TOKENS_V2_PATH = OUT_DIR / "multilingual_tokens_v2.parquet"
CANDIDATES = {
    "SAME_LANGUAGE_AS_QUERY": OUT_DIR / "unresolved_similarity_candidates.jsonl",
    "CROSS_LANGUAGE_PARALLEL": (
        OUT_DIR / "unresolved_similarity_candidates_cross_language.jsonl"),
}
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
CONFIG_PATH = Path("configs/language_layers_v2.json")

# Sentinel for a cluster whose members carry no resolved language. It is not a
# canonical code and must be requested by name, never swept in with a real one.
UNRESOLVED_LANGUAGE = "<UNRESOLVED>"
CLUSTER_MANIFEST_PATH = OUT_DIR / "unresolved_extraction_manifest.json"

QUEUE_JS_PATH = UI_DIR / "workbench_review_queue.js"
QUEUE_MANIFEST_PATH = UI_DIR / "workbench_review_queue_manifest.json"
QUEUE_REPORT_PATH = UI_DIR / "workbench_review_queue_report.md"


def digest_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_proposals(path):
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sequence_is_contentless(proposal):
    """True when the cluster's shared sequence carries no reading at all.

    `supporting_evidence[0].sequence` is the space-joined normalized sequence
    the cluster was keyed on. A sequence of nothing but placeholder characters
    groups occurrences by their emptiness.
    """
    sequence = cluster_sequence(proposal)
    if not sequence.strip():
        return True
    return all(char in CONTENTLESS_CHARS for char in sequence)


def sequence_length(proposal):
    """Signs in the shared sequence. Longer means more specific evidence."""
    return len([t for t in cluster_sequence(proposal).split(" ") if t])


def cluster_sequence(proposal):
    for evidence in proposal.get("supporting_evidence", []):
        if evidence.get("type") == "EXACT_NORMALIZED_SIGN_SEQUENCE":
            return evidence.get("sequence", "")
    return ""


def distinct_document_count(proposal):
    for evidence in proposal.get("supporting_evidence", []):
        if evidence.get("type") == "EXACT_NORMALIZED_SIGN_SEQUENCE":
            return int(evidence.get("distinct_document_count", 0))
    return 0


def cluster_languages(proposal):
    """The languages the clustering itself declared for this proposal.

    Read from the proposal's own supporting evidence rather than recomputed
    from member records: the clustering ran under a validated `language_scope`,
    and re-deriving the language here would be a second implementation of a
    selection the ratified artifact already made.
    """
    for evidence in proposal.get("supporting_evidence", []):
        if evidence.get("type") == "EXACT_NORMALIZED_SIGN_SEQUENCE":
            return [lang or UNRESOLVED_LANGUAGE
                    for lang in evidence.get("languages", [])]
    return []


def parse_language_selection(values, *, canonical_codes):
    """Validate `--language` into a frozen set, or `None` for no selection.

    Fails closed on an unknown code rather than silently returning an empty
    queue: `--language Hittite` and `--language hit` are typos a specialist
    would not otherwise see, and a silently empty session looks identical to
    "this language has no unresolved material", which is a different and much
    more interesting claim.
    """
    if not values:
        return None
    requested = []
    for value in values:
        requested.extend(part.strip() for part in value.split(",") if part.strip())
    permitted = set(canonical_codes) | {UNRESOLVED_LANGUAGE}
    unknown = [code for code in requested if code not in permitted]
    if unknown:
        raise SystemExit(
            f"Unknown language code(s): {', '.join(sorted(set(unknown)))}. "
            f"Ratified canonical codes are {', '.join(canonical_codes)} "
            f"(plus {UNRESOLVED_LANGUAGE} for occurrences with no resolved "
            "language). Codes are case-sensitive and come from "
            f"{CONFIG_PATH.as_posix()}.")
    if not requested:
        return None
    return frozenset(requested)


def proposal_matches_language(proposal, selection):
    """Whether a cluster is admitted by the requested language selection.

    The test is "declares at least one requested language", and it means
    different things per channel by construction. A `SAME_LANGUAGE_AS_QUERY`
    cluster is single-language, so this selects genuinely Akkadian (or Luwian,
    or Hurrian) clusters. A `CROSS_LANGUAGE_PARALLEL` cluster spans languages
    by definition, so this selects clusters that *involve* the requested
    language -- their other members are deliberately in other languages, and
    that is the point of the channel, not a leak.
    """
    if selection is None:
        return True
    return any(lang in selection for lang in cluster_languages(proposal))


def rank_key(proposal):
    """Queue order: specificity first, then recurrence across documents.

    Ranking by document count alone was tried and inverts the queue: it puts
    the single signs `a`, `i`, `e` at the top, because a damaged common sign
    appears everywhere. Length first, because a long shared sequence is
    unlikely to recur by chance; document count second, because occurrences
    from one document are one scribe rather than independent evidence.
    `cluster_id` breaks ties so the queue is reproducible.
    """
    return (
        -sequence_length(proposal),
        -distinct_document_count(proposal),
        -len(proposal["member_occurrence_ids"]),
        proposal["cluster_id"],
    )


def build_line_index(doc_ids, line_targets):
    """(doc_id, line_index) -> rendered token list, for context lines only.

    Read from the Gate 2 dataset -- the same governed source the occurrences
    were extracted from -- so context can never disagree with the occurrence it
    surrounds.
    """
    wanted_docs = set(doc_ids)
    frame = pd.read_parquet(
        TOKENS_V2_PATH,
        columns=["doc_id", "line_index_in_doc", "word_pos", "token",
                 "damage_state", "effective_lang_canonical"],
    )
    frame = frame[frame["doc_id"].isin(wanted_docs)]
    lines = defaultdict(list)
    for row in frame.sort_values(
            ["doc_id", "line_index_in_doc", "word_pos"]).itertuples(index=False):
        key = (row.doc_id, int(row.line_index_in_doc))
        if key in line_targets:
            lines[key].append({
                "token": row.token,
                "damage_state": row.damage_state,
                "language": row.effective_lang_canonical,
            })
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-clusters", type=int, default=MAX_CLUSTERS_PER_CHANNEL,
        help="clusters exported per channel (payload bound, not a judgment "
             "about the remainder)")
    parser.add_argument(
        "--min-sequence-length", type=int, default=MIN_SEQUENCE_LENGTH,
        help="shortest shared sequence admitted to the queue; 1 admits "
             "single-sign clusters, which are dominated by frequency")
    parser.add_argument(
        "--language", action="append", metavar="CODE",
        help="restrict the queue to clusters declaring this language "
             "(repeatable, or comma-separated). Without it the queue spans "
             "every language, and since ranking is by sequence length and "
             "Hittite is ~89%% of lexical tokens, the result is overwhelmingly "
             "Hittite -- a single-language session is not reachable by "
             "filtering in the browser alone.")
    args = parser.parse_args()

    for path in (OCCURRENCES_PATH, TOKENS_V2_PATH, SPLITS_PATH):
        if not path.exists():
            raise SystemExit(f"{path} not found; rebuild Phase 4 artifacts first.")

    language_contract = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    canonical_codes = language_contract["canonical_codes"]
    language_selection = parse_language_selection(
        args.language, canonical_codes=canonical_codes)
    if language_selection:
        print(f"Language selection: {', '.join(sorted(language_selection))}")

    occurrence_frame = pd.read_parquet(
        OCCURRENCES_PATH, columns=["occurrence_id", "record"])
    records = {
        row.occurrence_id: json.loads(row.record)
        for row in occurrence_frame.itertuples(index=False)
    }
    print(f"Occurrences available: {len(records):,}")

    splits = pd.read_parquet(SPLITS_PATH)
    catalog = {
        row.doc_id: {"cth": str(row.cth), "site": row.site,
                     "is_bin": bool(row.is_bin)}
        for row in splits.itertuples(index=False)
    }

    channels = {}
    policy_counts = {}
    for scope, path in CANDIDATES.items():
        if not path.exists():
            raise SystemExit(
                f"{path} not found. Run scripts/phase4_unresolved_clustering.py"
                f"{' --cross-language' if 'CROSS' in scope else ''} first.")
        proposals = load_proposals(path)
        contentless = [p for p in proposals if sequence_is_contentless(p)]
        remaining = [p for p in proposals if not sequence_is_contentless(p)]
        too_short = [p for p in remaining
                     if sequence_length(p) < args.min_sequence_length]
        contentful = [p for p in remaining
                      if sequence_length(p) >= args.min_sequence_length]
        # Language selection is a separate, separately counted stage. Folding
        # it into the line above would make one number ("eligible") answer two
        # different questions, and the screen has to be able to say which
        # exclusion removed what.
        off_language = [p for p in contentful
                        if not proposal_matches_language(p, language_selection)]
        eligible = [p for p in contentful
                    if proposal_matches_language(p, language_selection)]
        eligible.sort(key=rank_key)
        queued = eligible[:args.max_clusters]
        channels[scope] = queued
        channel_language_counts = Counter()
        for proposal in contentful:
            channel_language_counts.update(set(cluster_languages(proposal)))
        policy_counts[scope] = {
            "proposals_available": len(proposals),
            "excluded_contentless_sequence": len(contentless),
            "excluded_contentless_occurrences": sum(
                len(p["member_occurrence_ids"]) for p in contentless),
            "excluded_below_min_sequence_length": len(too_short),
            "excluded_below_min_occurrences": sum(
                len(p["member_occurrence_ids"]) for p in too_short),
            "excluded_off_language": len(off_language),
            "excluded_off_language_occurrences": sum(
                len(p["member_occurrence_ids"]) for p in off_language),
            "contentful_before_language_selection": len(contentful),
            "contentful_clusters_by_language": dict(
                sorted(channel_language_counts.items())),
            "eligible_after_exclusions": len(eligible),
            "queued": len(queued),
            "not_queued_payload_bound": max(0, len(eligible) - len(queued)),
            "single_document_clusters_queued": sum(
                1 for p in queued if distinct_document_count(p) <= 1),
            "queued_sequence_length_range": (
                [sequence_length(queued[-1]), sequence_length(queued[0])]
                if queued else []),
        }
        print(f"{scope}: {len(proposals):,} proposals -> {len(queued):,} queued "
              f"({len(contentless):,} contentless, {len(too_short):,} "
              f"below min length {args.min_sequence_length}"
              + (f", {len(off_language):,} off-language" if language_selection
                 else "") + " excluded)")
        if language_selection and not queued:
            print(f"  NOTE: no cluster in {scope} declares "
                  f"{', '.join(sorted(language_selection))} at sequence length "
                  f">= {args.min_sequence_length}. That is a real absence in "
                  "this channel, not a failed filter.")

    # Which occurrences and context lines the payload actually needs.
    needed_ids = set()
    for queued in channels.values():
        for proposal in queued:
            needed_ids.update(proposal["member_occurrence_ids"][:MAX_MEMBERS_DISPLAYED])
    missing = sorted(needed_ids - set(records))
    if missing:
        raise SystemExit(
            f"{len(missing)} queued member id(s) absent from the occurrence "
            f"table, e.g. {missing[:3]}; the candidate files and the occurrence "
            "table are out of step -- rebuild both, do not paper over it.")

    line_targets, doc_ids = set(), set()
    for occurrence_id in needed_ids:
        location = records[occurrence_id]["location"]
        doc_id, line_index = location["doc_id"], location["line_index_in_doc"]
        doc_ids.add(doc_id)
        if line_index is None:
            continue
        for offset in range(-CONTEXT_LINES, CONTEXT_LINES + 1):
            line_targets.add((doc_id, int(line_index) + offset))
    print(f"Context: {len(line_targets):,} line(s) across {len(doc_ids):,} document(s)")
    lines = build_line_index(doc_ids, line_targets)

    def member_view(occurrence_id):
        record = records[occurrence_id]
        location = record["location"]
        doc_id = location["doc_id"]
        line_index = location["line_index_in_doc"]
        before, after = [], []
        if line_index is not None:
            line_index = int(line_index)
            for offset in range(CONTEXT_LINES, 0, -1):
                key = (doc_id, line_index - offset)
                if key in lines:
                    before.append({"line_index_in_doc": line_index - offset,
                                   "tokens": lines[key]})
            for offset in range(1, CONTEXT_LINES + 1):
                key = (doc_id, line_index + offset)
                if key in lines:
                    after.append({"line_index_in_doc": line_index + offset,
                                  "tokens": lines[key]})
        meta = catalog.get(doc_id, {})
        return {
            # The whole record, so the browser hashes what is on disk.
            "record": record,
            "catalog": {
                "cth": meta.get("cth"),
                "site": meta.get("site"),
                # A bin document is unlabeled, not negative -- surfaced so an
                # expert can weigh a catch-all filing for what it is.
                "is_bin": meta.get("is_bin"),
                "evidence_class": "CATALOG_METADATA",
            },
            "context_lines": {"before": before, "after": after},
        }

    payload_channels = {}
    for scope, queued in channels.items():
        payload_channels[scope] = [{
            "proposal": proposal,
            "sequence": cluster_sequence(proposal),
            "member_count": len(proposal["member_occurrence_ids"]),
            "distinct_document_count": distinct_document_count(proposal),
            "members_displayed": min(
                MAX_MEMBERS_DISPLAYED, len(proposal["member_occurrence_ids"])),
            "members": [
                member_view(occurrence_id) for occurrence_id
                in proposal["member_occurrence_ids"][:MAX_MEMBERS_DISPLAYED]
            ],
        } for proposal in queued]

    cluster_manifest = json.loads(
        CLUSTER_MANIFEST_PATH.read_text(encoding="utf-8"))
    accepted_hashes = {
        "occurrences_logical_sha256":
            cluster_manifest["workbench"]["occurrences_logical_sha256"],
        "contract_version": ue.CONTRACT_VERSION,
    }
    for scope in CANDIDATES:
        entry = cluster_manifest.get("clustering", {}).get(scope, {})
        accepted_hashes[f"{scope}_candidates_logical_sha256"] = entry.get(
            "candidates_logical_sha256")

    category_counts = Counter()
    language_counts = Counter()
    # Per channel as well as pooled: a cross-language cluster contains members
    # in languages other than the requested one BY DESIGN, so a single pooled
    # tally makes an Akkadian session look contaminated when it is correct.
    language_counts_by_channel = {}
    for scope, queued in payload_channels.items():
        scope_counts = Counter()
        for cluster in queued:
            for member in cluster["members"]:
                category_counts.update(member["record"]["categories"])
                effective = (member["record"]["language"]["effective"]
                             or UNRESOLVED_LANGUAGE)
                language_counts.update([effective])
                scope_counts.update([effective])
        language_counts_by_channel[scope] = dict(sorted(scope_counts.items()))

    queue_manifest = {
        "task": "phase4_workbench_review_export",
        "queue_policy": QUEUE_POLICY,
        "contract_version": ue.CONTRACT_VERSION,
        "ground_truth_status": "NOT_CORPUS_TRUTH",
        "corpus_version": "TLHdig_0.2.0-beta",
        "evidence_policy": POLICY_NAME,
        "seed": SEED,
        "git_commit": ep._git_commit(),
        "source_hashes": accepted_hashes,
        "split_manifest_hash": digest_file(SPLITS_PATH),
        "config_hash": digest_file(CONFIG_PATH),
        "policy_parameters": {
            "contentless_chars": "".join(sorted(CONTENTLESS_CHARS)),
            "min_sequence_length": args.min_sequence_length,
            "max_members_displayed_per_cluster": MAX_MEMBERS_DISPLAYED,
            "max_clusters_per_channel": args.max_clusters,
            "context_lines_per_side": CONTEXT_LINES,
            "ranking": "sequence_length desc, distinct_document_count desc, "
                       "member_count desc, cluster_id asc",
            "language_selection": (
                sorted(language_selection) if language_selection else None),
        },
        "language_selection": {
            "requested": sorted(language_selection) if language_selection else None,
            "evidence_class": "OBSERVED_DOCUMENT_STRUCTURE",
            "source": "cluster proposal supporting_evidence[].languages, as "
                      "declared by the clustering run's validated "
                      "language_scope",
            "canonical_codes": canonical_codes,
            "language_contract_version": language_contract["contract_version"],
            "semantics_by_channel": {
                "SAME_LANGUAGE_AS_QUERY":
                    "clusters are single-language by construction, so a "
                    "selection yields clusters wholly in that language",
                "CROSS_LANGUAGE_PARALLEL":
                    "clusters span languages by construction, so a selection "
                    "yields clusters that INVOLVE that language; their other "
                    "members are in other languages by design",
            },
            "selection_is_a_view_not_a_finding": (
                "Restricting the queue to a language is a display decision. "
                "It does not assert that the excluded material is irrelevant, "
                "and it does not change any occurrence, proposal, or hash."),
            "no_calibration_is_implied": (
                "A single-language review session is a review surface only. "
                "No per-language calibration exists for any language, and no "
                "rate shown anywhere in this project may be transferred to a "
                "language it was not fit on."),
        },
        "channel_counts": policy_counts,
        "queued_member_category_counts": dict(sorted(category_counts.items())),
        "queued_member_language_counts": dict(sorted(language_counts.items())),
        "queued_member_language_counts_by_channel": language_counts_by_channel,
        "selection_is_a_view_not_a_finding": (
            "Exclusion from this queue is a display decision under "
            f"{QUEUE_POLICY}. No occurrence, proposal, or hash is modified, and "
            "an excluded cluster is not thereby judged uninteresting."),
        "default_channel": "SAME_LANGUAGE_AS_QUERY",
        "cross_language_requires_explicit_enable": True,
        # Hash of the queue CONTENT, so a rebuild can be checked the way every
        # other Phase 4 artifact is. The file hash below moves whenever the
        # clock does, because the records carry their own provenance.
        "channels_logical_sha256": ue.canonical_sha256(payload_channels),
    }

    UI_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"manifest": queue_manifest, "channels": payload_channels}
    QUEUE_JS_PATH.write_text(
        "// Generated by scripts/phase4_workbench_review_export.py -- do not "
        "edit by hand.\n"
        "window.WORKBENCH_REVIEW_QUEUE = "
        + json.dumps(payload, ensure_ascii=False, sort_keys=True) + ";\n",
        encoding="utf-8")
    queue_manifest["payload_sha256"] = digest_file(QUEUE_JS_PATH)
    QUEUE_MANIFEST_PATH.write_text(
        json.dumps(queue_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    size_mb = QUEUE_JS_PATH.stat().st_size / (1 << 20)
    report = [
        "# Phase 4 — workbench review queue",
        "",
        f"**Policy:** `{QUEUE_POLICY}` · contract "
        f"`unresolved_evidence_contract` v{ue.CONTRACT_VERSION} · every record "
        "`NOT_CORPUS_TRUTH`.",
        "",
        "A queue is a **view** over ratified artifacts. Nothing here modifies "
        "an occurrence, a cluster proposal, or an accepted hash, and exclusion "
        "from the queue is not a judgment that a cluster is uninteresting.",
        "",
        "## What the queue shows, and what it does not",
        "",
        "| channel | proposals | contentless | below min length | eligible | queued |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for scope, counts in policy_counts.items():
        report.append(
            f"| `{scope}` | {counts['proposals_available']:,} | "
            f"{counts['excluded_contentless_sequence']:,} | "
            f"{counts['excluded_below_min_sequence_length']:,} | "
            f"{counts['eligible_after_exclusions']:,} | {counts['queued']:,} |")
    same = policy_counts["SAME_LANGUAGE_AS_QUERY"]
    report += [
        "",
        "## Language selection",
        "",
    ]
    if language_selection:
        report += [
            f"This queue is restricted to **{', '.join(sorted(language_selection))}** "
            "and is therefore a single-language review surface.",
            "",
            "The test is *declares at least one requested language*, and it "
            "means different things per channel by construction. In "
            "`SAME_LANGUAGE_AS_QUERY` clusters are single-language, so the "
            "queue is wholly in the requested language. In "
            "`CROSS_LANGUAGE_PARALLEL` clusters span languages, so the queue "
            "is clusters that *involve* it — their other members are in other "
            "languages by design, which is the point of the channel.",
            "",
            "| channel | contentful | off-language | eligible | queued |",
            "|---|---:|---:|---:|---:|",
        ]
        for scope, counts in policy_counts.items():
            report.append(
                f"| `{scope}` | {counts['contentful_before_language_selection']:,} | "
                f"{counts['excluded_off_language']:,} | "
                f"{counts['eligible_after_exclusions']:,} | {counts['queued']:,} |")
    else:
        report += [
            "No language selection was applied, so this queue spans every "
            "language. Because ranking is by sequence length and Hittite is "
            "~89% of lexical tokens, an unrestricted queue is overwhelmingly "
            "Hittite; the browser's language filter narrows *this* queue and "
            "cannot reach material the queue never contained. Use "
            "`--language Akk` (repeatable, or comma-separated) to build a "
            "genuine single-language session.",
        ]
    report += [
        "",
        "Contentful clusters available per language, before any selection — "
        "the ceiling on what a single-language session could contain:",
        "",
        "| channel | " + " | ".join(
            f"`{code}`" for code in
            sorted({lang for counts in policy_counts.values()
                    for lang in counts["contentful_clusters_by_language"]})) + " |",
        "|---" * (1 + len({lang for counts in policy_counts.values()
                           for lang in counts["contentful_clusters_by_language"]}))
        + "|",
    ]
    all_langs = sorted({lang for counts in policy_counts.values()
                        for lang in counts["contentful_clusters_by_language"]})
    for scope, counts in policy_counts.items():
        cells = " | ".join(
            f"{counts['contentful_clusters_by_language'].get(lang, 0):,}"
            for lang in all_langs)
        report.append(f"| `{scope}` | {cells} |")
    report += [
        "",
        "**A single-language session is a review surface, not a prediction "
        "surface.** No per-language calibration exists. Nothing in this "
        "project licenses transferring a rate fit on one language to another, "
        "and the sparser languages here (`Pal`, `Sum`, `Luw`) do not have the "
        "composition mass to support a leakage-safe calibration at all.",
        "",
        "### Two exclusions, both awaiting ratification",
        "",
        "**Contentless sequences.** A cluster whose shared sequence is nothing "
        f"but placeholder characters (`{''.join(sorted(CONTENTLESS_CHARS))}` — "
        "the illegible `x`, the indeterminate filler `_`, editorial "
        "parentheses) groups occurrences by the absence of a reading. That "
        "gives an expert nothing to compare, and it is what produces the "
        "95,530-member proposal that would otherwise open the interface. Same-"
        f"language channel: {same['excluded_contentless_sequence']:,} cluster(s)"
        f" covering {same['excluded_contentless_occurrences']:,} occurrence(s).",
        "",
        f"**Sequences shorter than {args.min_sequence_length} signs.** Ranking "
        "an earlier draft of this queue by document count alone put the single "
        "signs `a` (3,542 documents), `i`, and `e` at the top. A damaged common "
        "sign appears everywhere; shared-sequence evidence gets its force from "
        "specificity, not from recurrence alone. This is the second Zipfian "
        "floor, one level up from `x`. Same-language channel: "
        f"{same['excluded_below_min_sequence_length']:,} cluster(s) covering "
        f"{same['excluded_below_min_occurrences']:,} occurrence(s).",
        "",
        "Both are **display policies**, not findings. Nothing excluded here is "
        "judged uninteresting, deleted, or altered; illegible runs and single "
        "signs remain in the extraction, and a future queue keyed on "
        "surrounding context rather than shared surface form would reach them. "
        "The pair needs Ixca's ratification before the queue is used for real "
        "expert labor, because they decide what a specialist is shown.",
        "",
        "### Sampling within a cluster",
        "",
        f"At most **{MAX_MEMBERS_DISPLAYED}** members are rendered per cluster, "
        "beside the cluster's true `member_count`. The interface must present "
        "this as a sample; a reviewed cluster is never a fully-seen cluster.",
        "",
        f"At most **{args.max_clusters}** clusters per channel are exported, to "
        "bound the browser payload. The remainder is unqueued, not rejected.",
        "",
        "## Payload",
        "",
        f"- `{QUEUE_JS_PATH.as_posix()}` — {size_mb:.2f} MB",
        f"- content hash `{queue_manifest['channels_logical_sha256']}` "
        "(stable across rebuilds)",
        f"- file hash `{queue_manifest['payload_sha256']}` (moves with the "
        "clock; the records carry their own provenance)",
        "- Whole canonical records travel with the queue, so the browser hashes "
        "the same bytes that are on disk; a display object would bind an "
        "expert's judgment to something unverifiable.",
        "",
        "## Source artifacts (unmodified)",
        "",
    ]
    for key, value in accepted_hashes.items():
        report.append(f"- `{key}`: `{value}`")
    report += [
        "",
        "## Standing display rules for any interface built on this queue",
        "",
        "1. Same-language is the default channel; cross-language is shown only "
        "as a visibly enabled alternative.",
        "2. No count or member total may be presented as a probability.",
        "3. Contradictory evidence attached to a proposal is always rendered.",
        "4. Withhold judgment is always available.",
        "5. The screen states that the queue is a subset, with these counts.",
        "",
    ]
    QUEUE_REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(f"  queue     -> {QUEUE_JS_PATH} ({size_mb:.2f} MB)")
    print(f"  manifest  -> {QUEUE_MANIFEST_PATH}")
    print(f"  report    -> {QUEUE_REPORT_PATH}")


if __name__ == "__main__":
    main()
