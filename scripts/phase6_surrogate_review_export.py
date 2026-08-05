#!/usr/bin/env python3
"""Export a balanced, method-blinded Step 3 error-analysis packet.

This is the executable companion to
`reports/phase6_surrogate_specialist_protocol.md`. It reproduces the saved
cross-fitted HITTITE_ONLY predictions, verifies every correctness bit against
the authoritative per-query artifact, samples gained/lost cases, and writes a
reviewer-visible packet plus a separate reveal map.

Protected test data are never selected. Reviewer-visible text is attested-only
and line-grouped under the validated HITTITE_ONLY scope.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

import evidence_policy as ep  # noqa: E402
import eval_harness as eh  # noqa: E402
import phase5_taskb_transfer as tb  # noqa: E402

SEED = 20260804
SCOPE = "HITTITE_ONLY"
POLICY = "transcription_assisted"
PROTOCOL = Path("reports/phase6_surrogate_specialist_protocol.md")
TASKB_RESULT = Path("Phase4/phase4_out/p5_taskb_transfer.json")
TASKB_PER_QUERY = Path("Phase4/phase4_out/p5_taskb_transfer_per_query.jsonl")
OUT_DIR = Path("Phase4/phase4_out")
BLIND_OUT = OUT_DIR / "phase6_surrogate_review_blind.json"
REVEAL_OUT = OUT_DIR / "phase6_surrogate_review_reveal.json"
MANIFEST_OUT = OUT_DIR / "phase6_surrogate_review_manifest.json"

REQUESTED = {
    ("duplicates", "gained"): 6,
    ("duplicates", "lost"): 6,
    ("joins", "gained"): 5,
    ("joins", "lost"): 3,
}

# Corpus data-quality exceptions already excluded and recorded by the
# authoritative Step 3 evaluator. ``build_positives`` reports them even when
# they are outside the dev population because it scans the full join-pair file
# before applying the requested fragment universe.
EXPECTED_DEGENERATE_SELF_JOINS = {"KBo 22.130a+::1", "KUB 28.89+::1"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def visible_fragment(row: dict, alias: str) -> dict:
    """Return only reviewer-authorized, case-local evidence."""
    key = SCOPE
    line_ids = row[f"{key}::lines"]
    segments = row[key]
    if len(line_ids) != len(segments):
        raise RuntimeError(f"line/segment mismatch for {row['fragment_id']}")
    return {
        "alias": alias,
        "active_scope": SCOPE,
        "line_count": len(segments),
        "attested_token_count": sum(len(segment) for segment in segments),
        "lines": [
            {"line_index": int(line_idx), "attested_signs": list(segment)}
            for line_idx, segment in zip(line_ids, segments)
        ],
    }


def select_cases(pools: dict[tuple[str, str], list[dict]], cth_of: dict[str, int],
                 requested: dict[tuple[str, str], int] = REQUESTED,
                 seed: int = SEED) -> tuple[list[dict], dict]:
    """Select deterministically, preferring unused queries and CTH clusters."""
    rng = random.Random(seed)
    selected: list[dict] = []
    used_queries: set[str] = set()
    used_cths: set[int] = set()
    accounting = {}

    for key, target in requested.items():
        pool = list(pools.get(key, []))
        rng.shuffle(pool)
        chosen = []
        for prefer_new_cth in (True, False):
            for record in pool:
                qid = record["query_id"]
                cth = cth_of[qid]
                if qid in used_queries or record in chosen:
                    continue
                if prefer_new_cth and cth in used_cths:
                    continue
                chosen.append(record)
                used_queries.add(qid)
                used_cths.add(cth)
                if len(chosen) == target:
                    break
            if len(chosen) == target:
                break
        selected.extend(chosen)
        accounting[f"{key[0]}::{key[1]}"] = {
            "requested": target,
            "available": len(pool),
            "selected": len(chosen),
            "shortfall": target - len(chosen),
        }
    return selected, accounting


def assert_blind_case(case: dict) -> None:
    """Fail if method, truth, score, rank, or corpus IDs leak into the packet."""
    forbidden_keys = {
        "query_id", "fragment_id", "parent_doc", "cth", "site", "method",
        "score", "rank", "correct", "gold", "positive", "outcome", "fold",
    }

    def walk(value):
        if isinstance(value, dict):
            leaked = forbidden_keys & set(value)
            if leaked:
                raise RuntimeError(f"blind packet leaked keys: {sorted(leaked)}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(case)


def assert_expected_degenerate_self_joins(degenerate: list[str]) -> None:
    observed = set(degenerate)
    if observed != EXPECTED_DEGENERATE_SELF_JOINS:
        raise RuntimeError(
            "self-join exclusions differ from the authoritative Step 3 set: "
            f"expected {sorted(EXPECTED_DEGENERATE_SELF_JOINS)}, "
            f"observed {sorted(observed)}"
        )


def reproduce_predictions(rows: list[dict], result: dict, persisted: list[dict]):
    """Return held-out records after exact agreement with saved correctness."""
    base_ok = [r for r in rows if tb.n_content(r, tb.BASE_SCOPE) >= tb.MIN_CONTENT_TOKENS]
    labeled = [r for r in base_ok if r["main_split"] in ("train", "dev")]
    dev_rows = [r for r in labeled if r["main_split"] == "dev"]
    s_index = tb.scorable(labeled, SCOPE)
    s_queries = tb.scorable(dev_rows, SCOPE)

    frags, _splits, _doc = eh.load_fragment_universe()
    positives, join_meta, degenerate = tb.build_positives(s_queries, frags)
    assert_expected_degenerate_self_joins(degenerate)
    family_map = eh.build_family_map(frags)
    fold_of, _loads = tb._comb.assign_folds(s_queries)  # noqa: SLF001

    empty_groups = defaultdict(list)
    bm25 = tb.scope_matrix(s_index, s_queries, SCOPE, "bm25", empty_groups)
    zb = tb._comb.znorm_rows(bm25)  # noqa: SLF001
    zu = tb._comb.znorm_rows(tb.scope_matrix(  # noqa: SLF001
        s_index, s_queries, SCOPE, "unigram_tfidf", empty_groups))
    zg = tb._comb.znorm_rows(tb.scope_matrix(  # noqa: SLF001
        s_index, s_queries, SCOPE, "bigram_only_tfidf", empty_groups))

    per_fold = result["scopes"][SCOPE]["per_fold_weight_selection"]
    held = {cell: {"u": {}, "ub": {}} for cell in ("joins", "duplicates")}
    for spec in per_fold:
        fold = int(spec["fold"])
        idx = [i for i, row in enumerate(s_queries) if fold_of[row["cth"]] == fold]
        wu = float(spec["alpha_unigram_only"])
        wp = tuple(float(x) for x in spec["alpha_pair"])
        scores_u = zb + wu * zu
        scores_ub = zb + wp[0] * zu + wp[1] * zg
        for cell in held:
            pq_u, _ = tb.retrieve(s_queries, s_index, scores_u, positives[cell],
                                  family_map, idx)
            pq_ub, _ = tb.retrieve(s_queries, s_index, scores_ub, positives[cell],
                                   family_map, idx)
            held[cell]["u"].update({r["query_id"]: r for r in pq_u})
            held[cell]["ub"].update({r["query_id"]: r for r in pq_ub})

    saved = {r["query_id"]: r for r in persisted}
    checked = 0
    for cell, arms in held.items():
        for arm, suffix in (("u", "unigram"), ("ub", "unigram_bigram")):
            key = f"{SCOPE}::{cell}::{suffix}"
            for qid, record in arms[arm].items():
                if qid not in saved or key not in saved[qid]:
                    raise RuntimeError(f"persisted correctness missing {key} for {qid}")
                if int(record["recall@1"]) != int(saved[qid][key]):
                    raise RuntimeError(f"reproduction mismatch {key} for {qid}")
                checked += 1
    return {
        "held": held,
        "positives": positives,
        "join_meta": join_meta,
        "index": s_index,
        "queries": s_queries,
        "fold_of": fold_of,
        "n_correctness_bits_checked": checked,
    }


def main() -> None:
    if not PROTOCOL.exists():
        raise SystemExit(f"missing pre-registered protocol: {PROTOCOL}")

    result = json.loads(TASKB_RESULT.read_text(encoding="utf-8"))
    persisted = load_jsonl(TASKB_PER_QUERY)
    universe, _lang_index, _refusals = tb.load_universe(tb.FIXED_SCOPES)
    reproduced = reproduce_predictions(universe, result, persisted)
    by_id = {r["fragment_id"]: r for r in universe}
    cth_of = {r["fragment_id"]: int(r["cth"]) for r in reproduced["queries"]}

    pools = defaultdict(list)
    for cell, arms in reproduced["held"].items():
        common = sorted(set(arms["u"]) & set(arms["ub"]))
        for qid in common:
            a = int(arms["u"][qid]["recall@1"])
            b = int(arms["ub"][qid]["recall@1"])
            if b > a:
                pools[(cell, "gained")].append({"query_id": qid, "cell": cell,
                                                 "outcome": "gained"})
            elif b < a:
                pools[(cell, "lost")].append({"query_id": qid, "cell": cell,
                                               "outcome": "lost"})

    selected, accounting = select_cases(pools, cth_of)
    if any(v["shortfall"] for v in accounting.values()):
        raise RuntimeError(f"sampling shortfall: {accounting}")

    rng = random.Random(SEED + 1)
    blind_cases, reveal_cases = [], []
    for number, selection in enumerate(selected, start=1):
        case_id = f"SR{number:03d}"
        qid, cell = selection["query_id"], selection["cell"]
        u = reproduced["held"][cell]["u"][qid]
        ub = reproduced["held"][cell]["ub"][qid]
        if u["top1"] == ub["top1"]:
            raise RuntimeError(f"gained/lost case has identical candidates: {qid}")
        assignment = [("unigram", u["top1"]), ("expanded_bigram", ub["top1"])]
        rng.shuffle(assignment)

        blind = {
            "case_id": case_id,
            "task": ("physical_join_retrieval" if cell == "joins"
                     else "duplicate_parallel_retrieval"),
            "query": visible_fragment(by_id[qid], "QUERY"),
            "candidate_A": visible_fragment(by_id[assignment[0][1]], "A"),
            "candidate_B": visible_fragment(by_id[assignment[1][1]], "B"),
            "allowed_actions": ["A", "B", "BOTH", "NEITHER", "UNRESOLVED"],
            "physical_evidence_available": False,
        }
        assert_blind_case(blind)
        blind_cases.append(blind)

        positives = reproduced["positives"][cell].get(qid, set())
        reveal_cases.append({
            "case_id": case_id,
            "query_id": qid,
            "task_cell": cell,
            "sampling_outcome": selection["outcome"],
            "cth": cth_of[qid],
            "fold": int(reproduced["fold_of"][cth_of[qid]]),
            "candidate_A": {
                "method": assignment[0][0], "fragment_id": assignment[0][1],
                "editorial_relation_positive": assignment[0][1] in positives,
            },
            "candidate_B": {
                "method": assignment[1][0], "fragment_id": assignment[1][1],
                "editorial_relation_positive": assignment[1][1] in positives,
            },
            "all_editorial_relation_positives": sorted(positives),
        })

    blind_payload = {
        "artifact": "phase6_surrogate_review_blind",
        "reviewer_status": "AI_SURROGATE_NOT_HITTITE_SPECIALIST",
        "evidence_policy": POLICY,
        "method_identity_hidden": True,
        "truth_and_outcome_hidden": True,
        "sampling_is_prevalence_weighted": False,
        "case_count": len(blind_cases),
        "rubric_source": str(PROTOCOL),
        "cases": blind_cases,
    }
    reveal_payload = {
        "artifact": "phase6_surrogate_review_reveal",
        "do_not_open_before_annotations_are_locked": True,
        "seed": SEED,
        "sampling_accounting": accounting,
        "correctness_bits_reproduced": reproduced["n_correctness_bits_checked"],
        "cases": reveal_cases,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BLIND_OUT.write_text(json.dumps(blind_payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    REVEAL_OUT.write_text(json.dumps(reveal_payload, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    registry = ep.load_registry()
    policy = ep.load_policy(POLICY)
    manifest = ep.build_manifest(
        task="phase6_blinded_surrogate_retrieval_review",
        evidence_policy=POLICY,
        features_requested=["token", "line_index_in_doc"],
        registry=registry,
        policy=policy,
        dataset_manifest_path="Phase4/phase4_out/multilingual_tokens_v2_manifest.json",
        split_manifest_path="Phase1_pipeline/p2_out/splits.parquet",
        config_path=PROTOCOL,
        seed=SEED,
        declared_statistics_universe=(
            "balanced diagnostic sample from persisted cross-fitted HITTITE_ONLY "
            "dev gained/lost Task B records; not prevalence weighted"),
    )
    manifest.update({
        "reviewer_status": "AI_SURROGATE_NOT_HITTITE_SPECIALIST",
        "protected_test_loaded": False,
        "blind_packet_sha256": sha256_file(BLIND_OUT),
        "sealed_reveal_sha256": sha256_file(REVEAL_OUT),
        "authoritative_taskb_result_sha256": sha256_file(TASKB_RESULT),
        "authoritative_per_query_sha256": sha256_file(TASKB_PER_QUERY),
        "sampling_metadata_not_visible_to_reviewer": [
            "method identity", "correctness", "editorial relation labels",
            "CTH", "fold", "fragment identifiers"],
        "sampling_accounting": accounting,
        "correctness_bits_reproduced": reproduced["n_correctness_bits_checked"],
    })
    ep.write_manifest(manifest, MANIFEST_OUT)
    print(f"wrote {len(blind_cases)} blinded cases")
    print(f"correctness bits reproduced: {reproduced['n_correctness_bits_checked']}")
    print(f"sampling: {json.dumps(accounting, sort_keys=True)}")
    print(f"blind: {BLIND_OUT}")
    print(f"reveal: {REVEAL_OUT} (do not inspect before annotations lock)")


if __name__ == "__main__":
    main()
