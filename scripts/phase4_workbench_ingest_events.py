#!/usr/bin/env python3
"""P4-E2: ingest an exported expert session into the append-only event log.

The workbench interface runs in a browser and cannot write to the event log.
It exports a session file; this script is the only supported way that file
becomes part of the log. Everything the contract cares about is checked here
rather than trusted from the page.

What ingest verifies, and why each check exists:

- **The reviewed record still matches what is on disk.** Every event carries
  `reviewed_record_sha256`, the canonical hash of the record the expert
  actually saw. Ingest recomputes that hash from the current occurrence or
  cluster proposal and refuses on any mismatch. A judgment about a record that
  has since changed is a judgment about something else.

- **The chain is rebuilt onto the real head, not the browser's.** A session
  chains from whatever head it assumed when it opened. The authoritative head
  is on disk and may have moved (another session, a restored backup). Events
  are therefore re-chained here in order. Re-chaining changes an event's own
  hash but never `reviewed_record_sha256`, which is the binding that matters.

- **Nothing is promoted.** Ingested events stay
  `QUARANTINED_EXPERT_JUDGMENT` with `requires_adjudication: true`. Ingest is
  not adjudication, and adjudication is a separate gate that does not exist
  yet by design.

Backups are not optional: the log is append-only and hash-chained, so a lost
file is unrecoverable *and* un-reconstructable. Occurrences rebuild from the
pinned corpus at any time; a specialist's judgments do not. This script
refuses to run when the existing log has never been backed up, unless
`--no-backup-check` is given deliberately.

Usage:
    python scripts/phase4_workbench_ingest_events.py <session.json>
    python scripts/phase4_workbench_ingest_events.py <session.json> --dry-run
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import pandas as pd  # noqa: E402

import unresolved_evidence as ue  # noqa: E402

OUT_DIR = Path("Phase4/phase4_out")
EVENTS_PATH = OUT_DIR / "expert_annotation_events.jsonl"
OCCURRENCES_PATH = OUT_DIR / "unresolved_occurrences.parquet"
LEDGER_PATH = OUT_DIR / "annotation_backups" / "backup_ledger.jsonl"
CANDIDATES = (
    OUT_DIR / "unresolved_similarity_candidates.jsonl",
    OUT_DIR / "unresolved_similarity_candidates_cross_language.jsonl",
)


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line
            in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_reviewable_records(needed_ids):
    """target_id -> the canonical record currently on disk.

    Cluster proposals are small enough to load whole. Occurrences are not, so
    only the ids an incoming session actually references are materialized.
    """
    records = {}
    for path in CANDIDATES:
        for proposal in read_jsonl(path):
            if proposal["cluster_id"] in needed_ids:
                records[proposal["cluster_id"]] = proposal
    outstanding = needed_ids - set(records)
    if outstanding and OCCURRENCES_PATH.exists():
        frame = pd.read_parquet(
            OCCURRENCES_PATH, columns=["occurrence_id", "record"])
        frame = frame[frame["occurrence_id"].isin(outstanding)]
        for row in frame.itertuples(index=False):
            records[row.occurrence_id] = json.loads(row.record)
    return records


def backup_is_current(events):
    """True when the log is empty or its current head is in the backup ledger.

    An empty log has nothing to lose. A log with events that appear in no
    backup is one disk failure away from being gone for good.
    """
    if not events:
        return True
    head = ue.AnnotationEventLog(events).head_sha256()
    return any(entry.get("chain_head_sha256") == head
               for entry in read_jsonl(LEDGER_PATH))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path,
                        help="session JSON exported by the workbench interface")
    parser.add_argument("--dry-run", action="store_true",
                        help="verify everything, write nothing")
    parser.add_argument(
        "--no-backup-check", action="store_true",
        help="proceed even though the existing log has no matching backup; "
             "use only when you have deliberately accepted that risk")
    args = parser.parse_args()

    if not args.session.exists():
        raise SystemExit(f"{args.session} not found.")

    session = json.loads(args.session.read_text(encoding="utf-8"))
    incoming = session.get("events", [])
    if not incoming:
        raise SystemExit("Session contains no events; nothing to ingest.")
    if session.get("contract_version") != ue.CONTRACT_VERSION:
        raise SystemExit(
            f"Session declares contract {session.get('contract_version')!r} but "
            f"this tree is {ue.CONTRACT_VERSION!r}. Occurrence identity hashes "
            "the category set, so a cross-version ingest would bind judgments "
            "to ids that no longer mean the same thing. Re-export instead.")

    existing = read_jsonl(EVENTS_PATH)
    log = ue.AnnotationEventLog(existing)
    log.verify_chain()
    print(f"Existing log: {len(existing)} event(s), head "
          f"{(log.head_sha256() or '<empty>')[:16]}")

    if not backup_is_current(existing) and not args.no_backup_check:
        raise SystemExit(
            "The existing event log's current head does not appear in "
            f"{LEDGER_PATH}. Run scripts/phase4_workbench_backup.py before "
            "appending — an append-only log that is lost cannot be rebuilt. "
            "Override with --no-backup-check only if you mean to.")

    needed = {event["target_id"] for event in incoming}
    records = load_reviewable_records(needed)
    missing = sorted(needed - set(records))
    if missing:
        raise SystemExit(
            f"{len(missing)} target(s) in this session are not present on disk, "
            f"e.g. {missing[:3]}. Refusing to ingest a judgment about a record "
            "this tree does not contain.")

    # Verify before appending anything: a partial ingest of a session would
    # leave the log in a state no one intended.
    mismatched = []
    for event in incoming:
        expected = ue.canonical_sha256(records[event["target_id"]])
        if event.get("reviewed_record_sha256") != expected:
            mismatched.append(event["target_id"])
    if mismatched:
        raise SystemExit(
            f"{len(mismatched)} event(s) reference a record whose current hash "
            f"differs from what the reviewer saw, e.g. {mismatched[:3]}. The "
            "artifacts were rebuilt after this session; the judgments are "
            "about a different record and must not be silently attached.")
    print(f"Verified {len(incoming)} event(s) against on-disk records.")

    accepted = []
    for event in incoming:
        accepted.append(log.append(
            event_id=event["event_id"],
            action=event["action"],
            target_id=event["target_id"],
            reviewed_record=records[event["target_id"]],
            reviewer_id=event["reviewer"]["reviewer_id"],
            declared_role=event["reviewer"]["declared_role"],
            hypothesis=event.get("hypothesis"),
            rationale=event.get("rationale"),
            created_utc=event.get("created_utc"),
            # prior_event_sha256 is deliberately omitted: AnnotationEventLog
            # supplies the real head, which is the re-chaining this ingest is
            # for. Passing the session's assumed head through would defeat it.
        ))
    log.verify_chain()

    if args.dry_run:
        print(f"Dry run: {len(accepted)} event(s) would be appended; "
              f"new head would be {log.head_sha256()[:16]}. Nothing written.")
        return

    with open(EVENTS_PATH, "a", encoding="utf-8") as handle:
        for event in accepted:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"Appended {len(accepted)} event(s) -> {EVENTS_PATH}")
    print(f"  new chain head: {log.head_sha256()}")
    print("  every event is QUARANTINED_EXPERT_JUDGMENT and requires a "
          "separate adjudication gate.")
    print("\nRun scripts/phase4_workbench_backup.py now — this session's "
          "judgments cannot be reconstructed from the corpus.")


if __name__ == "__main__":
    main()
