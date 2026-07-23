#!/usr/bin/env python3
"""Phase 2 P2-E: coverage-first witness recoverability census.

Primary question:
    When an attested span is intentionally hidden, how often does an
    independent same-composition witness bound the missing context?

This is not a restoration-accuracy experiment.  Same-CTH membership only
selects possible witnesses.  A witness contributes evidence only when its
attested-only sequence contains the query's left and right anchors in order,
with a variable-length middle.  Exact agreement, variant-only evidence,
ambiguity, and abstention are reported separately.

The secondary join diagnostic asks only whether a third witness contains
distinct attested n-grams shared with both members of a known join.  It does
not score physical compatibility or assert a join placement.

Usage:
    python scripts/p2e_witness_recoverability.py
"""

import hashlib
import json
import math
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import contracts
import eval_harness as eh
import evidence_policy as ep
import hittite_tokenizer as ht
from phase2_io import iter_allowed_join_metadata, split_lookup_fail_closed


SEED = 20260723
TARGET_SPLIT = "dev"
POLICY_NAME = "catalog_assisted"
ANCHOR_LENGTHS = (1, 2, 3)
MASK_LENGTHS = (1, 2, 3, 5)
MAX_WITNESS_MIDDLE = 12
JOIN_NGRAM_LENGTHS = (1, 2, 3, 5)
REAL_TRACER_LIMIT = 12

P2_OUT = Path("p2_out")
P4_OUT = Path("p4_out")
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2e_witness_recoverability.json"
MANIFEST_PATH = OUT_DIR / "p2e_witness_recoverability_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e_witness_recoverability.md"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(numerator, denominator):
    return round(100.0 * numerator / denominator, 2) if denominator else None


def load_dev_inputs():
    """Load content only after a fail-closed dev parent allowlist exists."""
    contracts.assert_dev_only_selection(TARGET_SPLIT, label="P2-E ingress")

    splits = pd.read_parquet(
        P2_OUT / "splits.parquet",
        columns=["doc_id", "cth", "is_bin", "main_split"],
    )
    split_lookup, ambiguous_ids = split_lookup_fail_closed(splits)
    dev_parent_ids = sorted(
        doc_id for doc_id, split in split_lookup.items()
        if split == TARGET_SPLIT
    )
    if not dev_parent_ids:
        raise AssertionError("P2-E: frozen split map produced no dev parents")

    edges = pd.read_parquet(
        P2_OUT / "edges.parquet",
        columns=["fragment_id", "parent_doc", "cth", "lines"],
        filters=[("parent_doc", "in", dev_parent_ids)],
    )
    returned_parents = set(edges["parent_doc"])
    unexpected = returned_parents.difference(dev_parent_ids)
    if unexpected:
        raise AssertionError(
            f"P2-E: edge reader returned non-dev parents: {sorted(unexpected)[:5]}")
    contracts.assert_unique_docids(edges)
    fragment_splits = {
        row.fragment_id: split_lookup[row.parent_doc]
        for row in edges.itertuples(index=False)
    }
    contracts.assert_no_test(
        edges["fragment_id"], fragment_splits, label="P2-E dev edges")

    decomposed = pd.read_parquet(
        P4_OUT / "decomposed_corpus.parquet",
        columns=[
            "doc_id", "line_index_in_doc", "word_pos", "token",
            "damage_state",
        ],
        filters=[("doc_id", "in", dev_parent_ids)],
    )
    content_parents = set(decomposed["doc_id"])
    unexpected_content = content_parents.difference(dev_parent_ids)
    if unexpected_content:
        raise AssertionError(
            "P2-E: decomposed reader returned non-dev parents: "
            f"{sorted(unexpected_content)[:5]}")
    contracts.assert_no_test(
        content_parents, split_lookup, label="P2-E decomposed content")

    dev_split_rows = splits[splits["doc_id"].isin(dev_parent_ids)]
    if bool(dev_split_rows["is_bin"].any()):
        raise AssertionError("P2-E: discovery/bin documents entered dev")

    return splits, split_lookup, ambiguous_ids, edges, decomposed


def build_line_index(decomposed):
    """Ordered raw (token, state) lines, preserving canonical input shape."""
    ordered = decomposed.sort_values(
        ["doc_id", "line_index_in_doc", "word_pos"])
    line_index = defaultdict(list)
    for row in ordered.itertuples(index=False):
        line_index[(row.doc_id, int(row.line_index_in_doc))].append(
            (row.token, row.damage_state))
    return line_index


