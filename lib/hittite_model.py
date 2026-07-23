#!/usr/bin/env python3
"""
hittite_model.py -- P4 D14: from-scratch transformer encoder + the
masking/boundary-example construction utilities used to pretrain it.

Reusable module (unnumbered, same reason as eval_harness.py) --
imported by 19_pretrain.py and 20_biencoder.py.

ARCHITECTURE ADAPTATION NOTE (documented, not silently assumed): spec
calls the span-infilling objective "T5-style variable-length span
corruption". True T5 collapses a masked span to ONE sentinel token and
reconstructs it via a decoder -- this project builds an ENCODER-ONLY
model (needed for D15's bi-encoder anyway), which has no decoder to
generate a variable-length sequence from one position. Adaptation:
a span of sampled length L is replaced by L copies of <MASK> (multi-
position masking, like BERT, but with SPAN boundaries and lengths
drawn from the calibrated del-span distribution rather than
independent per-token masking -- that calibrated-span-length choice is
the actual "clay-realistic vs uniform Ithaca masking" difference the
spec cares about, and is preserved exactly). A separate, lower-
probability <GAP>-collapse mode (single sentinel, no reconstruction
loss -- pure input corruption for robustness) is also implemented,
closer in spirit to true unknown-length-span T5 masking, but without a
loss target since encoder-only can't generate variable length output
from one position.

Boundary-validity task: implemented as a next-unit-prediction pair
(context window ending at a <LINE>/<PAR> boundary + a following-unit
window, TRUE continuation vs impostor per the negatives curriculum),
concatenated into one sequence and classified from the boundary
token's hidden state -- not an in-place full-sequence content swap
(which would need variable-length splicing); this is a clean,
tractable generalization of BERT-style next-sentence-prediction to
line/paragraph granularity.
"""

import torch
import torch.nn as nn


# ---------------------------------------------------------------- model

class HittiteEncoder(nn.Module):
    def __init__(self, vocab_size, d_model=384, n_layers=6, n_heads=6,
                 d_ff=1536, seq_len=512, dropout=0.1, pad_id=0):
        super().__init__()
        self.d_model = d_model
        self.seq_len = seq_len
        self.pad_id = pad_id
        self.tok_emb = nn.Embedding(vocab_size, d_model, padding_idx=pad_id)
        self.pos_emb = nn.Embedding(seq_len, d_model)
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

    def encode(self, input_ids):
        """Returns hidden states (B, T, D)."""
        B, T = input_ids.shape
        pos = torch.arange(T, device=input_ids.device).unsqueeze(0).expand(B, T)
        x = self.tok_emb(input_ids) + self.pos_emb(pos)
        pad_mask = input_ids == self.pad_id
        h = self.encoder(x, src_key_padding_mask=pad_mask)
        return self.ln_f(h)

    def mlm_logits(self, hidden):
        return self.mlm_head(hidden)

    def boundary_logit(self, hidden, positions):
        """hidden: (B,T,D). positions: (B,) index of the boundary token
        per example. Returns (B,) logits."""
        B = hidden.shape[0]
        picked = hidden[torch.arange(B, device=hidden.device), positions]
        return self.boundary_head(picked).squeeze(-1)

    def mean_pool(self, input_ids):
        """D15 whole-fragment embedding: mean over non-pad positions."""
        hidden = self.encode(input_ids)
        mask = (input_ids != self.pad_id).unsqueeze(-1).float()
        summed = (hidden * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1.0)
        return summed / counts

    @torch.no_grad()
    def line_embeddings(self, input_ids, line_id):
        """D15 line/passage-level scoring ablation (no separate
        training -- same encoder, different pooling granularity at eval
        time, per the matrix model's 'aggregate over aligned row-pairs'
        principle). Returns list (len B) of (n_lines_i, D) tensors:
        mean-pooled hidden states of the tokens between consecutive
        <LINE> markers (and sequence start/end), computed from ONE
        forward pass, not one pass per line."""
        hidden = self.encode(input_ids)  # (B, T, D)
        B, T = input_ids.shape
        out = []
        for b in range(B):
            ids = input_ids[b]
            bounds = [-1] + [i for i in range(T) if ids[i].item() == line_id]
            real_len = int((ids != self.pad_id).sum().item())
            bounds.append(real_len)
            bounds = sorted(set(x for x in bounds if x <= real_len))
            segs = []
            for s, e in zip(bounds, bounds[1:]):
                lo, hi = s + 1, e
                if hi <= lo:
                    continue
                segs.append(hidden[b, lo:hi].mean(dim=0))
            out.append(torch.stack(segs) if segs else hidden[b, :1] * 0.0)
        return out


# ---------------------------------------------------------------- masking

