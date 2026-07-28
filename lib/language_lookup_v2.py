"""Word-aware effective-language reader over the accepted Gate 2 dataset.

This is the v2 successor to `lib/line_lang_lookup.py`. That module reads
`line_lang_canonical` at LINE granularity and can only answer "is this line
tagged Hittite". It therefore cannot see the 7,100 valid word-over-line
overrides Gate 0 found -- notably 5,670 `Hit`-line / `Hur`-word cases, whose
Hurrian words are currently admitted into "Hittite-only" anchor construction.

Source of truth is `Phase4/phase4_out/multilingual_tokens_v2.parquet`
(Gate 2, logical SHA-256 35914a01...), which carries `effective_lang_*` per
token under the ratified `word_override_else_line_v2` rule.

Two fail-closed properties matter more than coverage here:

1. **Positional safety.** The Gate 2 dataset is keyed by an exact
   `(doc_id, line_index_in_doc, word_pos)` identity, verified unique and
   contiguous from 0 per line. The historical decomposed cache that active
   scripts render from is NOT: it carries 9,940 rows under duplicated keys
   across 28 documents, the archive-stem conflation recorded in
   PHASE4_SUCCESSOR_HANDOFF.md. Rather than trusting a doc-id blocklist,
   every lookup compares the caller's own token count for the line against
   the Gate 2 token count and refuses the line on any mismatch. A conflated
   line cannot silently borrow another stem's language assignment.

2. **Unresolved is not Hittite.** A line with any unresolved lexical token
   (malformed/unrecognized word tag, no valid line value to inherit) is
   excluded from every language-restricted scope, never guessed in.

Decisions are counted as they are made so the calling script can report what
its language scope actually excluded, with reasons, instead of reporting only
the surviving population.
"""

import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

import language_scope as ls


TOKENS_V2_PATH = Path("Phase4/phase4_out/multilingual_tokens_v2.parquet")

_COLUMNS = [
    "doc_id",
    "line_index_in_doc",
    "word_pos",
    "effective_lang_canonical",
    "effective_lang_status",
    "is_structural_token",
]

# Why a line was refused by a language scope. Reported verbatim so a
# coverage drop can be attributed rather than guessed at.
REASON_IN_SCOPE = "IN_SCOPE"
REASON_LINE_NOT_COVERED = "LINE_NOT_IN_LANGUAGE_DATASET"
REASON_TOKEN_COUNT_MISMATCH = "TOKEN_COUNT_MISMATCH_CONFLATED_SOURCE"
REASON_UNRESOLVED = "UNRESOLVED_LEXICAL_LANGUAGE"
REASON_MIXED = "MIXED_LANGUAGE_LINE"
REASON_OTHER_LANGUAGE = "OUT_OF_SCOPE_LANGUAGE"


@dataclass(frozen=True)
class LineDecision:
    """One line's admission decision under one scope."""

    in_scope: bool
    reason: str
    languages: frozenset
    n_lexical_tokens: int
    n_unresolved_lexical: int

    @property
    def sole_language(self):
        """The line's single resolved language, or None if 0 or >1."""
        return next(iter(self.languages)) if len(self.languages) == 1 else None


