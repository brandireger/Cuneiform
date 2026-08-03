#!/usr/bin/env python3
"""P4-F Stage 0: the language-conditioned training data path.

This is the piece `reports/phase4_p4f_gate3_proposal.md` explicitly scoped
OUT of the first Stage 0 session ("the actual Stage 1 training script/
data-loader integration ... best done together with real GPU access, where
it can be smoke-tested end-to-end rather than trusted on faith").

What it does, and the one thing it must not get wrong: attach a per-token
language id to every model-input position, aligned EXACTLY with the token
ids the encoder sees. Three separate transforms can break that alignment,
and each is handled at its source rather than re-derived here:

1. **Rendering** drops restored tokens, so a token's position in the model
   input is not its `word_pos` in the corpus line. Handled by
   `hittite_tokenizer.iter_structured_attested()`, which yields each
   token's true `(line_index_in_doc, word_pos)` identity as it emits it.
2. **Span masking** deletes positions when it collapses a span to a single
   `<GAP>`. Handled by `hittite_model.apply_span_masking(aux=...)`, which
   filters the language vector with the same predicate.
3. **Boundary examples** splice a continuation from a DIFFERENT document.
   Handled by `hittite_model.build_boundary_example(aux=..., aux_key=...)`,
   which carries each slice's own languages.

Both Stage 1 arms consume this module and therefore train on byte-identical
data. `condition_on_language` is the only difference between them -- arm A
simply never forwards `lang_ids` to the model. Deriving arm A's data from a
different admission rule would confound the falsifier's comparison with a
data difference, which is the failure mode proposal Sec.9 item 3 exists to
catch.

**Data-admission scope is deliberately NOT the arm's conditioning scope.**
Line admission always uses `MULTILINGUAL_CONDITIONED`. The obvious-looking
alternative -- giving arm A the ratified `ALL_LANGUAGES_UNCONDITIONED`
ablation scope -- would silently hand arm A MORE data, because
`language_lookup_v2._classify` short-circuits every filter for an ablation
scope (`if scope.is_ablation: return made(True, ...)`), admitting the
unresolved and archive-stem-conflated lines that the conditioned arm must
refuse. Proposal Sec.9 item 3 requires "data scope identical" while
`language_scope` differs between arms, so the two concepts are recorded as
separate manifest fields here.
"""

import hittite_tokenizer as ht
import language_scope as ls
from hittite_model import apply_span_masking, build_boundary_example, find_boundary_positions
from hittite_model_p4f import LANGUAGE_TO_ID, UNRESOLVED_LANGUAGE, language_ids_for_tokens

# The language id used for every position that carries no lexical language:
# structural specials (<EDGE_*>, <LINE>, <GAP>), the <MASK> token that
# replaces a masked position, and right-padding. All of these are real model
# input positions, so they need SOME row in the embedding table; none of them
# is evidence about a language.
UNRESOLVED_ID = LANGUAGE_TO_ID[UNRESOLVED_LANGUAGE]

# The scope that governs which LINES may contribute tokens. Identical for
# both Stage 1 arms -- see this module's docstring.
DATA_ADMISSION_SCOPE = "MULTILINGUAL_CONDITIONED"


def build_data_admission_scope():
    """The one place the Stage 1 data-admission rule is named."""
    return ls.build_language_scope(DATA_ADMISSION_SCOPE)


def render_example_with_languages(doc_id, line_idxs, line_index, top_edge_lost,
                                  bottom_edge_lost, on_physical_edge_by_line,
                                  *, admission_scope, language_index):
    """One fragment -> (token_strings, language_ids), exactly parallel.

    Lines the admission scope refuses contribute no tokens but keep their
    separator slot, matching how the v1 language filter already treats a
    non-Hittite line (`hittite_tokenizer._line_tokens`): removing the slot
    would renumber line positions that the rest of the pipeline depends on.
    """
    scope = ls.require_language_scope(
        admission_scope, label="p4f_data.render_example_with_languages")

    emptied = set()
    for idx in line_idxs:
        n_source = len(line_index.get((doc_id, idx), []))
        decision = language_index.line_decision(
            scope, doc_id, idx, n_source_tokens=n_source)
        if not decision.in_scope:
            emptied.add(idx)

    tokens, languages = [], []
    for tok, line_idx, word_pos in ht.iter_structured_attested(
            doc_id, line_idxs, line_index, top_edge_lost, bottom_edge_lost,
            on_physical_edge_by_line, emptied_lines=emptied):
        tokens.append(tok)
        if line_idx is None:
            languages.append(None)  # structural special: no lexical language
            continue
        lang, is_structural = language_index.token_language(
            doc_id, line_idx, word_pos)
        languages.append(None if is_structural else lang)

    return tokens, language_ids_for_tokens(languages)