def informative_attested_line(line_idx, token_states):
    """Canonical attested-only rendering, then remove non-readings.

    ``x`` is an illegible placeholder rather than a proposed sign value.
    Structural specials delimit text but are not sign evidence.  The
    cleanroom convention keeps all non-restored readings, including
    partially preserved ``laes`` readings.
    """
    canonical = ht.encode_fragment_window(
        [(line_idx, token_states)], include_restored=False)
    expected = [
        token for token, state in token_states if state != "restored"]
    if canonical != expected:
        raise AssertionError(
            "P2-E: canonical line encoding disagrees with explicit "
            "restoration exclusion")
    return [
        token for token in canonical
        if token not in ht.SPECIALS and token != "x"
    ]


def render_fragments(edges, line_index):
    """Return canonical attested-only per-line sequences for each fragment."""
    rendered = {}
    canonical_flat = []
    for row in edges.sort_values("fragment_id").itertuples(index=False):
        line_records = json.loads(row.lines)
        raw_lines = []
        content_lines = []
        for record in sorted(
                line_records, key=lambda value: value["line_index_in_doc"]):
            line_idx = int(record["line_index_in_doc"])
            token_states = line_index.get((row.parent_doc, line_idx), [])
            raw_lines.append((line_idx, token_states))
            content_lines.append(
                informative_attested_line(line_idx, token_states))
        canonical_flat.extend(
            ht.encode_fragment_window(raw_lines, include_restored=False))
        rendered[row.fragment_id] = content_lines
    return rendered, canonical_flat


def requested_anchor_keys(lines, anchor_length, mask_lengths):
    """All (left, right) anchor pairs around eligible masked spans."""
    requested = set()
    for line in lines:
        for mask_length in mask_lengths:
            stop = len(line) - anchor_length - mask_length + 1
            for start in range(anchor_length, max(anchor_length, stop)):
                left = tuple(line[start - anchor_length:start])
                right = tuple(
                    line[start + mask_length:
                         start + mask_length + anchor_length])
                requested.add((left, right))
    return requested


def iter_masked_spans(lines, anchor_length, mask_length):
    """Yield (anchor key, attested gold middle) without crossing lines."""
    for line in lines:
        stop = len(line) - anchor_length - mask_length + 1
        for start in range(anchor_length, max(anchor_length, stop)):
            left = tuple(line[start - anchor_length:start])
            gold = tuple(line[start:start + mask_length])
            right = tuple(
                line[start + mask_length:
                     start + mask_length + anchor_length])
            yield (left, right), gold


def build_anchor_index(
        fragment_ids,
        line_sequences,
        fragment_families,
        anchor_length,
        requested_by_cth,
        fragment_cth,
        max_middle=MAX_WITNESS_MIDDLE):
    """Index bounded witness middles and their independent source families.

    Only anchor pairs that occur around a possible query mask are retained;
    this changes memory use, not the evidence searched.
    """
    index = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    for fragment_id in sorted(fragment_ids):
        cth = fragment_cth[fragment_id]
        requested = requested_by_cth.get(cth, set())
        if not requested:
            continue
        family = fragment_families[fragment_id]
        for line in line_sequences[fragment_id]:
            for left_start in range(
                    0, len(line) - (2 * anchor_length) + 1):
                middle_start = left_start + anchor_length
                left = tuple(line[left_start:middle_start])
                for middle_length in range(max_middle + 1):
                    right_start = middle_start + middle_length
                    right_end = right_start + anchor_length
                    if right_end > len(line):
                        break
                    right = tuple(line[right_start:right_end])
                    key = (left, right)
                    if key not in requested:
                        continue
                    proposal = tuple(line[middle_start:right_start])
                    index[cth][key][proposal].add(family)
    return index


def independent_proposals(index, cth, key, excluded_family):
    """Return proposed middles supported outside the query's family."""
    proposals = set()
    for proposal, families in index.get(cth, {}).get(key, {}).items():
        if any(family != excluded_family for family in families):
            proposals.add(proposal)
    return proposals


def scramble_lines(lines, seed):
    """Deterministically permute token order while preserving line lengths."""
    rng = random.Random(seed)
    scrambled = []
    for line in lines:
        changed = list(line)
        rng.shuffle(changed)
        if len(changed) > 1 and changed == line:
            changed = changed[1:] + changed[:1]
        scrambled.append(changed)
    return scrambled


