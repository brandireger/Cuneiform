#!/usr/bin/env python3
"""P4-E: verify and back up the append-only expert annotation event log.

`specs/UNRESOLVED_EVIDENCE_WORKBENCH.md` requires annotation events to be
backed up separately before the workbench is used for real expert labor. This
is not a nicety: the log is append-only and hash-chained, so a lost event file
is unrecoverable AND un-reconstructable. Occurrences can be rebuilt from the
pinned corpus at any time; a specialist's day of judgments cannot.

The backup verifies the chain BEFORE copying. Backing up a corrupt log would
faithfully preserve the corruption and, worse, make it look archived.

Each backup is timestamped and never overwrites an earlier one, so the backup
directory is itself append-only.

Usage:
    python scripts/phase4_workbench_backup.py
    python scripts/phase4_workbench_backup.py --verify-only
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import unresolved_evidence as ue  # noqa: E402

EVENTS_PATH = Path("Phase4/phase4_out/expert_annotation_events.jsonl")
BACKUP_DIR = Path("Phase4/phase4_out/annotation_backups")
LEDGER_PATH = BACKUP_DIR / "backup_ledger.jsonl"


def read_events(path):
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verify(events):
    """Validate every event and its hash chain. Raises on the first break."""
    log = ue.AnnotationEventLog(events)
    log.verify_chain()
    return log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-only", action="store_true",
        help="check the chain without writing a backup")
    args = parser.parse_args()

    events = read_events(EVENTS_PATH)
    if not events:
        print(f"{EVENTS_PATH}: no events recorded yet; nothing to back up.")
        print("The workbench has not been used for expert labor.")
        return 0

    log = verify(events)
    head = log.head_sha256()
    print(f"Verified {len(events):,} event(s); chain intact. Head: {head}")

    if args.verify_only:
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = BACKUP_DIR / f"expert_annotation_events_{stamp}.jsonl"
    if target.exists():
        raise SystemExit(
            f"{target} already exists; refusing to overwrite a backup")
    shutil.copy2(EVENTS_PATH, target)

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with open(LEDGER_PATH, "a", encoding="utf-8") as ledger:
        ledger.write(json.dumps({
            "backup_utc": datetime.now(timezone.utc).isoformat(),
            "backup_path": str(target),
            "event_count": len(events),
            "chain_head_sha256": head,
            "backup_file_sha256": digest,
            "source_path": str(EVENTS_PATH),
        }, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"Backed up to {target}")
    print(f"  file sha256: {digest}")
    print(f"  ledger:      {LEDGER_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