def apply_span_masking(token_ids, mask_id, gap_id, vocab_size, specials_ids,
                        del_span_lengths, rng, mask_rate=0.15, gap_mode_prob=0.3,
                        max_span_len=20):
    """token_ids: list[int]. Returns (corrupted_ids, labels) where
    labels[i] = original token id if position i should be predicted
    (i.e. is a <MASK> position from a reconstruction-target span), else
    -100 (ignored in loss, matching torch's CrossEntropyLoss default
    ignore_index convention)."""
    n = len(token_ids)
    maskable = [i for i, t in enumerate(token_ids) if t not in specials_ids]
    budget = int(len(maskable) * mask_rate)
    corrupted = list(token_ids)
    labels = [-100] * n
    covered = set()
    used = 0
    attempts = 0
    while used < budget and attempts < budget * 10:
        attempts += 1
        length = del_span_lengths[rng.randrange(len(del_span_lengths))]
        length = max(1, min(length, max_span_len))
        start = rng.randrange(n)
        span = list(range(start, min(start + length, n)))
        span = [i for i in span if i not in covered and token_ids[i] not in specials_ids]
        if not span:
            continue
        if rng.random() < gap_mode_prob:
            # collapse to a single <GAP>, no reconstruction loss target
            first = span[0]
            corrupted[first] = gap_id
            for i in span[1:]:
                corrupted[i] = None  # marked for removal
            for i in span:
                covered.add(i)
            used += len(span)
        else:
            for i in span:
                labels[i] = token_ids[i]
                corrupted[i] = mask_id
                covered.add(i)
            used += len(span)
    # remove positions marked None (gap-collapsed extra slots), re-pad at caller
    out_ids = [c for c in corrupted if c is not None]
    out_labels = [labels[i] for i, c in enumerate(corrupted) if c is not None]
    return out_ids, out_labels


# ---------------------------------------------------------------- boundary examples

def find_boundary_positions(tokens, line_id, par_id):
    return [i for i, t in enumerate(tokens) if t in (line_id, par_id)]


def build_boundary_example(tokens, boundary_pos, all_boundary_pos, rng,
                            negatives_pool, window=32, max_reject_tries=8):
    """tokens: list[int] for the source fragment. boundary_pos: index
    of a <LINE>/<PAR> token within `tokens`. all_boundary_pos: every
    boundary position in `tokens` (for the in-document negative tier).
    negatives_pool: dict tier -> (candidate_list, exclude_cth) for
    'cross_genre' and 'random' tiers. candidate_list is the caller's
    FULL (unfiltered) pool/genre-group -- same-CTH exclusion (protects
    duplicate-witness signal, per spec) is done here via bounded
    rejection sampling, not by the caller pre-filtering the whole pool.

    PERF (2026-07-21, approved by architect, see 19_pretrain.py's PERF
    note): the original contract took a PRE-FILTERED list, which meant
    the caller rebuilt an O(pool_size) list comprehension on every
    single call inside sample_boundary_batch's retry loop (up to
    boundary_batch_size*20 times) -- measured at 1.1-2.2s of a
    1.5-3.1s step, i.e. the actual bottleneck, not GPU compute (which
    profiled at ~350-700ms). Rejection sampling touches O(1) items per
    try instead. candidate_list items are the same dicts sample_
    boundary_batch already holds ({'fragment_id','cth','genre_band',
    'ids'}), so no pre-extraction is needed either.

    Returns (context, continuation, label, tier) or None if there
    isn't enough content on either side -- tier is one of
    'true_continuation', 'in_doc', 'cross_genre', 'random', added for
    the D14 report's per-negative-type AUC breakdown
    (21_pretrain_report.py); training callers may ignore it."""
    context = tokens[max(0, boundary_pos - window):boundary_pos + 1]
    true_cont = tokens[boundary_pos + 1: boundary_pos + 1 + window]
    if len(true_cont) < 4 or len(context) < 4:
        return None
    if rng.random() < 0.5:
        return context, true_cont, 1, "true_continuation"
    # negative: curriculum order in_doc -> cross_genre -> random
    in_doc_candidates = [p for p in all_boundary_pos if abs(p - boundary_pos) > window]
    if in_doc_candidates:
        p = in_doc_candidates[rng.randrange(len(in_doc_candidates))]
        cand = tokens[p + 1: p + 1 + window]
        if len(cand) >= 4:
            return context, cand, 0, "in_doc"
    for tier in ("cross_genre", "random"):
        cand_list, exclude_cth = negatives_pool.get(tier, ([], None))
        if not cand_list:
            continue
        for _ in range(max_reject_tries):
            other = cand_list[rng.randrange(len(cand_list))]
            if other["cth"] == exclude_cth:
                continue
            other_tokens = other["ids"]
            if len(other_tokens) > window:
                start = rng.randrange(0, len(other_tokens) - window)
                cand = other_tokens[start:start + window]
                if len(cand) >= 4:
                    return context, cand, 0, tier
            break
    return None
