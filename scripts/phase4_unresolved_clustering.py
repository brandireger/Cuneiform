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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cross-language", action="store_true",
        help="emit the explicitly enabled cross-language parallel channel "
             "instead of the same-language default")
    args = parser.parse_args()

    if not OCCURRENCES_PATH.exists():
        raise SystemExit(
            f"{OCCURRENCES_PATH} not found. Run "
            "scripts/phase4_unresolved_extraction.py first.")

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
        "candidates_sha256": digest_file(candidates_path),
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"  emitted {len(emitted):,} proposals to {candidates_path}")
    print(f"  snapshot ({len(events)} expert event(s)) -> {SNAPSHOT_PATH}")
    print(f"  status counts: {dict(status_counts)}")


if __name__ == "__main__":
    main()
