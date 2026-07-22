# H2 — Tokenization-path audit

Per specs/P5C_AMENDMENT_2.md H2. Every call site in the repo that
encodes fragment content into a model (training or scoring) is listed
below, verdicted by EXECUTION (encode one real fragment, inspect the
resulting ids and UNK rate) — not by reading code. Corpus-wide
baseline OOV rate (per `reports/tokenizer_report.md`) is ~0.16%;
C1's contract threshold (P5C_AMENDMENT_2.md H3) is 5%.

## Call-site table

| script | function | path into tokenizer | verdict | UNK rate (measured) |
|---|---|---|---|---|
| `scripts/19_pretrain.py` (D14 pretrain) | `load_pretrain_data` -> `ht.build_structured_sequence_attested` | decomposed per-sign line_index, tuples correctly unpacked (`t for t, st in toks if st != RESTORED`) | **CLEAN** | 0.12% (500-fragment sample) |
| `scripts/20_biencoder.py` (D15 train) | `load_encoded_pool`/training loader -> `ht.build_structured_sequence_attested`; synthetic pairs -> `render_tokens()` | same decomposed path as D14; synthetic path unpacks tuples correctly (`flat.extend(t for t, st in toks)`) | **CLEAN** | 0.12% (shares D14's path); 0.0% (synthetic, 1-pair spot check) |
| `scripts/24_p4b_diagnostics.py` — **B1** (dense_mean_pool/dense_line_max retrieval baselines, `p4_out/p4b_b1.json`) | `load_encoded_pool` (imported directly from `20_biencoder.py`'s module namespace, line 44) -> same `build_structured_sequence_attested` path | reuses D15's already-clean encoding, no local re-implementation | **CLEAN** | 0.12% (identical code path to D15) |
| `scripts/24_p4b_diagnostics.py` — **B2** (complementarity/fusion) | reuses B1's `dense_fd_line_scores`/`bm25_fd_scores_dense`, no new embedding | N/A, no re-encoding | **CLEAN** | N/A (consumes B1's clean scores only) |
| `scripts/24_p4b_diagnostics.py` — **B5** (bi-encoder-similarity-vs-lexical-overlap correlation, REAL-pair half only) | local `embed_token_lists()` fed `json.loads(frags_lookup.loc[q,"sign_attested"])` directly | `sign_attested` (eval_harness's word/compound-level sign rendering, e.g. `"LUGAL-uš"`, `"NINDA.GUR₄.RA"`, `"Ú-UL"`) fed to a vocab built from `hittite_tokenizer`'s DECOMPOSED per-sign scheme — a granularity mismatch, not the tuple bug | **BROKEN** (third, distinct mechanism — see below) | 13.90% (500-fragment sample); 10.2% on one spot-checked fragment |
| `scripts/24_p4b_diagnostics.py` — **B5** (synthetic-pair half, same analysis) | `embed_token_lists()` fed `p["member_a_tokens"]`/`member_b_tokens"` (from `fracture_engine.render_tokens()`) | tuples already unpacked by `render_tokens()` before this point | **CLEAN** | 0.0% (1-pair spot check) |
| `scripts/27_seam_scorer.py` (D17) | local `flatten_lines(lines, tok)` (unused `tok` param) on `get_fragment_tokens()` output | `(token, damage_state)` tuples pushed into the flat sequence unextracted | **BROKEN** (E2) | 82.6% (90-window sample, `reports/p5c_report.md`) |
| `scripts/27b_seam_agreement.py` (D17 addendum) | local `flatten_lines(lines)`, identical pattern | same as above | **BROKEN** (E2) | same mechanism, same rate class |
| `scripts/28_edge_continuation.py` (D18) | local `flatten_lines(lines)`, identical pattern | same as above | **BROKEN** (E2) | same mechanism, same rate class |
| `scripts/29_cascade.py` (D19) — real-join pairs + hard negatives | local `flatten_lines(lines)` on `get_fragment_tokens()` output | same as above | **BROKEN** (E2) | same mechanism (912 real-join + 3,066 hard-neg rows) |
| `scripts/29_cascade.py` (D19) — synthetic pairs | same local `flatten_lines(lines)`, but fed `tokens_to_lines()`-reshaped `render_tokens()` output (already plain strings) | no tuples ever reach `flatten_lines` here | **CLEAN** | 600 rows unaffected |
| `scripts/29b_cascade_refit.py` (this session's A1 BM25 refit) | identical `flatten_lines`, inherited verbatim from `29_cascade.py` | same as above | **BROKEN** (E2), real/hard-neg rows; CLEAN, synthetic rows | same split as 29_cascade.py |
| `scripts/13_bm25.py` / `eval_harness.bm25_score_matrix` (all BM25 features, incl. this session's A1 refit) | `sign_attested` fed to a FRESH, per-call `CountVectorizer` (BM25's own vocabulary, not the neural tokenizer) | BM25 builds its own vocabulary from whatever tokens it is given — word/compound-granularity tokens are perfectly valid BM25 terms | **N/A / clean by design** | not applicable (no shared vocab, no UNK concept for BM25) |
| `scripts/25_p5_stratify.py` | loads `Tokenizer`/`HittiteEncoder` for model instantiation only | no `.encode()` call on fragment content found | **N/A** | — |
| `scripts/17_tokenizer.py`, `21_pretrain_report.py`, `22_biencoder_report.py` | vocab construction / metrics reporting only | no fragment-content encoding | **N/A** | — |
| `demo/` (all files) | — | no `tok.encode`/`flatten_lines`/`build_structured_sequence` call sites found (`grep -rl` empty) | **N/A** | — |

## Priority verdict (Branch R evidentiary base)

**D15 training featurization: CLEAN. P4B's B1/B2 (the named evidentiary
base for Branch R's BM25-over-dense retrieval decision): CLEAN.** Both
reuse `20_biencoder.py`'s `load_encoded_pool`/`build_structured_sequence_attested`
path, execution-verified at 0.12% UNK on a 500-fragment sample —
consistent with the corpus-wide ~0.16% OOV baseline. **No STOP
triggered per H2's named condition.** Branch R's retrieval-scale
conclusion (BM25 beats dense retrieval at full_distractor scale) does
NOT need re-examination.

**A third bug, distinct from E2, found and scoped during this audit:**
P4B's **B5** real-pair correlation sub-analysis (`embed_token_lists`
fed `sign_attested` directly) mixes two token-granularity schemes —
`sign_attested` (eval_harness's word/compound-level rendering, valid
for BM25's own freshly-fit vocabulary) fed through a neural tokenizer
whose vocabulary was built from `hittite_tokenizer`'s DECOMPOSED
per-sign scheme. Measured UNK rate 13.90% (500-fragment sample, ~87x
the 0.16% baseline, ~2.8x the 5% contract threshold) — real degradation,
not noise. This is NOT E2's tuple-flattening mechanism (no tuples
involved here; `sign_attested` is already a flat list of strings) —
it is a separate scheme mismatch, confined to B5's REAL-pair half
(the synthetic-pair half of the same B5 analysis, via `render_tokens()`,
is clean). **This degrades but does not invalidate** the specific
`p5_report.md` citation of B5 as corroborating evidence ("the exact
same failure mode P4B's B5 diagnosed for the bi-encoder") — B5's
~0.56 real-pair correlation number should be treated as provisional
pending a rerun through the correct (`build_structured_sequence_attested`)
path. This is out of scope for P5C_AMENDMENT_2.md's H1/H5 (which
target the D17/D18/D19 pipeline specifically), so it is not fixed here
— flagged for a future decision, not silently absorbed or silently
left uncaveated.

## Bug-account confirmation: TRAIN positive seam_scores, synthetic vs
real-join

Split by construction path (`p4_out/p5_train_features_v2.json`, X
column 2 = `seam_score`; positions 0:912 = real-join positives
(BROKEN path, E2), 912:1512 = synthetic positives (CLEAN path via
`render_tokens`), 1512:4578 = hard negatives (BROKEN path)):

| population | n | mean | std | median | min | max |
|---|---|---|---|---|---|---|
| real-join positives (BROKEN) | 912 | 0.8729 | 0.0277 | 0.8818 | 0.7204 | 0.9156 |
| synthetic positives (CLEAN) | 600 | 0.4119 | 0.1709 | 0.3858 | 0.0460 | 0.8536 |
| hard negatives (BROKEN) | 3,066 | 0.8759 | 0.0238 | 0.8831 | 0.7488 | 0.9168 |

**Histogram (10 bins, [0,1]):**

```
                0.0-0.1 0.1-0.2 0.2-0.3 0.3-0.4 0.4-0.5 0.5-0.6 0.6-0.7 0.7-0.8 0.8-0.9 0.9-1.0
real-join (+)        0       0       0       0       0       0       0      17     829      66
synthetic (+)         4      51     131     139      91      85      59      32       8       0
hard-neg (-)          0       0       0       0       0       0       0      21    2793     252
```

**Signature: PRESENT, exactly as predicted.** Real-join positives
(broken path) cluster tightly at 0.87-0.88, statistically
indistinguishable in location/spread from hard negatives (broken path,
also 0.87-0.88) — both populations collapse to the same narrow
structural attractor once content is stripped to `<UNK>`. Synthetic
positives (clean path) are widely dispersed (0.05-0.85, std 6x wider).
This is not merely consistent with the predicted bimodal story — it
exactly reconstructs `p5_report.md` §5's reported combined
positive-pair statistic: mixing the two populations at their true
weights (912 real-join + 600 synthetic = 1512) gives
mean = 0.603×0.8729 + 0.397×0.4119 = **0.6900** and
std = sqrt(0.603×0.0277² + 0.397×0.1709² + 0.603×0.397×(0.8729−0.4119)²)
= **0.2508** — matching the report's stated 0.690/0.251 to 3-4
decimals. §5's "positive-pair mean (±std)" was arithmetically real but
was never a coherent single population; it was an unweighted average
of a content-blind cluster and a content-aware distribution, and its
inflated spread was the mixture's own separation, not within-class
variance.

## Conclusion

No STOP triggered. Proceeding to H1 (canonicalize the encoding path),
H3 (contracts), H4 (tracers), H5 (sighted re-score) per
P5C_AMENDMENT_2.md's sequencing. The B5 scheme-mismatch finding is
carried forward as an open, scoped, disclosed issue — not fixed under
this amendment's authorization, not silently ignored.