def run_p2e_t1(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_index):
    """Content-sensitivity tracer for the new anchored-witness scorer."""
    synthetic_query = [["L1", "L2", "GOLD", "R1", "R2"]]
    synthetic_witness = {"w": [["L1", "L2", "GOLD", "R1", "R2"]]}
    synthetic_cth = {"w": 1}
    synthetic_family = {"w": "w-family"}
    synthetic_requested = {
        1: requested_anchor_keys(synthetic_query, 2, (1,))}
    synthetic_index = build_anchor_index(
        ["w"], synthetic_witness, synthetic_family, 2,
        synthetic_requested, synthetic_cth, max_middle=3)
    key, gold = next(iter_masked_spans(synthetic_query, 2, 1))
    original = independent_proposals(
        synthetic_index, 1, key, excluded_family="query-family")
    synthetic_witness["w"] = scramble_lines(
        synthetic_witness["w"], SEED)
    corrupted_index = build_anchor_index(
        ["w"], synthetic_witness, synthetic_family, 2,
        synthetic_requested, synthetic_cth, max_middle=3)
    corrupted = independent_proposals(
        corrupted_index, 1, key, excluded_family="query-family")
    synthetic_pass = gold in original and original != corrupted

    canaries = []
    for fragment_id in sorted(line_sequences):
        cth = fragment_cth[fragment_id]
        query_family = fragment_families[fragment_id]
        for key, canary_gold in iter_masked_spans(
                line_sequences[fragment_id], 2, 1):
            proposals = independent_proposals(
                anchor_index, cth, key, query_family)
            if proposals:
                canaries.append(
                    (fragment_id, cth, query_family, key, proposals))
                break
        if len(canaries) >= REAL_TRACER_LIMIT:
            break

    changed = 0
    for canary_index, (_, cth, query_family, key, original_props) in enumerate(
            canaries):
        witness_ids = [
            candidate for candidate in fragments_by_cth[cth]
            if fragment_families[candidate] != query_family
        ]
        corrupted_lines = {
            candidate: scramble_lines(
                line_sequences[candidate],
                SEED + canary_index + 1)
            for candidate in witness_ids
        }
        local_cth = {candidate: cth for candidate in witness_ids}
        local_requested = {cth: {key}}
        corrupted_local = build_anchor_index(
            witness_ids, corrupted_lines, fragment_families, 2,
            local_requested, local_cth)
        corrupted_props = independent_proposals(
            corrupted_local, cth, key, excluded_family=query_family)
        if original_props != corrupted_props:
            changed += 1

    required = max(1, math.ceil(len(canaries) / 3))
    real_pass = bool(canaries) and changed >= required
    result = {
        "synthetic_canary_pass": synthetic_pass,
        "real_canaries": len(canaries),
        "real_canaries_changed_under_order_scramble": changed,
        "real_canaries_required_to_change": required,
        "real_canary_pass": real_pass,
        "blocking_failures": int(not synthetic_pass) + int(not real_pass),
    }
    if result["blocking_failures"]:
        raise AssertionError(f"P2-E T1 content-sensitivity tracer failed: {result}")
    return result


