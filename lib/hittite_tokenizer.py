#!/usr/bin/env python3
"""
hittite_tokenizer.py -- P4 Deliverable D12: sign-level tokenizer.

Reusable module (like eval_harness.py; same digit-prefix import
restriction, hence unnumbered) -- imported by 18_fracture.py,
19_pretrain.py, 20_biencoder.py.

AMENDED 2026-07-22 (approved by architect, see tokenizer_report.md
"Target-vs-actual tension" for the original finding that triggered
this): word-level tokenization no longer treats a whole logogram/
Sumerogram/Akkadogram/determinative word as ONE atomic token. That
rule (reused verbatim from P3's bm25_sign) was fine for BM25 term
weighting but combinatorially expensive for a fixed neural vocab
(12,632 of 14,160 vocab entries were whole-word logogram forms).
Sign-level decomposition now matches what's physically on the tablet:
sGr/aGr/d content splits on '-'/'.' (GIŠ.DINANNA -> GIŠ + DINANNA;
DINGIR-LIM -> DINGIR + LIM; DUTU-uš -> D + UTU + uš), except a run
containing '×' (ligature compounds like KA×U) stays atomic. This
requires token boundaries that P2's corpus.parquet does NOT preserve
(it flattens a whole word's text before hyphen-splitting, losing the
<d>/<sGr>/<aGr> tag edges) -- so this module now consumes a NEW P4-
only artifact, Phase1_pipeline/p4_out/decomposed_corpus.parquet, built by
decompose_corpus.py re-walking the raw XML with tag-boundary-aware
segmentation. P2/P2.5's corpus.parquet is untouched and still frozen.

Case is preserved for logogram-class tokens (script class is free
signal via case: DUTU-derived tokens are uppercase, syllabic tokens
lowercase) -- no separate type marker needed.

Structural markers: <LINE> at line breaks, <PAR> already embedded
inline at parsep boundaries by decompose_corpus.py, <EDGE_T>/<EDGE_B>
at the fragment's top/bottom per edges.parquet's top_edge_lost/
bottom_edge_lost (a genuine physical edge gets the EDGE token; a
break gets <GAP> instead, since span length there is unknown), and
<EDGE_L>/<EDGE_R> inline at any line marked on_physical_edge.

Vocabulary source: TRAIN-side + discovery-pool ATTESTED text only
(dev/test never touch vocabulary construction). min_df=2.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

import eval_harness as eh
from decompose_corpus import RESTORED, build_decomposed_cache
from line_lang_lookup import is_hittite_line

SPECIALS = ["<PAD>", "<UNK>", "<MASK>", "<GAP>", "<LINE>", "<PAR>",
            "<EDGE_L>", "<EDGE_R>", "<EDGE_T>", "<EDGE_B>"]
MIN_DF = 2
TOKENIZER_PATH = Path("configs") / "tokenizer.json"
DECOMPOSED_PATH = Path("Phase1_pipeline/p4_out") / "decomposed_corpus.parquet"


def build_decomposed_line_index():
    """Returns dict (doc_id, line_index_in_doc) -> ordered list of
    (token, damage_state), sorted by word_pos. Single source of
    per-line token content for everything below."""
    if not DECOMPOSED_PATH.exists():
        build_decomposed_cache(str(Path("TLHdig_0.2.0-beta.zip")))
    df = pd.read_parquet(DECOMPOSED_PATH)
    df = df.sort_values(["doc_id", "line_index_in_doc", "word_pos"])
    idx = defaultdict(list)
    for row in df.itertuples(index=False):
        idx[(row.doc_id, row.line_index_in_doc)].append((row.token, row.damage_state))
    return idx


def _line_tokens(doc_id, idx, line_index, line_lang_lookup):
    """Raw (token, state) list for one line, emptied (not removed --
    line-position numbering elsewhere depends on every slot staying
    present) if line_lang_lookup is given and the line isn't confirmed
    Hittite. line_lang_lookup=None preserves old (language-blind)
    behaviour for any caller not yet updated."""
    toks = line_index.get((doc_id, idx), [])
    if line_lang_lookup is not None and not is_hittite_line(
            line_lang_lookup, doc_id, idx):
        return []
    return toks


def build_structured_sequence(doc_id, line_idxs, line_index, top_edge_lost,
                               bottom_edge_lost, on_physical_edge_by_line,
                               line_lang_lookup=None):
    """FULL rendering: all tokens regardless of damage state."""
    seq = ["<EDGE_T>" if not top_edge_lost else "<GAP>"]
    sorted_idxs = sorted(line_idxs)
    for pos, idx in enumerate(sorted_idxs):
        toks = _line_tokens(doc_id, idx, line_index, line_lang_lookup)
        line_edge = on_physical_edge_by_line.get(idx)
        if line_edge == "left":
            seq.append("<EDGE_L>")
        seq.extend(t for t, _ in toks)
        if line_edge == "right":
            seq.append("<EDGE_R>")
        if pos < len(sorted_idxs) - 1:
            seq.append("<LINE>")
    seq.append("<EDGE_B>" if not bottom_edge_lost else "<GAP>")
    return seq


def iter_structured_attested(doc_id, line_idxs, line_index, top_edge_lost,
                              bottom_edge_lost, on_physical_edge_by_line,
                              line_lang_lookup=None, emptied_lines=None):
    """The single traversal behind ATTESTED rendering. Yields
    (token_string, line_index_in_doc_or_None, word_pos_or_None).

    line_index_in_doc/word_pos are None for structural specials
    (<EDGE_*>, <LINE>, <GAP>) and carry the token's exact source
    identity otherwise. `word_pos` is the position in the line's FULL
    token list, counted BEFORE restored tokens are dropped -- that is
    the identity the Gate 2 language dataset is keyed by
    (lib/language_lookup_v2.py), so a consumer can attach a per-token
    language without re-deriving positions from the filtered output.

    Extracted (2026-08-02, P4-F Stage 0) so the language-conditioned
    data path in `lib/p4f_data.py` shares ONE implementation of this
    traversal with `build_structured_sequence_attested` below, rather
    than reimplementing the emit order and then drifting from it. A
    parallel implementation of a model-input construction step is the
    exact shape of the E2 defect (CLAUDE.md, "Model-input encoding").

    emptied_lines: optional set of line indices whose token content is
    suppressed, with their separator slots preserved -- the same
    treatment `_line_tokens` gives a language-filtered line, exposed so
    a v2 (word-aware) caller can apply its own admission decision
    without this module depending on the Phase 4 language stack."""
    yield ("<EDGE_T>" if not top_edge_lost else "<GAP>", None, None)
    sorted_idxs = sorted(line_idxs)
    for pos, idx in enumerate(sorted_idxs):
        toks = _line_tokens(doc_id, idx, line_index, line_lang_lookup)
        if emptied_lines is not None and idx in emptied_lines:
            toks = []
        line_edge = on_physical_edge_by_line.get(idx)
        if line_edge == "left":
            yield ("<EDGE_L>", None, None)
        for word_pos, (t, st) in enumerate(toks):
            if st != RESTORED:
                yield (t, idx, word_pos)
        if line_edge == "right":
            yield ("<EDGE_R>", None, None)
        if pos < len(sorted_idxs) - 1:
            yield ("<LINE>", None, None)
    yield ("<EDGE_B>" if not bottom_edge_lost else "<GAP>", None, None)


def build_structured_sequence_attested(doc_id, line_idxs, line_index, top_edge_lost,
                                        bottom_edge_lost, on_physical_edge_by_line,
                                        line_lang_lookup=None):
    """ATTESTED rendering: drops tokens with damage_state=='restored'.
    Specials (<NUM>, <PAR>, ...) carry damage_state 'attested' by
    convention from decompose_corpus.py and are always kept.

    line_lang_lookup: optional {(doc_id, line_index_in_doc): canonical}
    from line_lang_lookup.load_line_lang_lookup(). When given, a line
    not confirmed Hittite contributes no tokens (its <LINE> separator
    slot is preserved so line-position numbering elsewhere is
    unaffected) -- see CLAUDE.md's multilingual-layer note; this keeps
    non-Hittite content out of a Hittite-only rendering without
    discarding it from the underlying corpus."""
    return [tok for tok, _, _ in iter_structured_attested(
        doc_id, line_idxs, line_index, top_edge_lost, bottom_edge_lost,
        on_physical_edge_by_line, line_lang_lookup)]


def encode_fragment_window(lines, *, include_restored=False):
    """Canonical (token, damage_state) line-structure -> flat token
    STRING list with <LINE> separators (not yet encoded to ids). THE
    single path for this operation, per P5C_AMENDMENT_2.md H1 -- local
    reimplementations (the "flatten_lines" pattern that caused E2) are
    forbidden; import this instead.

    lines: [(line_idx, [(token, damage_state), ...]), ...], the
    structure fracture_engine.get_fragment_tokens() returns. Also
    accepts lines whose per-line list is already plain strings (e.g.
    fracture_engine.render_tokens()-derived synthetic pairs reshaped
    via tokens_to_lines()) -- handled transparently so callers don't
    need to know which representation they were handed.

    include_restored: if True, keep tokens marked damage_state=
    'restored' (default False -- matches get_fragment_tokens()'s own
    default of dropping them; only pass True if the caller explicitly
    wants restoration-inclusive rendering, e.g. FULL, never TEST-side
    or eval-side per the cleanroom rules)."""
    flat = []
    for i, (idx, toks) in enumerate(lines):
        for item in toks:
            if isinstance(item, tuple):
                tok, state = item
                if state == "restored" and not include_restored:
                    continue
                flat.append(tok)
            else:
                flat.append(item)
        if i < len(lines) - 1:
            flat.append("<LINE>")
    return flat


def load_edge_info():
    """Returns dict fragment_id -> (line_idxs, top_edge_lost,
    bottom_edge_lost, {line_idx: on_physical_edge})."""
    edges = pd.read_parquet(eh.P2_OUT / "edges.parquet")
    out = {}
    for row in edges.itertuples(index=False):
        lines = json.loads(row.lines)
        line_idxs = [pl["line_index_in_doc"] for pl in lines]
        by_line = {pl["line_index_in_doc"]: pl.get("on_physical_edge")
                   for pl in lines if pl.get("on_physical_edge")}
        out[row.fragment_id] = (line_idxs, bool(row.top_edge_lost),
                                 bool(row.bottom_edge_lost), by_line)
    return out


class Tokenizer:
    def __init__(self, vocab, specials):
        self.specials = specials
        self.vocab = vocab  # token -> id (specials first, then sorted vocab)
        self.id_to_token = {v: k for k, v in vocab.items()}
        self.unk_id = vocab["<UNK>"]
        self.pad_id = vocab["<PAD>"]

    def encode(self, tokens, strict=True):
        """strict=True (default, per P5C_AMENDMENT_2.md H1): every
        element must be str, or this raises immediately with the
        offending element in the message. A permissive `.get(t, unk)`
        lookup is exactly the mechanism that silently absorbed E2's
        (token, damage_state) tuples as an entire phase of <UNK> soup
        -- strict mode turns that class of bug into a crash at the
        first bad token instead of a silently-degraded score."""
        if strict:
            for i, t in enumerate(tokens):
                if not isinstance(t, str):
                    raise TypeError(
                        f"Tokenizer.encode: element {i} is {type(t).__name__} "
                        f"({t!r}), not str. Model-input encoding must go through "
                        f"encode_fragment_window() (or another str-only source) "
                        f"before reaching Tokenizer.encode(). See CLAUDE.md's "
                        f"'Model-input encoding' convention.")
        return [self.vocab.get(t, self.unk_id) for t in tokens]

    def decode(self, ids):
        return [self.id_to_token.get(i, "<UNK>") for i in ids]

    def save(self, path=TOKENIZER_PATH):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"vocab": self.vocab, "specials": self.specials,
                       "min_df": MIN_DF}, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path=TOKENIZER_PATH):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls(d["vocab"], d["specials"])


def build_vocab(frags, line_index, edge_info, line_lang_lookup=None):
    """TRAIN-side + discovery-pool ATTESTED text only. Returns
    (Tokenizer, doc_freq Counter, n_docs_used).

    line_lang_lookup: optional, see build_structured_sequence_attested.
    Passing the ratified line_lang_lookup here makes this a
    Hittite-only vocabulary -- the intended default going forward per
    specs/LINE_LANG_MIGRATION.md; omit only to reproduce the original
    Phase 1 (language-blind) vocab exactly."""
    pop = frags[(frags["main_split"] == "train") | (frags["is_bin"])]
    doc_freq = Counter()
    n_docs = 0
    for row in pop.itertuples(index=False):
        if row.fragment_id not in edge_info:
            continue
        line_idxs, top_lost, bot_lost, by_line = edge_info[row.fragment_id]
        seq = build_structured_sequence_attested(
            row.parent_doc, line_idxs, line_index, top_lost, bot_lost, by_line,
            line_lang_lookup=line_lang_lookup)
        n_docs += 1
        for t in set(seq):
            if t not in SPECIALS:
                doc_freq[t] += 1
    kept = sorted([t for t, c in doc_freq.items() if c >= MIN_DF])
    vocab = {t: i for i, t in enumerate(SPECIALS)}
    for t in kept:
        vocab[t] = len(vocab)
    return Tokenizer(vocab, SPECIALS), doc_freq, n_docs
