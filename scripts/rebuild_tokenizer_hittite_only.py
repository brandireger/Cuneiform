#!/usr/bin/env python3
"""Rebuild configs/tokenizer.json with the ratified Hittite-only line
filter (specs/LINE_LANG_MIGRATION.md).

The original vocab (Archive/scripts/17_tokenizer.py, frozen, Phase 1)
never checked line language at all -- every non-Hittite-tagged line
(Akkadian, Sumerian, Hattic, Luwian, Palaic, Hurrian; ~10.5% of
word-rows corpus-wide) contributed to what was meant to be a Hittite
sign vocabulary. This is the first regeneration of that vocab since
Phase 1 closed, using `migrations/line_lang_v1/line_lang_canonical.parquet`
(built by scripts/line_lang_rebuild.py) to exclude non-Hittite lines'
tokens from vocabulary construction -- their <LINE> position slot is
preserved (see hittite_tokenizer._line_tokens), only their token
CONTENT is excluded, so nothing about line-position numbering changes
for any downstream consumer.

Overwrites the live `configs/tokenizer.json` (not a frozen Archive/
artifact -- last touched at Phase 1 closeout and never regenerated
since, per this session's own investigation). Writes a NEW report
(`configs/tokenizer_report_line_lang_v1.md`) rather than overwriting
the historical `tokenizer_report.md`, so the delta is inspectable
against the original numbers.

Usage:
    python scripts/rebuild_tokenizer_hittite_only.py
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
from line_lang_lookup import load_line_lang_lookup  # noqa: E402

SEED = 20260725
REPORT_PATH = Path("configs") / "tokenizer_report_line_lang_v1.md"


def compute_oov(tok, frags, line_index, edge_info, split, line_lang_lookup):
    """OOV over Hittite-only-rendered text (matching what the vocab was
    built from) plus, separately, how many raw tokens were excluded as
    non-Hittite -- reported so a shrinking OOV denominator is visible,
    not silently hidden."""
    pop = frags[frags["main_split"] == split]
    total, oov, excluded_non_hittite = 0, 0, 0
    for row in pop.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        seq = ht.build_structured_sequence_attested(
            row.parent_doc, line_idxs, line_index, top_lost, bot_lost, by_line,
            line_lang_lookup=line_lang_lookup)
        unfiltered_seq = ht.build_structured_sequence_attested(
            row.parent_doc, line_idxs, line_index, top_lost, bot_lost, by_line)
        excluded_non_hittite += len(unfiltered_seq) - len(seq)
        for t in seq:
            if t in ht.SPECIALS:
                continue
            total += 1
            if t not in tok.vocab:
                oov += 1
    return oov, total, excluded_non_hittite


def main():
    frags, splits, doc_table = eh.load_fragment_universe()
    line_index = ht.build_decomposed_line_index()
    edge_info = ht.load_edge_info()
    line_lang_lookup = load_line_lang_lookup()

    print("Building vocabulary (TRAIN + discovery pool, ATTESTED, "
          "sign-decomposed, HITTITE-ONLY LINES)...")
    tok, doc_freq, n_docs = ht.build_vocab(
        frags, line_index, edge_info, line_lang_lookup=line_lang_lookup)

    old_tok = ht.Tokenizer.load()
    old_vocab_size = len(old_tok.vocab)

    tok.save()
    print(f"Vocab built from {n_docs} fragments. Vocab size (incl. "
          f"{len(ht.SPECIALS)} specials): {len(tok.vocab)} "
          f"(was {old_vocab_size} before this rebuild)")

    oov_dev, total_dev, excluded_dev = compute_oov(
        tok, frags, line_index, edge_info, "dev", line_lang_lookup)
    oov_rate = oov_dev / total_dev if total_dev else None
    print(f"Dev OOV (Hittite-only content): {oov_dev} / {total_dev} = "
          f"{oov_rate:.4%}" if oov_rate is not None else "Dev OOV: n/a")
    print(f"Dev tokens excluded as non-Hittite: {excluded_dev:,}")

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
            parent, line_idxs, line_index, top_lost, bot_lost, by_line,
            line_lang_lookup=line_lang_lookup)
        ids = tok.encode(seq)
        decoded = tok.decode(ids)
        roundtrip_examples.append({
            "fragment_id": fid, "original_tokens": seq, "decoded_tokens": decoded,
            "exact_match": seq == decoded,
            "unk_count": sum(1 for t in decoded if t == "<UNK>"),
        })

    check2_pass = (oov_rate is not None and oov_rate < 0.01)

    lines = [
        "# Tokenizer rebuild -- Hittite-only line filter "
        "(line_lang migration v1)",
        "",
        "Supersedes the vocab (not the report) in `tokenizer_report.md` "
        "(Phase 1, `Archive/scripts/17_tokenizer.py`, untouched since Phase "
        "1 closeout). That vocab was built without any language check -- "
        "non-Hittite lines (Akkadian, Sumerian, Hattic, Luwian, Palaic, "
        "Hurrian) contributed tokens to it. This rebuild excludes their "
        "content via `migrations/line_lang_v1/line_lang_canonical.parquet` "
        "(ratified vocabulary + Step C rebuild, this phase).",
        "",
        f"- Vocabulary source: TRAIN-side + discovery-pool ATTESTED, "
        f"HITTITE-ONLY text ({n_docs:,} fragments)",
        f"- min_df: {ht.MIN_DF}",
        f"- **Vocab size (incl. specials): {len(tok.vocab):,}** "
        f"(was {old_vocab_size:,} before this rebuild, "
        f"{len(tok.vocab) - old_vocab_size:+,})",
        f"- **Dev OOV rate (Hittite-only content): "
        f"{oov_rate:.4%}** ({oov_dev:,} / {total_dev:,} tokens) -- "
        f"{'PASS' if check2_pass else 'FAIL'} (target <1%)"
        if oov_rate is not None else "- Dev OOV rate: n/a",
        f"- Dev tokens excluded as non-Hittite (not counted toward OOV "
        f"either way): **{excluded_dev:,}**",
        "",
        "## Round-trip examples (5 seeded TRAIN fragments, Hittite-only "
        "rendering)",
        "",
    ]
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

    lines += [
        "## What this changes for downstream consumers",
        "",
        "Every script that calls `hittite_tokenizer.Tokenizer.load()` now "
        "gets this vocab, not the Phase 1 one -- their token ids and OOV "
        "behavior change even though no code in those scripts changed. "
        "Anything with a frozen numeric result computed against the old "
        "vocab (P2-E1 through P2-E7, the real-gap pipeline built earlier "
        "this phase) needs re-running under the new vocab to stay "
        "consistent, tracked as a separate step in this phase's work.",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"Report: {REPORT_PATH}")
    print(f"Vocab: {ht.TOKENIZER_PATH}")


if __name__ == "__main__":
    main()