def evaluate_recoverability(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_indices):
    """Aggregate structural availability, evidence, ambiguity, and abstention."""
    results = {}
    fragments_with_maskable = set()
    fragments_with_independent = set()
    fragments_with_support = set()

    cth_families = {
        cth: {fragment_families[fragment_id] for fragment_id in fragment_ids}
        for cth, fragment_ids in fragments_by_cth.items()
    }

    for anchor_length in ANCHOR_LENGTHS:
        for mask_length in MASK_LENGTHS:
            counts = Counter()
            support_fragments = set()
            independent_fragments = set()
            maskable_fragments = set()
            index = anchor_indices[anchor_length]
            for fragment_id in sorted(line_sequences):
                spans = list(iter_masked_spans(
                    line_sequences[fragment_id],
                    anchor_length,
                    mask_length))
                if not spans:
                    continue
                counts["maskable_spans_total"] += len(spans)
                maskable_fragments.add(fragment_id)
                cth = fragment_cth[fragment_id]
                query_family = fragment_families[fragment_id]
                independent_available = bool(
                    cth_families[cth].difference({query_family}))
                if not independent_available:
                    counts["structurally_unavailable_spans"] += len(spans)
                    continue

                independent_fragments.add(fragment_id)
                counts["candidate_eligible_spans"] += len(spans)
                for key, gold in spans:
                    proposals = independent_proposals(
                        index, cth, key, query_family)
                    if not proposals:
                        counts["abstained_spans"] += 1
                        continue
                    counts["witness_supported_spans"] += 1
                    support_fragments.add(fragment_id)
                    if gold in proposals:
                        counts["exact_agreement_spans"] += 1
                    else:
                        counts["variant_only_spans"] += 1
                    if len(proposals) > 1:
                        counts["ambiguous_spans"] += 1
                    else:
                        counts["single_proposal_spans"] += 1

            fragments_with_maskable.update(maskable_fragments)
            fragments_with_independent.update(independent_fragments)
            fragments_with_support.update(support_fragments)
            counts.update({
                "fragments_with_maskable_spans": len(maskable_fragments),
                "fragments_with_independent_witness": len(
                    independent_fragments),
                "fragments_with_witness_support": len(support_fragments),
            })
            eligible = counts["candidate_eligible_spans"]
            supported = counts["witness_supported_spans"]
            counts.update({
                "structural_coverage_percent":
                    pct(eligible, counts["maskable_spans_total"]),
                "attested_support_percent_of_eligible":
                    pct(supported, eligible),
                "exact_agreement_percent_of_eligible":
                    pct(counts["exact_agreement_spans"], eligible),
                "exact_agreement_percent_of_supported":
                    pct(counts["exact_agreement_spans"], supported),
                "variant_only_percent_of_supported":
                    pct(counts["variant_only_spans"], supported),
                "ambiguous_percent_of_supported":
                    pct(counts["ambiguous_spans"], supported),
                "abstention_percent_of_eligible":
                    pct(counts["abstained_spans"], eligible),
            })
            results[f"a{anchor_length}_m{mask_length}"] = dict(counts)

    return {
        "cells": results,
        "fragments_total": len(line_sequences),
        "fragments_with_any_maskable_span": len(fragments_with_maskable),
        "fragments_with_any_independent_witness": len(
            fragments_with_independent),
        "fragments_with_any_attested_support": len(fragments_with_support),
    }


def ngram_occurrences(lines, n):
    occurrences = defaultdict(list)
    for line_number, line in enumerate(lines):
        for start in range(0, len(line) - n + 1):
            occurrences[tuple(line[start:start + n])].append(
                (line_number, start, start + n))
    return occurrences


def occurrences_overlap(one, two):
    if one[0] != two[0]:
        return False
    return one[1] < two[2] and two[1] < one[2]


def has_two_sided_witness_coverage(lines_a, lines_b, witness_lines, n):
    """A witness must contain distinct, non-overlapping A- and B-linked n-grams."""
    grams_a = set(ngram_occurrences(lines_a, n))
    grams_b = set(ngram_occurrences(lines_b, n))
    if not grams_a or not grams_b:
        return False
    witness = ngram_occurrences(witness_lines, n)
    positions_a = [
        occurrence
        for gram in grams_a
        for occurrence in witness.get(gram, ())
    ]
    positions_b = [
        occurrence
        for gram in grams_b
        for occurrence in witness.get(gram, ())
    ]
    return any(
        not occurrences_overlap(one, two)
        for one in positions_a
        for two in positions_b
    )


