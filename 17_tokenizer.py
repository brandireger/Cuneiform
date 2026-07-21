#!/usr/bin/env python3
"""
17_tokenizer.py -- P4 D12 CLI: build the sign-level tokenizer.

Usage:
    python 17_tokenizer.py

AMENDED 2026-07-22 (architect-approved): logogram decomposition, see
hittite_tokenizer.py docstring. This supersedes the first run's
"Target-vs-actual tension" finding (vocab=14,170/OOV=3.66% under the
original P3-verbatim whole-word-logogram rule) -- that finding is what
triggered the amendment, kept in git history, not repeated here as if
still open.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import eval_harness as eh
import hittite_tokenizer as ht

SEED = 20260722


def compute_oov(tok, frags, line_index, edge_info, split):
    pop = frags[frags["main_split"] == split]
    total, oov = 0, 0
    for row in pop.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        seq = ht.build_structured_sequence_attested(
            row.parent_doc, line_idxs, line_index, top_lost, bot_lost, by_line)
        for t in seq:
            if t in ht.SPECIALS:
                continue
            total += 1
            if t not in tok.vocab:
                oov += 1
    return oov, total


def main():
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()

    print("Building vocabulary (TRAIN + discovery pool, ATTESTED, sign-decomposed)...")
    tok, doc_freq, n_docs = ht.build_vocab(frags, line_index, edge_info)
    tok.save()
    print(f"Vocab built from {n_docs} fragments. Vocab size (incl. {len(ht.SPECIALS)} "
          f"specials): {len(tok.vocab)}")

    oov_dev, total_dev = compute_oov(tok, frags, line_index, edge_info, "dev")
    oov_rate = oov_dev / total_dev if total_dev else None
    print(f"Dev OOV: {oov_dev} / {total_dev} = {oov_rate:.4%}" if oov_rate is not None else "Dev OOV: n/a")

    # ---- round-trip examples: 5 seeded real fragments
    rng = random.Random(SEED)
    train_frags = frags[frags["main_split"] == "train"]["fragment_id"].tolist()
    sample_ids = rng.sample(train_frags, min(5, len(train_frags)))
    roundtrip_examples = []
    frag_lookup = frags.set_index("fragment_id")
    for fid in sample_ids:
        parent = frag_lookup.loc[fid, "parent_doc"]
        if fid not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[fid]
        seq = ht.build_structured_sequence_attested(
            parent, line_idxs, line_index, top_lost, bot_lost, by_line)
        ids = tok.encode(seq)
        decoded = tok.decode(ids)
        roundtrip_examples.append({
            "fragment_id": fid, "original_tokens": seq, "decoded_tokens": decoded,
            "exact_match": seq == decoded,
            "unk_count": sum(1 for t in decoded if t == "<UNK>"),
        })

    top_tokens = doc_freq.most_common(30)

    non_special_vocab = [t for t in tok.vocab if t not in ht.SPECIALS]
    logogram_like = [t for t in non_special_vocab
                     if any(c.isupper() for c in t) or any(c.isdigit() for c in t)]
    syllabic_like = [t for t in non_special_vocab if t not in logogram_like]

    check2_pass = (oov_rate is not None and oov_rate < 0.01)

    lines = [
        "# P4 D12 -- Tokenizer Report", "",
        f"- Vocabulary source: TRAIN-side + discovery-pool ATTESTED "
        f"text only ({n_docs:,} fragments)",
        f"- min_df: {ht.MIN_DF}",
        f"- Specials: {ht.SPECIALS}",
        f"- **Vocab size (incl. specials): {len(tok.vocab):,}**",
        f"- **Dev OOV rate: {oov_rate:.4%}** ({oov_dev:,} / {total_dev:,} tokens) "
        f"-- {'PASS' if check2_pass else 'FAIL'} (target <1%)"
        if oov_rate is not None else "- Dev OOV rate: n/a",
        "",
        "## Amendment 2026-07-22 (approved by architect): sign-level "
        "logogram decomposition", "",
        "The first tokenizer run reused P3's bm25_sign rule verbatim "
        "(whole-word logogram tokens) and landed at vocab=14,170 / dev "
        "OOV=3.66%, missing both stated targets (\"low thousands\" / "
        "<1%). Diagnosis at the time: 12,632 of 14,160 vocab entries "
        "were whole-word logogram/Sumerogram/Akkadogram forms (each "
        "inflected combination, e.g. `DUTU-ŠI` vs `DUTU-uš`, its own "
        "atomic entry) -- excellent for BM25 term weighting, "
        "combinatorially expensive for a fixed neural vocabulary. "
        "Flagged rather than silently fixed, per CLAUDE.md. Architect "
        "decision: decompose logograms into their constituent signs "
        "(what's physically on the tablet), splitting sGr/aGr/d "
        "content on `-`/`.` (`DINGIR-LIM` -> `DINGIR` + `LIM`; "
        "`DUTU-uš` -> `D` + `UTU` + `uš`), except `×`-ligature "
        "compounds (`KA×U`) which stay atomic -- one wedge-cluster, "
        "one token. This required re-deriving token boundaries from "
        "the raw XML's `<d>`/`<sGr>`/`<aGr>` tag edges directly "
        "(P2's corpus.parquet flattens a word's text before hyphen-"
        "splitting, losing those edges) -- see decompose_corpus.py, a "
        "new P4-only derived artifact; P2/P2.5's corpus.parquet stays "
        "frozen and untouched. P3's BM25 tables are unaffected (they "
        "already ran and are frozen; this tokenizer is P4-only).",
        f"- **Result: vocab {len(tok.vocab):,} entries "
        f"({len(logogram_like):,} logogram-class + {len(syllabic_like):,} "
        f"syllabic/other), dev OOV {oov_rate:.2%}** -- "
        f"{'meets' if check2_pass else 'still short of'} the <1% target.",
        "",
        "## Top 30 tokens (by document frequency in TRAIN+discovery)", "",
        "| token | doc_freq |", "|---|---|",
    ]
    for t, c in top_tokens:
        lines.append(f"| `{t}` | {c:,} |")

    lines += ["", "## Round-trip examples (5 seeded TRAIN fragments)", "",
              "Round-trip must reconstruct the original transliteration "
              "string exactly (hyphens/dots re-insertable by joining "
              "decomposed tokens) for in-vocab tokens; mismatches are "
              "attributable only to genuine OOV -> `<UNK>` substitution, "
              "shown via unk_count.", ""]
    for ex in roundtrip_examples:
        lines.append(f"### {ex['fragment_id']}")
        lines.append(f"- original ({len(ex['original_tokens'])} tokens): "
                     f"`{' '.join(ex['original_tokens'][:60])}`" +
                     (" ..." if len(ex['original_tokens']) > 60 else ""))
        lines.append(f"- decoded (exact_match={ex['exact_match']}, "
                     f"unk_count={ex['unk_count']}): "
                     f"`{' '.join(ex['decoded_tokens'][:60])}`" +
                     (" ..." if len(ex['decoded_tokens']) > 60 else ""))
        lines.append("")

    with open("tokenizer_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Done. tokenizer.json + tokenizer_report.md written.")


if __name__ == "__main__":
    main()