class EffectiveLanguageIndex:
    """Per-line effective-language view of the Gate 2 token dataset."""

    def __init__(self, lines, *, source_path, source_sha256, n_rows, n_docs):
        self._lines = lines
        self.source_path = str(source_path)
        self.source_sha256 = source_sha256
        self.n_rows = n_rows
        self.n_docs = n_docs
        self.decision_counts = Counter()

    # ---------------------------------------------------------------- reads

    def has_line(self, doc_id, line_index_in_doc):
        return (doc_id, int(line_index_in_doc)) in self._lines

    def line_languages(self, doc_id, line_index_in_doc):
        """Resolved lexical languages on this line (structural tokens are
        excluded, per Gate 0 decision 6: they inherit a language for layout
        purposes but are never lexical language evidence)."""
        entry = self._lines.get((doc_id, int(line_index_in_doc)))
        if entry is None:
            return frozenset()
        langs, structural = entry
        return frozenset(
            lang for lang, is_struct in zip(langs, structural)
            if not is_struct and lang is not None)

    def token_language(self, doc_id, line_index_in_doc, word_pos):
        """(canonical_language_or_None, is_structural) for one exact token.

        Raises KeyError for an unknown line, and IndexError for a word_pos
        the language dataset does not cover -- both are identity failures
        that must not resolve to a default.
        """
        entry = self._lines[(doc_id, int(line_index_in_doc))]
        langs, structural = entry
        return langs[int(word_pos)], structural[int(word_pos)]

    # ------------------------------------------------------------ decisions

    def line_decision(
            self, language_scope, doc_id, line_index_in_doc,
            *, n_source_tokens, record=True):
        """Decide whether one line's content is admitted under `scope`.

        `n_source_tokens` is the caller's own token count for the line (from
        the historical decomposed cache). Any disagreement with the Gate 2
        count refuses the line -- see this module's docstring, property 1.
        """
        scope = ls.require_language_scope(
            language_scope, label="EffectiveLanguageIndex.line_decision")

        entry = self._lines.get((doc_id, int(line_index_in_doc)))
        if entry is None:
            decision = LineDecision(
                scope.is_ablation, REASON_LINE_NOT_COVERED, frozenset(), 0, 0)
        else:
            langs, structural = entry
            if len(langs) != int(n_source_tokens):
                decision = LineDecision(
                    False, REASON_TOKEN_COUNT_MISMATCH, frozenset(),
                    len(langs), 0)
            else:
                decision = self._classify(scope, langs, structural)

        if record:
            self.decision_counts[(scope.scope, decision.reason)] += 1
        return decision

    def _classify(self, scope, langs, structural):
        lexical = [
            lang for lang, is_struct in zip(langs, structural)
            if not is_struct]
        resolved = frozenset(lang for lang in lexical if lang is not None)
        n_unresolved = sum(1 for lang in lexical if lang is None)

        def made(in_scope, reason):
            return LineDecision(
                in_scope, reason, resolved, len(lexical), n_unresolved)

        # The ablation scope intentionally carries no language identity, so
        # it admits everything -- including unresolved and conflated lines.
        if scope.is_ablation:
            return made(True, REASON_IN_SCOPE)

        # A line with no lexical content renders empty either way; admitting
        # it keeps per-fragment line numbering identical without adding any
        # cross-language content.
        if not lexical:
            return made(True, REASON_IN_SCOPE)

        if n_unresolved:
            return made(False, REASON_UNRESOLVED)

        if scope.scope == "MULTILINGUAL_CONDITIONED":
            return made(True, REASON_IN_SCOPE)

        if scope.scope == "HITTITE_ONLY":
            permitted = {"Hit"}
        elif scope.scope == "SAME_LANGUAGE_AS_QUERY":
            permitted = {scope.query_language}
        elif scope.scope == "CROSS_LANGUAGE_PARALLEL":
            # Different-language evidence only, and still single-language per
            # line so an admitted line cannot smuggle the query language back
            # in as a mixed remainder.
            if len(resolved) > 1:
                return made(False, REASON_MIXED)
            if scope.query_language in resolved:
                return made(False, REASON_OTHER_LANGUAGE)
            return made(True, REASON_IN_SCOPE)
        else:  # pragma: no cover - validate_language_scope covers the space
            raise ls.LanguageScopeError(
                f"Unhandled language scope: {scope.scope!r}")

        if len(resolved) > 1:
            return made(False, REASON_MIXED)
        if resolved <= permitted:
            return made(True, REASON_IN_SCOPE)
        return made(False, REASON_OTHER_LANGUAGE)

    # ------------------------------------------------------------ reporting

    def decision_summary(self):
        """{scope_name: {reason: count}} for the run report/manifest."""
        summary = {}
        for (scope_name, reason), count in sorted(self.decision_counts.items()):
            summary.setdefault(scope_name, {})[reason] = count
        return summary

    def manifest_entry(self):
        # `rows_loaded`/`documents_loaded`, not dataset totals: an index is
        # normally filtered to the run's own documents, and a manifest that
        # implied full-corpus coverage would misstate the universe.
        # The checksum is of the whole Parquet file, so it identifies the
        # artifact regardless of the filter; it is NOT the Gate 2 logical
        # row hash and must not be compared against it.
        return {
            "language_dataset_path": self.source_path,
            "language_dataset_file_sha256": self.source_sha256,
            "language_dataset_rows_loaded": self.n_rows,
            "language_dataset_documents_loaded": self.n_docs,
            "line_decisions": self.decision_summary(),
        }


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_effective_language_index(doc_ids=None, path=TOKENS_V2_PATH):
    """Load the Gate 2 language dataset, optionally scoped to `doc_ids`.

    Raises if the accepted artifact is absent -- fail closed rather than
    degrade to the line-granularity v1 filter without saying so.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run "
            "`python scripts/phase4_multilingual_token_dataset.py` (Gate 2) "
            "before any code that requires word-aware language resolution.")

    filters = None
    if doc_ids is not None:
        doc_ids = list(doc_ids)
        if not doc_ids:
            raise ValueError(
                "load_effective_language_index: empty doc_ids selection")
        filters = [("doc_id", "in", doc_ids)]

    frame = pd.read_parquet(path, columns=_COLUMNS, filters=filters)
    frame = frame.sort_values(["doc_id", "line_index_in_doc", "word_pos"])

    lines = {}
    for (doc_id, line_idx), group in frame.groupby(
            ["doc_id", "line_index_in_doc"], sort=False):
        positions = group["word_pos"].tolist()
        # Contiguity is an identity guarantee of the accepted dataset; if it
        # ever breaks, positional lookup would silently misattribute a
        # language, so check rather than assume.
        if positions != list(range(len(positions))):
            raise AssertionError(
                "load_effective_language_index: non-contiguous word_pos for "
                f"({doc_id!r}, {int(line_idx)}) -- positional language "
                "lookup is unsafe for this line.")
        langs = tuple(
            None if pd.isna(value) else value
            for value in group["effective_lang_canonical"].tolist())
        structural = tuple(bool(v) for v in group["is_structural_token"])
        lines[(doc_id, int(line_idx))] = (langs, structural)

    return EffectiveLanguageIndex(
        lines,
        source_path=path,
        source_sha256=_sha256(path),
        n_rows=int(len(frame)),
        n_docs=int(frame["doc_id"].nunique()),
    )


def hittite_only_projection(doc_ids, *, path=TOKENS_V2_PATH):
    """(scope, index) for the ratified word-aware Hittite-only projection.

    The single helper the active P2-E and real-gap scripts call, so the
    scope name, mixed-line policy, and dataset path are declared identically
    everywhere instead of eight times by hand.
    """
    scope = ls.build_language_scope("HITTITE_ONLY")
    index = load_effective_language_index(doc_ids, path=path)
    return scope, index
