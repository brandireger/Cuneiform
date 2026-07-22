#!/usr/bin/env python3
"""
dm0_audit_sample.py -- samples lines for the DM0_RULING.md Ruling 2
spot-audit and dumps raw XML + decomposed tokens + cu_alignment output
side-by-side for hand verification.

Usage:
    python demo/dm0_audit_sample.py
"""
import json
import random
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from Archive.demo.cu_alignment import align_line

SEED = 20260722


def main():
    dec = None
    import pandas as pd
    dec = pd.read_parquet(Path("p4_out") / "decomposed_corpus.parquet")
    real = dec[dec["token"] != "<PAR>"]
    per_line_tokens = real.groupby(["doc_id", "line_index_in_doc"])["token"].apply(list).reset_index()
    per_line_states = real.groupby(["doc_id", "line_index_in_doc"])["damage_state"].apply(list).reset_index()

    oracle = pd.read_parquet(Path("p2_out") / "damage_oracle.parquet")
    oracle["cu_str"] = oracle["cu"].fillna("")
    merged = oracle.merge(per_line_tokens, on=["doc_id", "line_index_in_doc"], how="left")
    merged = merged.merge(per_line_states, on=["doc_id", "line_index_in_doc"], how="left",
                          suffixes=("", "_state"))
    merged["token"] = merged["token"].apply(lambda x: x if isinstance(x, list) else [])
    merged["damage_state"] = merged["damage_state"].apply(lambda x: x if isinstance(x, list) else [])

    pop = merged[merged["cu_str"].str.len() > 0].copy()

    def classify(row):
        cat, cells = align_line(row["cu_str"], row["token"], row["damage_state"])
        return cat

    pop["category"] = pop.apply(classify, axis=1)
    edge_trim_pop = pop[pop["category"] == "edge_trim"]
    skeleton_pop = pop[pop["category"] == "skeleton_only"]

    rng = random.Random(SEED)
    edge_sample = edge_trim_pop.sample(min(30, len(edge_trim_pop)), random_state=SEED)
    skeleton_sample = skeleton_pop.sample(min(15, len(skeleton_pop)), random_state=SEED)

    print(f"edge_trim population: {len(edge_trim_pop)}, sampled {len(edge_sample)}")
    print(f"skeleton_only population: {len(skeleton_pop)}, sampled {len(skeleton_sample)}")

    zp = zipfile.ZipFile("TLHdig_0.2.0-beta.zip")
    names = zp.namelist()

    def find_xml_for_doc(doc_id):
        guess = doc_id + ".xml"
        for n in names:
            if n.endswith("/" + guess) or n.endswith(guess):
                return n
        return None

    def raw_line_snippet(doc_id, line_index):
        name = find_xml_for_doc(doc_id)
        if name is None:
            return "(file not found)"
        raw = zp.read(name).decode("utf-8")
        segments = re.split(r"(?=<lb )", raw)
        lb_segments = segments[1:]
        if line_index >= len(lb_segments):
            return "(line index out of range)"
        return lb_segments[line_index][:500]

    out_records = []
    for tier, sample in (("edge_trim", edge_sample), ("skeleton_only", skeleton_sample)):
        for _, row in sample.iterrows():
            cat, cells = align_line(row["cu_str"], row["token"], row["damage_state"])
            token_damage_pairs = list(zip(row["token"], row["damage_state"]))
            raw_xml = raw_line_snippet(row["doc_id"], row["line_index_in_doc"])
            out_records.append({
                "tier": tier, "doc_id": row["doc_id"],
                "line_index_in_doc": int(row["line_index_in_doc"]),
                "line_label": row["line_label"], "cu": row["cu_str"],
                "tokens_with_states": token_damage_pairs,
                "aligned_cells": cells,
                "raw_xml": raw_xml,
            })

    with open(Path("demo") / "dm_out" / "audit_sample.json", "w", encoding="utf-8") as f:
        json.dump(out_records, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(out_records)} records -> demo/dm_out/audit_sample.json")


if __name__ == "__main__":
    main()
