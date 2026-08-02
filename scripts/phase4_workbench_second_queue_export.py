#!/usr/bin/env python3
"""P4-E2 handoff item 4: the second queue.

`scripts/phase4_workbench_review_export.py` ranks by sequence length, which
structurally cannot surface two populations named in
`reports/phase4_p4e2_expert_interface.md` (open decision 3) and
`reports/phase5_p4e2_queue_policy_ratification.md` ("the real question ...
is where it now sits"):

- **468-599 rare single-sign clusters** (same-language, <=2 documents):
  they exist as real clusters, but length-descending ranking can never lift
  a single-sign cluster into a 60-cluster window, so they are unreachable
  no matter how the minimum-sequence-length rule is set. `RARE_BY_RARITY`
  is the SAME candidate pool the first queue reads, re-ranked by rarity
  (fewest documents first) instead of by length. Nothing is reclustered.

- **~13,900 ungrouped occurrences** whose sequence is unique, so they never
  form a cluster in the first queue's exact-sequence channel at all.
  `LOCAL_CONTEXT_PARALLEL` is a genuinely new channel
  (`scripts/phase4_unresolved_clustering.py --local-context`), grouping
  them by their immediate flanking attested tokens instead of by their own
  content -- specs/UNRESOLVED_EVIDENCE_WORKBENCH.md's second named channel
  ("local left/right textual context"), not previously implemented.

Deliberately separate from the first queue's output, not a mode on it:
`Phase4/phase4_out/workbench_ui_out/workbench_review_queue.js`'s content hash
is a pinned invariant elsewhere in this project ("if it moves without a
deliberate policy change, something altered what a specialist sees" --
PHASE5_SUCCESSOR_HANDOFF.md). This script reads the first queue's ratified
helpers by import, never modifies its file, and writes to its own path.

Both channels reuse `configs/p4e2_queue_policy.json`'s ratified
contentless-sequence exclusion (measured to be load-bearing here too --
see reports/phase5_second_queue.md). Neither applies the deferred minimum-
sequence-length rule: `RARE_BY_RARITY` exists specifically to admit what
that rule's length-descending sibling suppresses, and
`LOCAL_CONTEXT_PARALLEL` has no single "cluster sequence" for the rule to
apply to in the first place.

Usage:
    python scripts/phase4_workbench_second_queue_export.py
    python scripts/phase4_workbench_second_queue_export.py --max-clusters 40
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

import evidence_policy as ep  # noqa: E402
import unresolved_evidence as ue  # noqa: E402

import phase4_workbench_review_export as wexp  # noqa: E402

SEED = 20260802
POLICY_NAME = "transcription_assisted"

OUT_DIR = Path("Phase4/phase4_out")
UI_DIR = OUT_DIR / "workbench_ui_out"
OCCURRENCES_PATH = OUT_DIR / "unresolved_occurrences.parquet"
LOCAL_CONTEXT_CANDIDATES_PATH = (
    OUT_DIR / "unresolved_similarity_candidates_local_context.jsonl")
SAME_LANGUAGE_CANDIDATES_PATH = wexp.CANDIDATES["SAME_LANGUAGE_AS_QUERY"]
SPLITS_PATH = wexp.SPLITS_PATH
CLUSTER_MANIFEST_PATH = wexp.CLUSTER_MANIFEST_PATH
CONTENTLESS_CHARS = wexp.CONTENTLESS_CHARS
MAX_MEMBERS_DISPLAYED = wexp.MAX_MEMBERS_DISPLAYED
MAX_CLUSTERS_PER_CHANNEL = wexp.MAX_CLUSTERS_PER_CHANNEL
CONTEXT_LINES = wexp.CONTEXT_LINES
TOKENS_V2_PATH = wexp.TOKENS_V2_PATH

QUEUE_JS_PATH = UI_DIR / "workbench_second_queue.js"
QUEUE_MANIFEST_PATH = UI_DIR / "workbench_second_queue_manifest.json"
QUEUE_REPORT_PATH = UI_DIR / "workbench_second_queue_report.md"


# ----------------------------------------------------------- RARE_BY_RARITY
# Reads the SAME candidate file the first queue's SAME_LANGUAGE_AS_QUERY
# channel reads; only the ranking differs. wexp's own accessors apply
# directly since the evidence type (EXACT_NORMALIZED_SIGN_SEQUENCE) is
# unchanged.

def tiebreak(cluster_id):
    """Deterministic, reproducible, and NOT alphabetical.

    Every ranking below ties on its real keys across a group in the
    thousands (e.g. every RARE_BY_RARITY cluster at the minimum possible
    distinct_document_count=1, member_count=2). Breaking that tie on
    cluster_id -- a string sort -- reproduces the exact mistake
    reports/phase5_p4e2_queue_policy_ratification.md already found and
    named: "I first eyeballed the rare single-sign tail ... I was reading
    an alphabetically sorted sample," which put every punctuation-leading
    token ('i, :a, _bu) at the top of a set that is 79.1% plain sign
    readings. A SHA-256 of the cluster_id has no relationship to sequence
    content, so it cannot reintroduce that bias, and it is stable across
    reruns without needing Python's per-process-randomized hash() or a
    stateful random.shuffle() (deferred-issues-sweep already flagged
    hash() as a source of silent nondeterminism elsewhere in this repo).
    Not a claim that any one ordering within a tied group is "more
    correct" -- just that alphabetical is a specific wrong one to default
    to by accident."""
    return hashlib.sha256(f"{SEED}:{cluster_id}".encode()).hexdigest()


def rarity_rank_key(proposal):
    """Opposite of wexp.rank_key by design: this channel exists to surface
    what length-first ranking structurally cannot reach. Fewest documents
    first, then fewest members -- both dimensions biased toward LESS
    evidence, since "rare" means minimal, not merely short."""
    return (
        wexp.distinct_document_count(proposal),
        len(proposal["member_occurrence_ids"]),
        tiebreak(proposal["cluster_id"]),
    )


# ------------------------------------------------------ LOCAL_CONTEXT_PARALLEL
# A different evidence type (LOCAL_LEFT_RIGHT_CONTEXT), so wexp's sequence-
# keyed accessors do not apply; small parallel accessors below mirror them.

def context_left(proposal):
    for evidence in proposal.get("supporting_evidence", []):
        if evidence.get("type") == "LOCAL_LEFT_RIGHT_CONTEXT":
            return evidence.get("left", "")
    return ""


def context_right(proposal):
    for evidence in proposal.get("supporting_evidence", []):
        if evidence.get("type") == "LOCAL_LEFT_RIGHT_CONTEXT":
            return evidence.get("right", "")
    return ""


def context_is_contentless(proposal):
    """True when EITHER flanking side carries no reading at all. A cluster
    keyed on 'flanked by illegible on both sides' groups occurrences by an
    absence, the same defect the first queue's contentless rule targets --
    measured here too (reports/phase5_second_queue.md): 283 of 1,240
    clusters, 32% of members, before this filter."""
    for side in (context_left(proposal), context_right(proposal)):
        side = side.strip()
        if not side or all(char in CONTENTLESS_CHARS for char in side):
            return True
    return False


def context_distinct_document_count(proposal):
    for evidence in proposal.get("supporting_evidence", []):
        if evidence.get("type") == "LOCAL_LEFT_RIGHT_CONTEXT":
            return int(evidence.get("distinct_document_count", 0))
    return 0


def context_languages(proposal):
    for evidence in proposal.get("supporting_evidence", []):
        if evidence.get("type") == "LOCAL_LEFT_RIGHT_CONTEXT":
            return [lang or wexp.UNRESOLVED_LANGUAGE
                    for lang in evidence.get("languages", [])]
    return []


def context_rank_key(proposal):
    """Opposite bias from rarity_rank_key by design: this channel is not
    about how rare the CONTENT is, it is about how well-supported the SLOT
    is -- more independent documents landing on the identical immediate
    environment is stronger evidence about that environment, not weaker."""
    return (
        -context_distinct_document_count(proposal),
        -len(proposal["member_occurrence_ids"]),
        tiebreak(proposal["cluster_id"]),
    )


def build_channel(proposals, *, contentless_fn, rank_fn, max_clusters):
    contentless = [p for p in proposals if contentless_fn(p)]
    eligible = [p for p in proposals if not contentless_fn(p)]
    eligible.sort(key=rank_fn)
    queued = eligible[:max_clusters]
    return {
        "queued": queued,
        "counts": {
            "proposals_available": len(proposals),
            "excluded_contentless": len(contentless),
            "excluded_contentless_occurrences": sum(
                len(p["member_occurrence_ids"]) for p in contentless),
            "eligible_after_exclusions": len(eligible),
            "queued": len(queued),
            "not_queued_payload_bound": max(0, len(eligible) - len(queued)),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-clusters", type=int, default=MAX_CLUSTERS_PER_CHANNEL,
        help="clusters exported per channel (payload bound, not a judgment "
             "about the remainder) -- same provisional default as the first "
             "queue; 'queue size' is still an open decision there too")
    args = parser.parse_args()

    for path in (OCCURRENCES_PATH, TOKENS_V2_PATH, SPLITS_PATH,
                 SAME_LANGUAGE_CANDIDATES_PATH, LOCAL_CONTEXT_CANDIDATES_PATH):
        if not path.exists():
            missing_local_context = path == LOCAL_CONTEXT_CANDIDATES_PATH
            raise SystemExit(
                f"{path} not found. Run "
                + ("scripts/phase4_unresolved_clustering.py --local-context"
                   if missing_local_context
                   else "scripts/phase4_unresolved_extraction.py and "
                        "scripts/phase4_unresolved_clustering.py")
                + " first.")

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

    rarity = build_channel(
        wexp.load_proposals(SAME_LANGUAGE_CANDIDATES_PATH),
        contentless_fn=wexp.sequence_is_contentless,
        rank_fn=rarity_rank_key, max_clusters=args.max_clusters)
    context = build_channel(
        wexp.load_proposals(LOCAL_CONTEXT_CANDIDATES_PATH),
        contentless_fn=context_is_contentless,
        rank_fn=context_rank_key, max_clusters=args.max_clusters)
    channels = {"RARE_BY_RARITY": rarity, "LOCAL_CONTEXT_PARALLEL": context}
    for scope, channel in channels.items():
        c = channel["counts"]
        print(f"{scope}: {c['proposals_available']:,} proposals -> "
              f"{c['queued']:,} queued ({c['excluded_contentless']:,} "
              "contentless excluded)")

    needed_ids = set()
    for channel in channels.values():
        for proposal in channel["queued"]:
            needed_ids.update(
                proposal["member_occurrence_ids"][:MAX_MEMBERS_DISPLAYED])
    missing = sorted(needed_ids - set(records))
    if missing:
        raise SystemExit(
            f"{len(missing)} queued member id(s) absent from the occurrence "
            f"table, e.g. {missing[:3]}; the candidate files and the "
            "occurrence table are out of step -- rebuild both.")

    line_targets, doc_ids = set(), set()
    for occurrence_id in needed_ids:
        location = records[occurrence_id]["location"]
        doc_id, line_index = location["doc_id"], location["line_index_in_doc"]
        doc_ids.add(doc_id)
        if line_index is None:
            continue
        for offset in range(-CONTEXT_LINES, CONTEXT_LINES + 1):
            line_targets.add((doc_id, int(line_index) + offset))
    print(f"Context: {len(line_targets):,} line(s) across "
          f"{len(doc_ids):,} document(s)")
    lines = wexp.build_line_index(doc_ids, line_targets)

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
            "record": record,
            "catalog": {
                "cth": meta.get("cth"), "site": meta.get("site"),
                "is_bin": meta.get("is_bin"),
                "evidence_class": "CATALOG_METADATA",
            },
            "context_lines": {"before": before, "after": after},
        }

    payload_channels = {}
    for scope, channel in channels.items():
        payload_channels[scope] = [{
            "proposal": proposal,
            "member_count": len(proposal["member_occurrence_ids"]),
            "members_displayed": min(
                MAX_MEMBERS_DISPLAYED, len(proposal["member_occurrence_ids"])),
            "members": [
                member_view(occurrence_id) for occurrence_id
                in proposal["member_occurrence_ids"][:MAX_MEMBERS_DISPLAYED]
            ],
        } for proposal in channel["queued"]]

    cluster_manifest = json.loads(
        CLUSTER_MANIFEST_PATH.read_text(encoding="utf-8"))
    accepted_hashes = {
        "occurrences_logical_sha256":
            cluster_manifest["workbench"]["occurrences_logical_sha256"],
        "contract_version": ue.CONTRACT_VERSION,
        "SAME_LANGUAGE_AS_QUERY_candidates_logical_sha256":
            cluster_manifest.get("clustering", {}).get(
                "SAME_LANGUAGE_AS_QUERY", {}).get("candidates_logical_sha256"),
        "LOCAL_CONTEXT_PARALLEL_candidates_logical_sha256":
            cluster_manifest.get("clustering", {}).get(
                "LOCAL_CONTEXT_PARALLEL", {}).get("candidates_logical_sha256"),
    }

    category_counts = Counter()
    language_counts = Counter()
    language_counts_by_channel = {}
    for scope, queued in payload_channels.items():
        scope_counts = Counter()
        for cluster in queued:
            for member in cluster["members"]:
                category_counts.update(member["record"]["categories"])
                effective = (member["record"]["language"]["effective"]
                             or wexp.UNRESOLVED_LANGUAGE)
                language_counts.update([effective])
                scope_counts.update([effective])
        language_counts_by_channel[scope] = dict(sorted(scope_counts.items()))

    queue_manifest = {
        "task": "phase4_workbench_second_queue_export",
        "queue_policy": wexp.QUEUE_POLICY,
        "contract_version": ue.CONTRACT_VERSION,
        "ground_truth_status": "NOT_CORPUS_TRUTH",
        "corpus_version": "TLHdig_0.2.0-beta",
        "evidence_policy": POLICY_NAME,
        "seed": SEED,
        "git_commit": ep._git_commit(),
        "source_hashes": accepted_hashes,
        "split_manifest_hash": wexp.digest_file(SPLITS_PATH),
        "policy_parameters": {
            "contentless_chars": "".join(sorted(CONTENTLESS_CHARS)),
            "minimum_sequence_length_rule": (
                "not applied in this queue -- see module docstring"),
            "local_context_window": 1,
            "max_members_displayed_per_cluster": MAX_MEMBERS_DISPLAYED,
            "max_clusters_per_channel": args.max_clusters,
            "context_lines_per_side": CONTEXT_LINES,
            "ranking": {
                "RARE_BY_RARITY":
                    "distinct_document_count asc, member_count asc, "
                    "cluster_id asc",
                "LOCAL_CONTEXT_PARALLEL":
                    "distinct_document_count desc, member_count desc, "
                    "cluster_id asc",
            },
        },
        "channel_counts": {scope: channel["counts"]
                           for scope, channel in channels.items()},
        "queued_member_category_counts": dict(sorted(category_counts.items())),
        "queued_member_language_counts": dict(sorted(language_counts.items())),
        "queued_member_language_counts_by_channel": language_counts_by_channel,
        "selection_is_a_view_not_a_finding": (
            "Exclusion from this queue is a display decision. No occurrence, "
            "proposal, or hash is modified, and an excluded cluster is not "
            "thereby judged uninteresting."),
        "relationship_to_first_queue": (
            "A separate queue, not a mode on the first. "
            "workbench_review_queue.js and its channels_logical_sha256 are "
            "untouched by this script."),
        "default_channel": "RARE_BY_RARITY",
        "channels_logical_sha256": ue.canonical_sha256(payload_channels),
    }

    UI_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"manifest": queue_manifest, "channels": payload_channels}
    QUEUE_JS_PATH.write_text(
        "// Generated by scripts/phase4_workbench_second_queue_export.py -- "
        "do not edit by hand.\n"
        "window.WORKBENCH_SECOND_QUEUE = "
        + json.dumps(payload, ensure_ascii=False, sort_keys=True) + ";\n",
        encoding="utf-8")
    queue_manifest["payload_sha256"] = wexp.digest_file(QUEUE_JS_PATH)
    QUEUE_MANIFEST_PATH.write_text(
        json.dumps(queue_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    size_mb = QUEUE_JS_PATH.stat().st_size / (1 << 20)
    report = [
        "# Phase 4/5 — the second workbench queue",
        "",
        f"**Policy:** `{wexp.QUEUE_POLICY}` (contentless-sequence exclusion "
        "reused; minimum-sequence-length NOT applied here, see below) · "
        f"contract `unresolved_evidence_contract` v{ue.CONTRACT_VERSION} · "
        "every record `NOT_CORPUS_TRUTH`.",
        "",
        "A separate queue from `workbench_review_queue.js`, covering two "
        "populations that queue's length-first ranking and exact-sequence "
        "clustering structurally cannot reach. See "
        "`reports/phase5_second_queue.md` for the full design writeup and "
        "the measurements behind every choice below.",
        "",
        "## Channels",
        "",
        "| channel | proposals | contentless excluded | eligible | queued |",
        "|---|---:|---:|---:|---:|",
    ]
    for scope, channel in channels.items():
        c = channel["counts"]
        report.append(
            f"| `{scope}` | {c['proposals_available']:,} | "
            f"{c['excluded_contentless']:,} | "
            f"{c['eligible_after_exclusions']:,} | {c['queued']:,} |")
    report += [
        "",
        "### `RARE_BY_RARITY`",
        "",
        "Same candidate pool as the first queue's `SAME_LANGUAGE_AS_QUERY` "
        "channel (`unresolved_similarity_candidates.jsonl`), re-ranked by "
        "ascending distinct-document-count instead of descending sequence "
        "length. Nothing is reclustered and no hash the first queue depends "
        "on is touched. Ranked by rarity, most of the top of this queue is "
        "single-sign material, largely Sumerograms — the population named "
        "in `reports/phase5_p4e2_queue_policy_ratification.md`.",
        "",
        "### `LOCAL_CONTEXT_PARALLEL`",
        "",
        "A genuinely new clustering channel "
        "(`scripts/phase4_unresolved_clustering.py --local-context`): "
        "occurrences with no same-language sequence peer, grouped instead by "
        "the single immediately-adjacent attested token on each side. "
        "Measured before choosing the window "
        "(`reports/phase5_second_queue.md`): requiring two full tokens "
        "collapses the yield from 4,089 occurrences to 73. Ranked by "
        "descending distinct-document-count — the opposite bias from "
        "`RARE_BY_RARITY`, because this channel's value is a well-supported "
        "SLOT, not a rare CONTENT.",
        "",
        "## What this queue does not do",
        "",
        "- The deferred `minimum_sequence_length` rule from "
        "`configs/p4e2_queue_policy.json` is **not applied** in either "
        "channel here — `RARE_BY_RARITY` exists specifically to admit what "
        "that rule's sibling (length-descending ranking) suppresses, and "
        "`LOCAL_CONTEXT_PARALLEL` clusters carry no single \"cluster "
        "sequence\" for the rule to test.",
        "- `--language` selection and a `CROSS_LANGUAGE_PARALLEL`-style "
        "channel are not implemented for this queue. Both are straightforward "
        "extensions of the first queue's existing machinery if wanted; not "
        "built here because neither was named in the two populations this "
        "queue was scoped to close.",
        "- **Queue size (60/channel) is inherited, not re-ratified.** The "
        "first queue's own P4-E2 report flags this as still open; this queue "
        "did not resolve it, only reused the same provisional default.",
        "",
        "## Payload",
        "",
        f"- `{QUEUE_JS_PATH.as_posix()}` — {size_mb:.2f} MB",
        f"- content hash `{queue_manifest['channels_logical_sha256']}` "
        "(stable across rebuilds)",
        f"- file hash `{queue_manifest['payload_sha256']}` (moves with the "
        "clock; the records carry their own provenance)",
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
        "1. No count or member total may be presented as a probability.",
        "2. Contradictory evidence attached to a proposal is always rendered.",
        "3. Withhold judgment is always available.",
        "4. The screen states that the queue is a subset, with these counts.",
        "5. This queue and the first queue are separate views; a specialist "
        "session should say which one produced a given judgment.",
        "",
    ]
    QUEUE_REPORT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(f"  queue     -> {QUEUE_JS_PATH} ({size_mb:.2f} MB)")
    print(f"  manifest  -> {QUEUE_MANIFEST_PATH}")
    print(f"  report    -> {QUEUE_REPORT_PATH}")


if __name__ == "__main__":
    main()
