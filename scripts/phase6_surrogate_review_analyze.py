#!/usr/bin/env python3
"""Reveal and summarize the locked Phase 6 surrogate-review annotations.

This script is descriptive only. The review sample is deliberately balanced,
so its counts must not be presented as prevalence or population estimates.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ANNOTATIONS = Path("Phase4/phase4_out/phase6_surrogate_review_annotations.json")
REVEAL = Path("Phase4/phase4_out/phase6_surrogate_review_reveal.json")
OUTPUT = Path("Phase4/phase4_out/phase6_surrogate_review_analysis.json")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preference_category(preference: str, revealed_case: dict) -> str:
    if preference in {"NEITHER", "UNRESOLVED"}:
        return preference.lower()
    if preference == "BOTH":
        return "both"
    return revealed_case[f"candidate_{preference}"]["method"].replace(
        "expanded_bigram", "expanded"
    )


def selected_aliases(preference: str) -> list[str]:
    if preference == "BOTH":
        return ["A", "B"]
    if preference in {"A", "B"}:
        return [preference]
    return []


def benchmark_positive(candidate: dict) -> bool:
    """Read the corrected field or the locked packet's legacy misnomer."""
    if "benchmark_positive" in candidate:
        return bool(candidate["benchmark_positive"])
    return bool(candidate["editorial_relation_positive"])


def analyze(annotations: dict, reveal: dict) -> dict:
    locked = annotations.get("status") == "LOCKED_BEFORE_REVEAL_CONTENT_INSPECTION"
    if not locked or annotations.get("reveal_content_inspected_before_lock") is not False:
        raise RuntimeError("annotations do not carry the required pre-reveal lock")

    ann_by_id = {x["case_id"]: x for x in annotations["annotations"]}
    rev_by_id = {x["case_id"]: x for x in reveal["cases"]}
    if set(ann_by_id) != set(rev_by_id):
        raise RuntimeError("annotation and reveal case IDs differ")

    by_stratum: dict[str, Counter] = defaultdict(Counter)
    cases = []
    single_choice_n = 0
    single_choice_benchmark_agreement = 0
    selected_any_n = 0
    selected_contains_benchmark_positive = 0
    physical_counts = Counter()

    for case_id in sorted(ann_by_id):
        ann = ann_by_id[case_id]
        rev = rev_by_id[case_id]
        preference = ann["preferred_candidate"]
        category = preference_category(preference, rev)
        stratum = f"{rev['task_cell']}::{rev['sampling_outcome']}"
        by_stratum[stratum][category] += 1

        aliases = selected_aliases(preference)
        selected_positive = any(
            benchmark_positive(rev[f"candidate_{alias}"])
            for alias in aliases
        )
        if aliases:
            selected_any_n += 1
            selected_contains_benchmark_positive += int(selected_positive)
        if len(aliases) == 1:
            single_choice_n += 1
            single_choice_benchmark_agreement += int(selected_positive)

        method_to_alias = {
            rev["candidate_A"]["method"]: "A",
            rev["candidate_B"]["method"]: "B",
        }
        expanded_alias = method_to_alias["expanded_bigram"]
        unigram_alias = method_to_alias["unigram"]
        physical = ann["physical_join_judgment"]
        if physical is not None:
            physical_counts[physical] += 1

        cases.append({
            "case_id": case_id,
            "task_cell": rev["task_cell"],
            "sampling_outcome": rev["sampling_outcome"],
            "preferred_candidate": preference,
            "preference_category": category,
            "selected_contains_benchmark_positive": (
                selected_positive if aliases else None
            ),
            "expanded_alias": expanded_alias,
            "expanded_benchmark_positive": benchmark_positive(
                rev[f"candidate_{expanded_alias}"]
            ),
            "expanded_textual_support": ann["textual_relation_support"][
                expanded_alias
            ],
            "unigram_alias": unigram_alias,
            "unigram_benchmark_positive": benchmark_positive(
                rev[f"candidate_{unigram_alias}"]
            ),
            "unigram_textual_support": ann["textual_relation_support"][
                unigram_alias
            ],
            "formulaicity_ambiguity": ann["formulaicity_ambiguity"],
            "physical_join_judgment": physical,
            "specialist_priority": ann["specialist_priority"],
        })

    return {
        "artifact": "phase6_surrogate_review_analysis",
        "status": "DESCRIPTIVE_BALANCED_SAMPLE_NOT_A_POPULATION_ESTIMATE",
        "reviewer_status": annotations["reviewer_role"],
        "annotation_lock_verified": True,
        "case_count": len(cases),
        "preference_by_stratum": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(by_stratum.items())
        },
        "benchmark_label_agreement": {
            "single_candidate_choices": single_choice_n,
            "single_candidate_choice_is_benchmark_positive": (
                single_choice_benchmark_agreement
            ),
            "all_nonabstaining_choices": selected_any_n,
            "selected_set_contains_benchmark_positive": (
                selected_contains_benchmark_positive
            ),
            "note": (
                "Join positives are editor-encoded physical partners. The "
                "so-called duplicate positives are same-CTH non-join pairs, "
                "not annotated duplicate or parallel relations."
            ),
        },
        "label_semantics": {
            "joins": "EDITORIAL_PHYSICAL_JOIN_PARTNER",
            "duplicates": "SAME_CTH_NON_JOIN_BENCHMARK_PROXY",
        },
        "physical_join_judgments": dict(sorted(physical_counts.items())),
        "cases": cases,
    }


def main() -> None:
    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    reveal = json.loads(REVEAL.read_text(encoding="utf-8"))
    result = analyze(annotations, reveal)
    result["inputs"] = {
        "annotations": str(ANNOTATIONS),
        "annotations_sha256": sha256_file(ANNOTATIONS),
        "reveal": str(REVEAL),
        "reveal_sha256": sha256_file(REVEAL),
    }
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(json.dumps(result["preference_by_stratum"], sort_keys=True))
    print(json.dumps(result["benchmark_label_agreement"], sort_keys=True))
    print(json.dumps(result["physical_join_judgments"], sort_keys=True))


if __name__ == "__main__":
    main()
