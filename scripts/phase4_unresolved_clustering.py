#!/usr/bin/env python3
"""P4-E: deterministic same-language cluster proposals over occurrences.

Groups unresolved occurrences that share an exact normalized sign sequence,
within the same effective language by default. This is the simplest of the
typed channels named in `specs/UNRESOLVED_EVIDENCE_WORKBENCH.md` -- exact or
normalized sign sequence -- and it is deliberately first, because it needs no
model and its output can be checked by eye.

Three properties the contract insists on, implemented rather than promised:

- **Same-language grouping by default.** Clusters are built per effective
  language. A cross-language grouping is a separate, explicitly enabled
  channel (`--cross-language`) that emits its own records with
  `language_scope: CROSS_LANGUAGE_PARALLEL`, so an expert can always tell
  which kind of evidence they are looking at.

- **Suggestions, not findings.** Every record is `SYSTEM_PROPOSAL` /
  `NOT_CORPUS_TRUTH` with `scores_are_probabilities: false` -- system-proposed
  rather than model-proposed, because this channel is deterministic string
  matching and no model is consulted (contract 1.1.0). The match count is a
  count, never a confidence.

- **Unresolved-language occurrences are not silently pooled.** They form
  their own `<UNRESOLVED>` bucket instead of being swept into a majority
  language, per the charter's "code-switched and unresolved contexts are a
  named stratum" rule.

Usage:
    python scripts/phase4_unresolved_clustering.py
    python scripts/phase4_unresolved_clustering.py --cross-language
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

SEED = 20260726
POLICY_NAME = "transcription_assisted"
MIN_CLUSTER_SIZE = 2
MAX_CLUSTERS_EMITTED = 5000

OUT_DIR = Path("Phase4/phase4_out")
OCCURRENCES_PATH = OUT_DIR / "unresolved_occurrences.parquet"
# The two channels write to different files. Sharing one path would let a
# cross-language run silently replace the same-language evidence an expert was
# working from -- the two must stay separable on disk, not just in a field.
CANDIDATES_PATH = OUT_DIR / "unresolved_similarity_candidates.jsonl"
CROSS_CANDIDATES_PATH = (
    OUT_DIR / "unresolved_similarity_candidates_cross_language.jsonl")
# `--local-context` is a third, separately written channel (same reasoning as
# the cross-language split above): it groups occurrences the first two
# channels cannot reach at all -- see build_context_clusters().
LOCAL_CONTEXT_CANDIDATES_PATH = (
    OUT_DIR / "unresolved_similarity_candidates_local_context.jsonl")
# Measured, not guessed (reports/phase5_second_queue.md): among the ~13,900
# occurrences with no same-language sequence peer, requiring the single
# immediately-adjacent attested token on each side to match admits 4,089 of
# them into 1,240 clusters. Two full tokens on each side collapses the yield
# to 73 -- Hittite scribal formulae are short enough that anything stricter
# is not "more precise," it is "empty."
LOCAL_CONTEXT_WINDOW = 1
SNAPSHOT_PATH = OUT_DIR / "unresolved_cluster_snapshot.parquet"
EVENTS_PATH = OUT_DIR / "expert_annotation_events.jsonl"
MANIFEST_PATH = OUT_DIR / "unresolved_extraction_manifest.json"
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
CONFIG_PATH = Path("configs/language_layers_v2.json")
REGISTRY_PATH = Path("configs/evidence_registry.yaml")
POLICIES_PATH = Path("configs/evidence_policies.yaml")
TOKENS_V2_PATH = OUT_DIR / "multilingual_tokens_v2.parquet"


def digest_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_hash(proposals):
    """Content hash over the stable identity of every cluster proposal.

    Mirrors `phase4_unresolved_extraction.logical_hash`, and exists for the
    same reason. A hash of the candidates FILE is not usable here: every record
    in that file embeds `provenance.created_utc` and `git_commit`, so it changes
    on every rerun by construction and cannot distinguish a real content change
    from the clock advancing. Provenance is excluded here: WHEN a grouping was
    proposed is not part of WHAT it groups.
    """
    digest = hashlib.sha256()
    for item in sorted(proposals, key=lambda p: p["cluster_id"]):
        stable = {
            key: item[key] for key in
            ("cluster_id", "member_occurrence_ids", "method", "status",
             "language_scope", "supporting_evidence", "contradictory_evidence",
             "scores_are_probabilities", "ground_truth_status")
        }
        digest.update(json.dumps(
            stable, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


def normalized_sequence(tokens):
    """Case-folded sign sequence used as the exact-match key.

    Normalization is limited to case: anything more aggressive (stripping
    uncertainty markers, collapsing determinatives) would merge occurrences an
    expert needs to keep apart, and the marker is often the very thing under
    review.
    """
    return tuple(token.casefold() for token in tokens)


def load_occurrences():
    frame = pd.read_parquet(OCCURRENCES_PATH, columns=[
        "occurrence_id", "categories", "doc_id", "effective_language",
        "main_split", "record"])
    rows = []
    for row in frame.itertuples(index=False):
        record = json.loads(row.record)
        rows.append({
            "occurrence_id": row.occurrence_id,
            # Parquet returns NaN for a null language; normalize to None so an
            # unresolved occurrence sorts and buckets as a named stratum
            # rather than blowing up on a float/str comparison.
            "language": (None if pd.isna(row.effective_language)
                         else row.effective_language),
            "doc_id": row.doc_id,
            "main_split": row.main_split,
            "categories": list(row.categories),
            "tokens": record["display"].get("tokens", []),
            "left": record["context"].get("left", []),
            "right": record["context"].get("right", []),
        })
    return rows


def build_clusters(rows, *, cross_language):
    """Group by exact normalized sequence, within or across language."""
    buckets = defaultdict(list)
    for row in rows:
        if not row["tokens"]:
            continue
        sequence = normalized_sequence(row["tokens"])
        language = row["language"] or "<UNRESOLVED>"
        key = (sequence,) if cross_language else (sequence, language)
        buckets[key].append(row)

    clusters = []
    for key, members in sorted(buckets.items(), key=lambda item: str(item[0])):
        if len(members) < MIN_CLUSTER_SIZE:
            continue
        languages = sorted({m["language"] or "<UNRESOLVED>" for m in members})
        if cross_language and len(languages) < 2:
            # Not a cross-language parallel at all; the same-language channel
            # already covers it. Emitting it here would inflate the apparent
            # yield of cross-language assistance.
            continue
        # Occurrences from one document are not independent evidence of a
        # recurring form; record the distinct-document count so an expert can
        # discount a cluster that is really one scribe repeating themselves.
        documents = sorted({m["doc_id"] for m in members})
        clusters.append({
            "sequence": list(key[0]),
            "members": members,
            "languages": languages,
            "documents": documents,
        })
    clusters.sort(
        key=lambda c: (-len(c["documents"]), -len(c["members"]),
                       c["sequence"]))
    return clusters


def ungrouped_by_sequence(rows):
    """Occurrences with no same-language sequence peer at all.

    The exact-sequence channel above requires MIN_CLUSTER_SIZE members
    sharing a sequence; a truly unique sequence never reaches it. This is
    the ~13,900-occurrence population named in
    reports/phase4_p4e2_expert_interface.md's open decision 3 -- computed
    from the SAME same-language buckets build_clusters() uses, not a
    separate reimplementation that could drift from what "ungrouped" means
    there.
    """
    buckets = defaultdict(list)
    for row in rows:
        if not row["tokens"]:
            continue
        key = (normalized_sequence(row["tokens"]), row["language"] or "<UNRESOLVED>")
        buckets[key].append(row)
    return [members[0] for members in buckets.values() if len(members) == 1]


def build_context_clusters(rows, *, window=LOCAL_CONTEXT_WINDOW):
    """Group occurrences with no sequence peer by their immediate flanking
    context instead -- specs/UNRESOLVED_EVIDENCE_WORKBENCH.md's second named
    channel ("local left/right textual context"), distinct from the
    exact-sequence channel build_clusters() implements.

    Two occurrences whose own content differs (or is differently damaged)
    but which sit in the identical immediate environment are evidence about
    the SLOT, not the content -- an expert comparing them is asking "what,
    in general, goes between these two words," which a sequence-keyed
    cluster cannot answer for material with no surface-form match anywhere
    else in the corpus.

    `window` tokens must be present on BOTH sides for an occurrence to
    join -- a one-sided match halves the precision of the signal for a
    yield that measurement showed is not needed at window=1 (4,089 of
    13,901 already join with both sides required).
    """
    candidates = ungrouped_by_sequence(rows)
    buckets = defaultdict(list)
    for row in candidates:
        left = tuple(t.casefold() for t in row["left"][-window:])
        right = tuple(t.casefold() for t in row["right"][:window])
        if len(left) < window or len(right) < window:
            continue
        language = row["language"] or "<UNRESOLVED>"
        buckets[(left, right, language)].append(row)

    clusters = []
    for key, members in sorted(buckets.items(), key=lambda item: str(item[0])):
        if len(members) < MIN_CLUSTER_SIZE:
            continue
        documents = sorted({m["doc_id"] for m in members})
        clusters.append({
            "left": list(key[0]),
            "right": list(key[1]),
            "language": key[2],
            "members": members,
            "documents": documents,
        })
    # Opposite ranking philosophy from build_clusters() by design: that
    # channel already favors well-attested material, so this one favors
    # what it does NOT surface -- more corroborating members first, since
    # unlike the rarity channel below this is about how well-supported the
    # SLOT is, not how rare the content in it is.
    clusters.sort(
        key=lambda c: (-len(c["documents"]), -len(c["members"]),
                        c["left"], c["right"]))
    return clusters


def run_local_context(args):
    """Self-contained so the exact-sequence code path above is never touched
    by this channel's presence -- same reasoning as keeping same-line and
    cross-line real-gap calibration structurally separate: two populations
    that must never be pooled are safer kept in two code paths than merged
    into one with a flag threaded through every line."""
    del args  # no local-context-specific CLI options today
    rows = load_occurrences()
    print(f"Occurrences loaded: {len(rows):,}")

    ungrouped = ungrouped_by_sequence(rows)
    print(f"Occurrences with no same-language sequence peer: {len(ungrouped):,}")

    clusters = build_context_clusters(rows)
    scope = "SAME_LANGUAGE_AS_QUERY"
    method = f"local_left_right_context_k{LOCAL_CONTEXT_WINDOW}"
    joined = sum(len(c["members"]) for c in clusters)
    print(f"Clusters (LOCAL_CONTEXT_PARALLEL, window={LOCAL_CONTEXT_WINDOW}): "
          f"{len(clusters):,} ({joined:,} of {len(ungrouped):,} ungrouped "
          "occurrences join one)")

    provenance = ue.build_provenance(
        split_manifest_hash=digest_file(SPLITS_PATH),
        language_layer_hash=digest_file(TOKENS_V2_PATH),
        config_hash=digest_file(CONFIG_PATH),
        git_commit=ep._git_commit(),
        seed=SEED,
        evidence_policy=POLICY_NAME,
    )

    emitted = []
    for index, cluster in enumerate(clusters[:MAX_CLUSTERS_EMITTED], 1):
        members = cluster["members"]
        proposal = ue.build_cluster_proposal(
            cluster_id=f"ctx-s-{index:05d}",
            member_occurrence_ids=[m["occurrence_id"] for m in members],
            method_name=method,
            evidence_class="EDITORIAL_TRANSCRIPTION",
            model_derived=False,
            language_scope=scope,
            supporting_evidence=[{
                "type": "LOCAL_LEFT_RIGHT_CONTEXT",
                "left": " ".join(cluster["left"]),
                "right": " ".join(cluster["right"]),
                "context_window": LOCAL_CONTEXT_WINDOW,
                "member_count": len(members),
                "distinct_document_count": len(cluster["documents"]),
                "languages": [cluster["language"]],
                "value_is_a_count_not_a_score": True,
            }],
            contradictory_evidence=[{
                "type": "SINGLE_DOCUMENT_CLUSTER",
                "summary": (
                    "Every member comes from one document, so this may be one "
                    "scribe repeating a form rather than a recurring one."),
            }] if len(cluster["documents"]) == 1 else [],
            provenance=provenance,
        )
        emitted.append(proposal)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_CONTEXT_CANDIDATES_PATH, "w", encoding="utf-8") as handle:
        for proposal in emitted:
            handle.write(json.dumps(
                proposal, ensure_ascii=False, sort_keys=True) + "\n")

    size_histogram = Counter(
        len(proposal["member_occurrence_ids"]) for proposal in emitted)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest.setdefault("clustering", {})["LOCAL_CONTEXT_PARALLEL"] = {
        "method": method,
        "model_derived": False,
        "context_window": LOCAL_CONTEXT_WINDOW,
        "ungrouped_by_sequence_count": len(ungrouped),
        "ungrouped_occurrences_joining_a_context_cluster": joined,
        "clusters_found": len(clusters),
        "clusters_emitted": len(emitted),
        "min_cluster_size": MIN_CLUSTER_SIZE,
        "multi_document_clusters": sum(
            1 for cluster in clusters if len(cluster["documents"]) > 1),
        "cluster_size_histogram": dict(sorted(size_histogram.items())),
        "scores_are_probabilities": False,
        "candidates_path": str(LOCAL_CONTEXT_CANDIDATES_PATH),
        "candidates_logical_sha256": logical_hash(emitted),
        "candidates_file_sha256": digest_file(LOCAL_CONTEXT_CANDIDATES_PATH),
        "file_hash_is_not_stable": (
            "Every record embeds provenance.created_utc and git_commit, so "
            "candidates_file_sha256 changes on every rerun regardless of "
            "content; compare candidates_logical_sha256 to check "
            "reproducibility."),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"  emitted {len(emitted):,} proposals to {LOCAL_CONTEXT_CANDIDATES_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cross-language", action="store_true",
        help="emit the explicitly enabled cross-language parallel channel "
             "instead of the same-language default")
    parser.add_argument(
        "--local-context", action="store_true",
        help="emit the local left/right context channel over occurrences "
             "with no same-language sequence peer, instead of the "
             "exact-sequence channel (mutually exclusive with "
             "--cross-language; a separate build, kept as a separate run)")
    args = parser.parse_args()

    if not OCCURRENCES_PATH.exists():
        raise SystemExit(
            f"{OCCURRENCES_PATH} not found. Run "
            "scripts/phase4_unresolved_extraction.py first.")

    if args.local_context:
        run_local_context(args)
        return

    rows = load_occurrences()
    print(f"Occurrences loaded: {len(rows):,}")

    clusters = build_clusters(rows, cross_language=args.cross_language)
    scope = ("CROSS_LANGUAGE_PARALLEL" if args.cross_language
             else "SAME_LANGUAGE_AS_QUERY")
    candidates_path = (CROSS_CANDIDATES_PATH if args.cross_language
                       else CANDIDATES_PATH)
    method = ("exact_normalized_sign_sequence_cross_language"
              if args.cross_language else "exact_normalized_sign_sequence")
    print(f"Clusters ({scope}): {len(clusters):,}")

    provenance = ue.build_provenance(
        split_manifest_hash=digest_file(SPLITS_PATH),
        language_layer_hash=digest_file(TOKENS_V2_PATH),
        config_hash=digest_file(CONFIG_PATH),
        git_commit=ep._git_commit(),
        seed=SEED,
        evidence_policy=POLICY_NAME,
    )

    emitted = []
    for index, cluster in enumerate(clusters[:MAX_CLUSTERS_EMITTED], 1):
        members = cluster["members"]
        sequence = " ".join(cluster["sequence"])
        proposal = ue.build_cluster_proposal(
            cluster_id=f"seq-{'x' if args.cross_language else 's'}-{index:05d}",
            member_occurrence_ids=[m["occurrence_id"] for m in members],
            method_name=method,
            evidence_class="EDITORIAL_TRANSCRIPTION",
            # Deterministic string matching; no model consulted. With
            # model_derived=False the builder assigns SYSTEM_PROPOSAL, so the
            # status itself no longer implies a model was involved.
            model_derived=False,
            language_scope=scope,
            supporting_evidence=[{
                "type": "EXACT_NORMALIZED_SIGN_SEQUENCE",
                "sequence": sequence,
                "member_count": len(members),
                "distinct_document_count": len(cluster["documents"]),
                "languages": cluster["languages"],
                "value_is_a_count_not_a_score": True,
            }],
            contradictory_evidence=[{
                "type": "SINGLE_DOCUMENT_CLUSTER",
                "summary": (
                    "Every member comes from one document, so this may be one "
                    "scribe repeating a form rather than a recurring one."),
            }] if len(cluster["documents"]) == 1 else [],
            provenance=provenance,
        )
        emitted.append(proposal)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(candidates_path, "w", encoding="utf-8") as handle:
        for proposal in emitted:
            handle.write(json.dumps(
                proposal, ensure_ascii=False, sort_keys=True) + "\n")

    # The snapshot is a projection of the append-only event log, never
    # independent state. With no expert events yet it is every occurrence at
    # UNREVIEWED -- which is the correct, honest starting position.
    events = []
    if EVENTS_PATH.exists():
        events = [
            json.loads(line) for line in
            EVENTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        ue.AnnotationEventLog(events).verify_chain()
    snapshot = ue.project_snapshot(
        events, occurrence_ids=[row["occurrence_id"] for row in rows])
    pd.DataFrame([
        {
            "occurrence_id": occurrence_id,
            "status": state["status"],
            "clusters": state["clusters"],
            "hypothesis_count": len(state["hypotheses"]),
        }
        for occurrence_id, state in snapshot["occurrences"].items()
    ]).to_parquet(SNAPSHOT_PATH, index=False)

    status_counts = Counter(
        state["status"] for state in snapshot["occurrences"].values())
    size_histogram = Counter(
        len(proposal["member_occurrence_ids"]) for proposal in emitted)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest.setdefault("clustering", {})[scope] = {
        "method": method,
        "model_derived": False,
        "clusters_found": len(clusters),
        "clusters_emitted": len(emitted),
        "min_cluster_size": MIN_CLUSTER_SIZE,
        "multi_document_clusters": sum(
            1 for cluster in clusters if len(cluster["documents"]) > 1),
        "cluster_size_histogram": dict(sorted(size_histogram.items())),
        "expert_events": len(events),
        "snapshot_status_counts": dict(sorted(status_counts.items())),
        "scores_are_probabilities": False,
        "candidates_path": str(candidates_path),
        "candidates_logical_sha256": logical_hash(emitted),
        "candidates_file_sha256": digest_file(candidates_path),
        "file_hash_is_not_stable": (
            "Every record embeds provenance.created_utc and git_commit, so "
            "candidates_file_sha256 changes on every rerun regardless of "
            "content; compare candidates_logical_sha256 to check "
            "reproducibility."),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"  emitted {len(emitted):,} proposals to {candidates_path}")
    print(f"  snapshot ({len(events)} expert event(s)) -> {SNAPSHOT_PATH}")
    print(f"  status counts: {dict(status_counts)}")


if __name__ == "__main__":
    main()
