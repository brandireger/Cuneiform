#!/usr/bin/env python3
"""P4-F Stage 0 (reports/phase4_p4f_gate3_proposal.md): the
language-conditioned encoder architecture.

Not a modification of `Archive/lib/hittite_model.py` -- that file is the
frozen Phase 1 snapshot ("do not rewrite it in place", AGENTS.md) and D14's
checkpoint is a real 60,000-step run whose weights are only meaningful under
its exact, unmodified architecture. This module reproduces
`HittiteEncoder`'s unconditioned forward pass faithfully (verified by
`tests/test_hittite_model_p4f.py`'s parameter-count check against the
figure `Archive/reports/pretrain_report.md` recorded for D14:
12,817,991) and adds exactly the one thing the Gate 3 proposal names: an
optional learned language embedding, summed into the token embedding
before the encoder.

`condition_on_language` controls whether the language pathway exists in the
model AT ALL, not just whether it receives real values -- Stage 1's arm A
(unconditioned) and arm B (conditioned) are the SAME class with this one
constructor flag, rather than two independently-written classes, so
"otherwise identical" (proposal Sec.4) is a code-level guarantee, not a
claim to audit by hand. `encode()` fails closed in both directions: a
conditioned model refuses to run without `lang_ids`, and an unconditioned
model refuses to accept them -- the second case exists specifically to
catch the arm A / arm B cross-contamination the proposal's tracer item 3
is written to guard against (Sec.9).
"""
import torch
import torch.nn as nn

# Canonical vocabulary, ratified 2026-07-25 (specs/LINE_LANG_MIGRATION.md,
# Step C): Hit, Akk, Sum, Hat, Hur, Luw, Pal. `<UNRESOLVED>` is appended as
# an 8th slot for structural tokens (<LINE>, <PAR>, <GAP>, <MASK>, padding
# -- none of which carry a language) and for genuinely unresolved word-level
# language values, matching how the rest of Phase 4 already treats these
# (Gate 2: "62,810 structural tokens excluded from lexical-language
# statistics"). Order matters: it is the embedding table's row order, and
# must match `LANGUAGE_TO_ID` exactly -- pinned together in one place so
# they cannot drift apart.
LANGUAGE_CODES = ("Hit", "Akk", "Sum", "Hat", "Hur", "Luw", "Pal", "<UNRESOLVED>")
UNRESOLVED_LANGUAGE = "<UNRESOLVED>"
LANGUAGE_TO_ID = {code: i for i, code in enumerate(LANGUAGE_CODES)}


class UnrecognizedLanguageCodeError(ValueError):
    """A language value that is neither a canonical code nor None/unresolved.

    Fails closed rather than silently mapping to <UNRESOLVED> -- an
    unexpected value here is a sign the P4-D language layer and this
    module's vocabulary have drifted apart, which is exactly the kind of
    silent mismatch this project's other language-handling code (e.g.
    lib/line_lang_lookup.py) refuses to guess through.
    """


def language_ids_for_tokens(effective_languages):
    """[canonical code or None, ...] -> [int index into LANGUAGE_CODES, ...]

    One entry per token position, same length and order as the model's
    `input_ids` for that example -- alignment is the caller's
    responsibility (typically: the same per-token `effective_lang_canonical`
    values the real-gap and workbench pipelines already read, with
    structural/special-token positions passed as None). None and the
    literal string "<UNRESOLVED>" both map to the UNRESOLVED slot; anything
    else not in the canonical 7 raises rather than being coerced.
    """
    ids = []
    for lang in effective_languages:
        if lang is None or lang == UNRESOLVED_LANGUAGE:
            ids.append(LANGUAGE_TO_ID[UNRESOLVED_LANGUAGE])
            continue
        if lang not in LANGUAGE_TO_ID:
            raise UnrecognizedLanguageCodeError(
                f"{lang!r} is not one of the 7 canonical codes "
                f"{LANGUAGE_CODES[:7]} or None/<UNRESOLVED>. This is either "
                "new corpus data outside the ratified vocabulary or a "
                "genuine bug in whatever produced this value -- not "
                "something to guess through.")
        ids.append(LANGUAGE_TO_ID[lang])
    return ids