def evaluate_join_diagnostic(
        join_records,
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth):
    totals = Counter()
    by_tier = defaultdict(Counter)
    by_type = defaultdict(Counter)

    for record in join_records:
        parent = record["parent_doc"]
        fragment_a = f"{parent}::{record['member_a']['siglum']}"
        fragment_b = f"{parent}::{record['member_b']['siglum']}"
        tier = str(record.get("tier", "unknown"))
        join_type = str(record.get("join_type", "unknown"))
        totals["pairs"] += 1
        by_tier[tier]["pairs"] += 1
        by_type[join_type]["pairs"] += 1

        if fragment_a not in line_sequences or fragment_b not in line_sequences:
            totals["unmapped_pairs"] += 1
            by_tier[tier]["unmapped_pairs"] += 1
            by_type[join_type]["unmapped_pairs"] += 1
            continue

        cth = fragment_cth[fragment_a]
        parent_family = fragment_families[fragment_a]
        candidates = [
            fragment_id for fragment_id in fragments_by_cth.get(cth, ())
            if fragment_families[fragment_id] != parent_family
        ]
        if candidates:
            totals["pairs_with_third_witness"] += 1
            by_tier[tier]["pairs_with_third_witness"] += 1
            by_type[join_type]["pairs_with_third_witness"] += 1

        for n in JOIN_NGRAM_LENGTHS:
            if any(
                    has_two_sided_witness_coverage(
                        line_sequences[fragment_a],
                        line_sequences[fragment_b],
                        line_sequences[candidate],
                        n)
                    for candidate in candidates):
                key = f"pairs_with_attested_two_sided_coverage_n{n}"
                totals[key] += 1
                by_tier[tier][key] += 1
                by_type[join_type][key] += 1

    def finalize(counter):
        result = dict(counter)
        pairs = counter["pairs"]
        result["third_witness_percent"] = pct(
            counter["pairs_with_third_witness"], pairs)
        for n in JOIN_NGRAM_LENGTHS:
            key = f"pairs_with_attested_two_sided_coverage_n{n}"
            result[f"attested_two_sided_coverage_n{n}_percent"] = pct(
                counter[key], pairs)
        return result

    return {
        "overall": finalize(totals),
        "by_tier": {
            key: finalize(value) for key, value in sorted(by_tier.items())},
        "by_join_type": {
            key: finalize(value) for key, value in sorted(by_type.items())},
        "interpretation": (
            "Two-sided coverage means one independent witness fragment "
            "contains distinct non-overlapping attested n-grams also found "
            "in A and B. It is textual coverage, not a physical-fit score "
            "or proof of placement."),
    }


