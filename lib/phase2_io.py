"""Cleanroom-safe readers shared by Phase 2 probes.

The join JSONL stores ``parent_doc`` first.  This module uses that prefix to
apply the frozen split gate before decoding the rest of a row, so test-side
relation payloads are never parsed by train/dev probes.
"""

import json
import re
from collections.abc import Iterator, Mapping, MutableMapping
from pathlib import Path

import pandas as pd


PARENT_PREFIX = re.compile(rb'^\{"parent_doc":\s*("(?:\\.|[^"])*")')
EXCLUSIVE_CONTENT_MARKER = b', "exclusive_content":'


def split_lookup_fail_closed(
        splits: pd.DataFrame) -> tuple[dict[str, str], set[str]]:
    """Return unambiguous doc-to-split assignments and quarantined IDs."""
    grouped = splits.groupby("doc_id", sort=False)["main_split"].agg(
        lambda values: frozenset(values))
    lookup: dict[str, str] = {}
    ambiguous: set[str] = set()
    for doc_id, values in grouped.items():
        if len(values) != 1:
            ambiguous.add(doc_id)
        else:
            lookup[doc_id] = next(iter(values))
    return lookup, ambiguous


def iter_allowed_join_metadata(
        path: str | Path,
        split_lookup: Mapping[str, str],
        ambiguous_ids: set[str],
        allowed_split: str,
        audit_counts: MutableMapping[str, int],
) -> Iterator[dict]:
    """Yield metadata only after the parent is proven to be allowed.

    The large ``exclusive_content`` payload is removed before JSON decoding.
    Rows outside ``allowed_split`` are neither decoded nor yielded.
    """
    with open(path, "rb") as source:
        for line_number, raw_line in enumerate(source, 1):
            match = PARENT_PREFIX.match(raw_line)
            if not match:
                raise ValueError(
                    f"{path}:{line_number}: parent_doc is not the first "
                    "decodable field")
            parent_doc = json.loads(match.group(1).decode("utf-8"))
            if parent_doc in ambiguous_ids:
                audit_counts["ambiguous_parent_rows_skipped"] += 1
                continue
            if parent_doc not in split_lookup:
                raise AssertionError(
                    f"{path}:{line_number}: parent_doc {parent_doc!r} is "
                    "absent from the frozen split map")
            if split_lookup[parent_doc] != allowed_split:
                continue

            marker_at = raw_line.find(EXCLUSIVE_CONTENT_MARKER)
            metadata_raw = (
                raw_line[:marker_at] + b"}"
                if marker_at >= 0 else raw_line
            )
            record = json.loads(metadata_raw.decode("utf-8"))
            if record["parent_doc"] != parent_doc:
                raise AssertionError(
                    f"{path}:{line_number}: parent prefix disagrees with "
                    "decoded metadata")
            yield record