class P4FEncoder(nn.Module):
    """Same architecture as D14's `HittiteEncoder`, plus one optional
    addition. Default constructor arguments match D14's recorded config
    exactly (`Archive/reports/pretrain_report.md`): 6 layers, d_model=384,
    6 heads, d_ff=1536, seq_len=512, 12,817,991 params when
    condition_on_language=False."""

    def __init__(self, vocab_size, d_model=384, n_layers=6, n_heads=6,
                 d_ff=1536, seq_len=512, dropout=0.1, pad_id=0,
                 condition_on_language=False,
                 n_language_codes=len(LANGUAGE_CODES)):
        super().__init__()
        self.d_model = d_model
        self.seq_len = seq_len
        self.pad_id = pad_id
        self.condition_on_language = condition_on_language
        self.tok_emb = nn.Embedding(vocab_size, d_model, padding_idx=pad_id)
        self.pos_emb = nn.Embedding(seq_len, d_model)
        # No padding_idx here, deliberately: every position has SOME
        # language ID (structural tokens map to <UNRESOLVED>, not a
        # dedicated pad row), so nothing about this embedding should ever
        # be pinned to zero the way tok_emb's pad rows are.
        self.lang_emb = (
            nn.Embedding(n_language_codes, d_model)
            if condition_on_language else None)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_ff,
            dropout=dropout, activation="gelu", batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.mlm_head = nn.Linear(d_model, vocab_size)
        self.boundary_head = nn.Sequential(
            nn.Linear(d_model, d_model), nn.GELU(), nn.Linear(d_model, 1))
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)

    def encode(self, input_ids, lang_ids=None):
        """Returns hidden states (B, T, D). `lang_ids`: (B, T) long tensor
        of indices into LANGUAGE_CODES, required iff condition_on_language
        -- the mismatch cases both raise rather than silently doing the
        wrong thing, since this is precisely the boundary where an arm A/
        arm B mixup would otherwise pass silently."""
        if self.condition_on_language and lang_ids is None:
            raise ValueError(
                "condition_on_language=True but lang_ids was not provided. "
                "A conditioned model run without a language signal is not "
                "a conditioned run -- this must fail, not silently degrade "
                "to the unconditioned baseline it is being compared against.")
        if not self.condition_on_language and lang_ids is not None:
            raise ValueError(
                "condition_on_language=False but lang_ids was provided. "
                "This is the arm A/arm B cross-contamination the Gate 3 "
                "proposal's tracer item 3 exists to catch (Sec.9) -- an "
                "unconditioned run must never see a language signal, "
                "deliberately or by a wiring mistake.")
        B, T = input_ids.shape
        pos = torch.arange(T, device=input_ids.device).unsqueeze(0).expand(B, T)
        x = self.tok_emb(input_ids) + self.pos_emb(pos)
        if self.condition_on_language:
            x = x + self.lang_emb(lang_ids)
        pad_mask = input_ids == self.pad_id
        h = self.encoder(x, src_key_padding_mask=pad_mask)
        return self.ln_f(h)

    def mlm_logits(self, hidden):
        return self.mlm_head(hidden)

    def boundary_logit(self, hidden, positions):
        """hidden: (B,T,D). positions: (B,) index of the boundary token per
        example. Returns (B,) logits."""
        B = hidden.shape[0]
        picked = hidden[torch.arange(B, device=hidden.device), positions]
        return self.boundary_head(picked).squeeze(-1)

    def mean_pool(self, input_ids, lang_ids=None):
        """D15-style whole-fragment embedding: mean over non-pad
        positions."""
        hidden = self.encode(input_ids, lang_ids=lang_ids)
        mask = (input_ids != self.pad_id).unsqueeze(-1).float()
        summed = (hidden * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1.0)
        return summed / counts


# --------------------------------------------------- Gate 3 proposal Sec.9
# The conditioned-vs-unconditioned tracer, required to pass before either
# Stage 1 run starts. Each check is a canary-scale, no-GPU-epoch-required
# plumbing check in the tradition of scripts/00_tracers.py's T1-T5 and
# lib/contracts.py's C1-C10 -- it cannot tell you conditioning HELPS, only
# that the mechanism is actually wired the way the comparison assumes.
# scripts/phase4_p4f_conditioning_tracer.py is the runnable entry point;
# the functions live here, beside the model they inspect.

def language_embedding_table_not_collapsed(lang_emb, *, max_cosine_similarity=0.99):
    """Tracer item 1. Every pair of language-embedding rows must be
    distinguishable at initialization. Catches a degenerate init -- e.g. a
    stray `padding_idx` added to `lang_emb` later for "consistency" with
    `tok_emb`, which would silently zero the <UNRESOLVED> row (by far the
    most common one, since every structural token maps to it) and freeze
    its gradient. Returns (passed: bool, worst_pair: (i, j, similarity))."""
    weight = lang_emb.weight.detach()
    normed = weight / weight.norm(dim=1, keepdim=True).clamp(min=1e-8)
    sim = normed @ normed.T
    n = sim.shape[0]
    worst = (-1, -1, -1.0)
    for i in range(n):
        for j in range(i + 1, n):
            value = sim[i, j].item()
            if value > worst[2]:
                worst = (i, j, value)
    return worst[2] <= max_cosine_similarity, worst


def conditioning_changes_forward_pass(model, input_ids, real_lang_ids, *, atol=1e-5):
    """Tracer item 2. `model` must have condition_on_language=True. Runs
    the SAME input_ids through the model with real_lang_ids and again with
    every position forced to the same constant language id; the two hidden
    states must differ beyond floating-point noise. If they don't, the
    language pathway is not reaching the computation regardless of what
    the training loop reports -- exactly the class of bug
    P5_CLOSEOUT.md Sec.2.4 already found once (five scripts silently fed a
    frozen model blank-page input for months because nothing checked the
    input pipeline was actually wired). Returns (passed: bool,
    max_abs_difference: float)."""
    if not model.condition_on_language:
        raise ValueError(
            "conditioning_changes_forward_pass requires a "
            "condition_on_language=True model -- there is no pathway to "
            "test on an unconditioned one.")
    model.eval()
    with torch.no_grad():
        real = model.encode(input_ids, lang_ids=real_lang_ids)
        constant_lang_ids = torch.zeros_like(real_lang_ids)
        constant = model.encode(input_ids, lang_ids=constant_lang_ids)
    max_diff = (real - constant).abs().max().item()
    return max_diff > atol, max_diff


def manifests_differ_only_in(manifest_a, manifest_b, *, expected_differing_keys):
    """Tracer item 3. Compares two Stage 1 run manifests (flat dicts) and
    confirms only `expected_differing_keys` actually differ -- catches an
    accidental confound (e.g. arm B silently also getting a different
    learning rate or seed) that would invalidate the falsifier's comparison
    even if both runs individually "succeed". Returns (passed: bool,
    unexpectedly_differing_keys: set, missing_expected_differences: set)."""
    all_keys = set(manifest_a) | set(manifest_b)
    actually_differing = {
        key for key in all_keys
        if manifest_a.get(key) != manifest_b.get(key)
    }
    expected = set(expected_differing_keys)
    unexpected = actually_differing - expected
    missing = expected - actually_differing
    return not unexpected and not missing, unexpected, missing