def load_pretrain_data(tok, frags, line_index, edge_info, seq_len,
                       *, admission_scope, language_index):
    """Split -> [{fragment_id, cth, genre_band, ids, lang_ids}].

    Mirrors `Archive/scripts/19_pretrain.py:load_pretrain_data`'s split
    routing exactly -- train + discovery(bin) for gradient updates, dev for
    loss curves only, TEST NEVER TOUCHED -- and adds the parallel language
    vector. Returns (pools, stats) so the caller can report what language
    admission actually excluded instead of only the survivors.
    """
    out = {"train": [], "discovery": [], "dev": []}
    stats = {
        "fragments_seen": 0,
        "fragments_without_edge_info": 0,
        "fragments_too_short": 0,
        "test_side_fragments_skipped": 0,
        "lines_emptied_by_language_admission": 0,
        "tokens_kept": 0,
    }
    for row in frags.itertuples(index=False):
        stats["fragments_seen"] += 1
        if row.fragment_id not in edge_info:
            stats["fragments_without_edge_info"] += 1
            continue
        if row.main_split == "train":
            bucket = "train"
        elif row.is_bin:
            bucket = "discovery"
        elif row.main_split == "dev":
            bucket = "dev"
        else:
            stats["test_side_fragments_skipped"] += 1
            continue  # test-side: NEVER touched, cleanroom rule 1

        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        tokens, lang_ids = render_example_with_languages(
            row.parent_doc, line_idxs, line_index, top_lost, bot_lost, by_line,
            admission_scope=admission_scope, language_index=language_index)

        ids = tok.encode(tokens)[:seq_len]
        lang_ids = lang_ids[:seq_len]
        if len(ids) != len(lang_ids):  # pragma: no cover - structural guard
            raise AssertionError(
                f"{row.fragment_id}: {len(ids)} token ids vs {len(lang_ids)} "
                "language ids after truncation. Tokenizer.encode is 1:1, so "
                "this can only mean the rendering and language vectors were "
                "built by different traversals.")
        if len(ids) < 4:
            stats["fragments_too_short"] += 1
            continue
        stats["tokens_kept"] += len(ids)
        out[bucket].append({
            "fragment_id": row.fragment_id, "cth": row.cth,
            "genre_band": row.genre_band, "ids": ids, "lang_ids": lang_ids,
        })
    return out, stats


def pad_batch(seqs, pad_value, max_len):
    """Right-pad to a fixed width. Used for token ids (pad=tok.pad_id),
    labels (pad=-100) and language ids (pad=UNRESOLVED_ID) alike, so the
    three stay the same shape by construction."""
    out = []
    for s in seqs:
        s = list(s[:max_len])
        out.append(s + [pad_value] * (max_len - len(s)))
    return out


def sample_mlm_batch(pool, tok, cfg, rng, del_span_lengths):
    """(input_ids, labels, lang_ids) as nested lists, all (B, seq_len)."""
    specials_ids = set(tok.encode(ht.SPECIALS))
    mask_id, gap_id = tok.vocab["<MASK>"], tok.vocab["<GAP>"]
    batch_ids, batch_labels, batch_langs = [], [], []
    for _ in range(cfg["mlm_batch_size"]):
        ex = pool[rng.randrange(len(pool))]
        corrupted, labels, langs = apply_span_masking(
            ex["ids"], mask_id, gap_id, len(tok.vocab), specials_ids,
            del_span_lengths, rng, cfg["mask_rate"], cfg["gap_mode_prob"],
            cfg["max_span_len"], aux=ex["lang_ids"])
        # A masked position's own language is exactly what the model must
        # not be told: predicting the token from its own language label
        # would leak part of the answer. <MASK> therefore carries
        # <UNRESOLVED>, like every other non-lexical position. <GAP> gets
        # the same treatment -- it too replaced real content, and although
        # a gap-collapsed span carries no reconstruction target to leak,
        # letting it keep the removed content's language would make <GAP>
        # the one structural special that reports a language it does not
        # have.
        langs = [UNRESOLVED_ID if cid in (mask_id, gap_id) else lang
                 for cid, lang in zip(corrupted, langs)]
        batch_ids.append(corrupted[:cfg["seq_len"]])
        batch_labels.append(labels[:cfg["seq_len"]])
        batch_langs.append(langs[:cfg["seq_len"]])
    return (pad_batch(batch_ids, tok.pad_id, cfg["seq_len"]),
            pad_batch(batch_labels, -100, cfg["seq_len"]),
            pad_batch(batch_langs, UNRESOLVED_ID, cfg["seq_len"]))


def sample_boundary_batch(pool, tok, cfg, rng):
    """(input_ids, boundary_positions, labels, tiers, lang_ids) or None."""
    line_id, par_id = tok.vocab["<LINE>"], tok.vocab["<PAR>"]
    by_genre = {}
    for ex in pool:
        by_genre.setdefault(ex["genre_band"], []).append(ex)

    contexts, conts, labels, tiers, aux_ctx, aux_cont = [], [], [], [], [], []
    attempts = 0
    while (len(contexts) < cfg["boundary_batch_size"]
           and attempts < cfg["boundary_batch_size"] * 20):
        attempts += 1
        ex = pool[rng.randrange(len(pool))]
        boundaries = find_boundary_positions(ex["ids"], line_id, par_id)
        if not boundaries:
            continue
        bp = boundaries[rng.randrange(len(boundaries))]
        neg_pools = {
            "cross_genre": (by_genre.get(ex["genre_band"], pool), ex["cth"]),
            "random": (pool, ex["cth"]),
        }
        result = build_boundary_example(
            ex["ids"], bp, boundaries, rng, neg_pools,
            window=cfg["boundary_window"],
            aux=ex["lang_ids"], aux_key="lang_ids")
        if result is None:
            continue
        ctx, cont, label, tier, a_ctx, a_cont = result
        contexts.append(ctx)
        conts.append(cont)
        labels.append(label)
        tiers.append(tier)
        aux_ctx.append(a_ctx)
        aux_cont.append(a_cont)

    if not contexts:
        return None
    seqs = [c + k for c, k in zip(contexts, conts)]
    lang_seqs = [c + k for c, k in zip(aux_ctx, aux_cont)]
    boundary_positions = [len(c) - 1 for c in contexts]
    max_len = cfg["boundary_seq_len"]
    return (pad_batch(seqs, tok.pad_id, max_len),
            [min(p, max_len - 1) for p in boundary_positions],
            labels, tiers,
            pad_batch(lang_seqs, UNRESOLVED_ID, max_len))