def run_base_tracers():
    """Run the repository's mandatory carried-forward tracer suite."""
    completed = subprocess.run(
        [sys.executable, "scripts/00_tracers.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = completed.stdout.strip()
    if completed.stderr.strip():
        output = f"{output}\nSTDERR:\n{completed.stderr.strip()}".strip()
    if completed.returncode != 0 or "blocking failures: 0" not in output:
        raise AssertionError(
            "P2-E: mandatory base tracer suite failed before scoring:\n"
            f"{output}")
    return {
        "command": f"{sys.executable} scripts/00_tracers.py",
        "return_code": completed.returncode,
        "blocking_failures": 0,
        "stdout": output,
    }


def write_report(summary, elapsed_seconds):
    primary = summary["recoverability"]["cells"]["a2_m1"]
    join = summary["join_diagnostic"]["overall"]
    tracer = summary["tracers"]["p2e_t1"]

    cell_rows = []
    for cell_name, values in summary["recoverability"]["cells"].items():
        cell_rows.append(
            f"| {cell_name} | {values['candidate_eligible_spans']:,} | "
            f"{values['witness_supported_spans']:,} "
            f"({values['attested_support_percent_of_eligible']}%) | "
            f"{values['exact_agreement_spans']:,} "
            f"({values['exact_agreement_percent_of_eligible']}%) | "
            f"{values['variant_only_spans']:,} | "
            f"{values['ambiguous_spans']:,} | "
            f"{values['abstention_percent_of_eligible']}% |")

    join_rows = []
    for n in JOIN_NGRAM_LENGTHS:
        join_rows.append(
            f"| {n} | "
            f"{join[f'pairs_with_attested_two_sided_coverage_n{n}']:,} | "
            f"{join[f'attested_two_sided_coverage_n{n}_percent']}% |")

    lines = [
        "# Phase 2 P2-E witness recoverability census",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Tracer block",
        "",
        f"- Carried-forward `00_tracers.py`: PASS; "
        f"{summary['tracers']['base']['blocking_failures']} blocking failures "
        "(its D18 T4 diagnostic remains visible and non-blocking).",
        f"- New anchored-witness T1: PASS; synthetic canary passed and "
        f"{tracer['real_canaries_changed_under_order_scramble']}/"
        f"{tracer['real_canaries']} real canaries changed under token-order "
        f"scrambling (required {tracer['real_canaries_required_to_change']}).",
        "",
        "## What was measured",
        "",
        "Only frozen **dev** content was read. Restored readings and unreadable "
        "`x` placeholders were excluded. For every intentionally masked "
        "attested span, an independent same-CTH witness was searched for the "
        "same left/right anchors with a variable middle of 0–12 signs. "
        "Same-CTH membership selected candidates; it did not count as evidence.",
        "",
        "## Primary result (2-sign anchors, 1 hidden sign)",
        "",
        f"- {primary['maskable_spans_total']:,} spans were maskable; "
        f"{primary['candidate_eligible_spans']:,} had a structurally available "
        f"independent witness ({primary['structural_coverage_percent']}%).",
        f"- Attested witness evidence existed for "
        f"{primary['witness_supported_spans']:,} eligible spans "
        f"({primary['attested_support_percent_of_eligible']}%). The system "
        f"abstained on {primary['abstained_spans']:,} "
        f"({primary['abstention_percent_of_eligible']}%).",
        f"- The hidden attested sign appeared among witness proposals for "
        f"{primary['exact_agreement_spans']:,} eligible spans "
        f"({primary['exact_agreement_percent_of_eligible']}%). "
        f"{primary['variant_only_spans']:,} supported spans supplied only a "
        f"different/omitted middle; {primary['ambiguous_spans']:,} supported "
        "spans had multiple witness alternatives.",
        "",
        "These are **recoverability and agreement** rates, not accuracy on "
        "genuinely lost text. A parallel constrains plausible context but does "
        "not prove that two witnesses had identical wording.",
        "",
        "## Horizon matrix",
        "",
        "| anchors/mask | eligible | supported | exact among eligible | "
        "variant-only | ambiguous | abstention |",
        "|---|---:|---:|---:|---:|---:|---:|",
        *cell_rows,
        "",
        "## Known-join diagnostic: third-witness textual coverage",
        "",
        f"{join['pairs_with_third_witness']:,}/{join['pairs']:,} dev join "
        f"pairs ({join['third_witness_percent']}%) had any independent "
        "same-CTH witness. The stricter table requires one witness fragment "
        "to contain distinct attested n-grams linked to both join members.",
        "",
        "| shared n-gram length | covered pairs | percent of all dev pairs |",
        "|---:|---:|---:|",
        *join_rows,
        "",
        "This is a textual-evidence ceiling only. It says nothing about clay "
        "fit, edge geometry, or whether A and B are adjacent.",
        "",
        "## Decision",
        "",
        "Use the horizon matrix as Phase 2's first recoverability map. Any "
        "next reconstruction model must emit alternatives and abstain outside "
        "the empirically supported cells; join ranking remains a downstream "
        "diagnostic, not the project definition.",
        "",
        "## Governance",
        "",
        f"- Evidence profile: `{summary['evidence_policy']}`.",
        "- Semantic fields: `token`, `damage_state`, `line_index_in_doc`, "
        "`cth`; no `cu`, morphology, restorations, editor identity, or model "
        "output.",
        "- Test-side content accessed: **no**.",
        f"- Seed: {SEED}; elapsed: {elapsed_seconds:.1f}s.",
        f"- Machine-readable result: `{RESULT_PATH}`; manifest: "
        f"`{MANIFEST_PATH}`.",
        "",
        "Corpus: TLHdig Beta 0.2.0, Müller, Prechel, Rieken & Schwemer "
        "(2025), DOI 10.5281/zenodo.15459134, CC BY 4.0.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(POLICY_NAME, POLICIES_PATH)
    semantic_fields = ["token", "damage_state", "line_index_in_doc", "cth"]
    ep.validate_semantic_features(semantic_fields, registry, policy)

    base_tracers = run_base_tracers()
    splits, split_lookup, ambiguous_ids, edges, decomposed = load_dev_inputs()
    line_index = build_line_index(decomposed)
    line_sequences, canonical_flat = render_fragments(edges, line_index)

    tokenizer = ht.Tokenizer.load()
    encoded = tokenizer.encode(canonical_flat, strict=True)
    contracts.assert_encoding_sane(
        encoded, tokenizer, max_unk=0.05, label="P2-E dev attested-only")

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_cth = {
        row.fragment_id: int(row.cth)
        for row in edges.itertuples(index=False)
    }
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)
    }
    fragments_by_cth = defaultdict(list)
    for fragment_id, cth in fragment_cth.items():
        fragments_by_cth[cth].append(fragment_id)

    requested_by_anchor = {}
    anchor_indices = {}
    for anchor_length in ANCHOR_LENGTHS:
        requested_by_cth = defaultdict(set)
        for fragment_id, lines in line_sequences.items():
            requested_by_cth[fragment_cth[fragment_id]].update(
                requested_anchor_keys(lines, anchor_length, MASK_LENGTHS))
        requested_by_anchor[anchor_length] = requested_by_cth
        anchor_indices[anchor_length] = build_anchor_index(
            line_sequences.keys(),
            line_sequences,
            fragment_families,
            anchor_length,
            requested_by_cth,
            fragment_cth,
        )

    p2e_t1 = run_p2e_t1(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_indices[2],
    )

    recoverability = evaluate_recoverability(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_indices,
    )

    join_audit = Counter()
    join_records = list(iter_allowed_join_metadata(
        P2_OUT / "join_pairs.jsonl",
        split_lookup,
        ambiguous_ids,
        TARGET_SPLIT,
        join_audit,
    ))
    join_diagnostic = evaluate_join_diagnostic(
        join_records,
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
    )

    summary = {
        "probe": "P2-E coverage-first witness recoverability",
        "probe_label": "PROBE — not for citation",
        "evidence_policy": policy.name,
        "target_split": TARGET_SPLIT,
        "test_side_accessed": False,
        "restorations_included": False,
        "unreadable_x_included_as_sign_evidence": False,
        "parameters": {
            "anchor_lengths": list(ANCHOR_LENGTHS),
            "mask_lengths": list(MASK_LENGTHS),
            "maximum_witness_middle_length": MAX_WITNESS_MIDDLE,
            "join_ngram_lengths": list(JOIN_NGRAM_LENGTHS),
            "seed": SEED,
        },
        "input_counts": {
            "unambiguous_dev_parent_documents": len({
                row.parent_doc for row in edges.itertuples(index=False)}),
            "dev_fragments": len(edges),
            "dev_decomposed_token_rows": len(decomposed),
            "ambiguous_doc_ids_quarantined": len(ambiguous_ids),
            "dev_join_records": len(join_records),
            "join_reader_audit": dict(join_audit),
        },
        "tracers": {
            "base": base_tracers,
            "p2e_t1": p2e_t1,
        },
        "recoverability": recoverability,
        "join_diagnostic": join_diagnostic,
        "interpretation_limits": [
            "Same-CTH membership is catalog-assisted candidate selection, "
            "not proof of parallel wording.",
            "Agreement with intentionally masked attested text measures "
            "recoverability under known context, not correctness on a real "
            "lacuna.",
            "Variant-only witness middles are alternatives or omissions, "
            "not errors by default.",
            "The join diagnostic is textual coverage, not physical-fit "
            "evidence or a join score.",
        ],
        "input_hashes": {
            "edges_parquet": sha256(P2_OUT / "edges.parquet"),
            "decomposed_corpus_parquet":
                sha256(P4_OUT / "decomposed_corpus.parquet"),
            "join_pairs_jsonl": sha256(P2_OUT / "join_pairs.jsonl"),
            "splits_parquet": sha256(P2_OUT / "splits.parquet"),
            "tokenizer_json": sha256(Path("configs") / "tokenizer.json"),
        },
    }

    manifest = ep.build_manifest(
        task="missing_information_witness_recoverability",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=P4_OUT / "decomposed_corpus.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=POLICIES_PATH,
        seed=SEED,
        declared_statistics_universe=(
            "frozen unambiguous real-composition dev fragments only; "
            "same-CTH independent witness candidates; no fitted corpus "
            "statistics; known dev joins used only for a secondary coverage "
            "diagnostic"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "control_fields_observed": ["fragment_id", "parent_doc", "main_split"],
        "relation_labels_observed_for_secondary_diagnostic": [
            "member_a.siglum", "member_b.siglum", "join_type", "tier"],
        "relation_label_evidence_class": "EDITORIAL_RELATION",
        "test_side_accessed": False,
        "restoration_included": False,
        "model_scoring_performed": False,
        "exact_attested_sequence_matching_performed": True,
        "input_hashes": summary["input_hashes"],
    })

    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ep.write_manifest(manifest, MANIFEST_PATH)
    elapsed = time.perf_counter() - started
    write_report(summary, elapsed)

    primary = recoverability["cells"]["a2_m1"]
    print(
        "P2-E complete: "
        f"{primary['witness_supported_spans']}/"
        f"{primary['candidate_eligible_spans']} eligible a2_m1 spans "
        "had attested witness support; "
        f"{primary['exact_agreement_spans']} included the masked gold.")
    print(f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}")


if __name__ == "__main__":
    main()
