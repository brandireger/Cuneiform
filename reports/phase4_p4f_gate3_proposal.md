# P4-F Gate 3 training proposal — language-conditioned pretraining

**Status: RATIFIED 2026-08-02 (Ixca), as drafted, no changes requested.**
Drafted 2026-08-02 per `PHASE4_CHARTER.md` §Gate 3 ("Requires a named
hypothesis, config, time estimate, GPU budget, falsifier, checkpoint/output
paths, and confirmation that the new vocabulary and model dimensions cannot
overwrite the frozen D14 run") and `PHASE5_SUCCESSOR_HANDOFF.md` item 7.
Ratification authorizes exactly what §7 ("What ratification does and does
not authorize") states, no more: Stage 0 (the code change, no GPU) and
Stage 1 (the two named runs, at the named budget, against the named
falsifier). Stage 2 and everything past it remain separately gated.

**Execution status:** Stage 0 is implementable now (no GPU required) and is
the next work in this session. Stage 1 remains blocked on GPU access this
environment does not have — see the handoff for whoever picks this up with
one.

No GPU is available in the environment this was drafted in, so nothing here
has been executed. Every figure either comes from an existing frozen
artifact (cited) or is stated as an estimate (labeled as one).

## 1. What already exists, and what does not

The frozen baseline this proposal compares against:

| | |
|---|---|
| Checkpoint | `runs/pretrain_base/checkpoint.pt` (= **D14**, frozen, never to be touched) |
| Architecture | 6 layers, d_model=384, 6 heads, d_ff=1536, seq_len=512 — **12,817,991 params** |
| Training | 60,000 steps, TRAIN + discovery-pool ATTESTED sequences, dev for loss curves only, test never touched |
| Known metrics (dev) | boundary_auc(pooled) 0.7904; **in_doc AUC 0.7461** (the hard tier — "the curriculum's hard negatives are the number that matters," `Archive/reports/pretrain_report.md`); span-infill exact-match 0.413@len1 collapsing to ~0 by len6 |
| Language awareness | **none** — D14 saw mixed-language text with no signal telling it which language a token belonged to (`PHASE4_CHARTER.md` §1) |

**Checked directly, not assumed: language-conditioning does not exist in the
model code today.** `lib/hittite_model.py`'s `HittiteEncoder` and
`Archive/scripts/19_pretrain.py`'s data pipeline have no language-embedding
input, no per-token or per-span language field, nothing. This is not a
training-config knob to flip — it is unwritten code, and it is Stage 0
below, not Stage 1.

**Checked directly: the checkpoint path is already safely parameterized.**
`19_pretrain.py --tag <name>` writes to `runs/pretrain_<name>/checkpoint.pt`,
defaulting to `--tag base` (D14's own path). Every run this proposal names
uses an explicit, distinct `--tag`; none can collide with `runs/pretrain_base/`
unless someone manually passes `--tag base`, which is why §6 makes that
tag reserved and forbidden for any P4-F work.

## 2. The hypothesis, stated so it can be wrong

Phase 1's own closeout (`P5_CLOSEOUT.md`) already measured, on this exact
architecture and task, that BM25 beats the dense/boundary-head system
decisively at every scale, that the D14 boundary head "does not discriminate
true join partners from BM25-mined lexically-similar non-partners on real
content" (0.468 vs 0.480, heavily overlapping), and that tier-A joins are
"not solved, or approached, by anything built." A near-identical proposal to
this one — **D17b, a ≤12h conditional retrain** — was **suspended, not
executed**, because its own diagnostic precondition never produced a clear
signal that retraining was worth the GPU. This history is the reason this
proposal is staged rather than a blanket "retrain and compare six ways" ask.

**Hypothesis (Stage 1 only):** on the *same* multilingual training data,
adding an explicit language signal (a learned per-token language embedding,
added to input token embeddings before the encoder) measurably improves the
boundary head's discrimination on the hardest negative tier (`in_doc`)
relative to an otherwise-identical multilingual model trained *without* that
signal — because an unconditioned model must currently represent, e.g., a
Hittite and an Akkadian token with the same surface form identically, which
a language-conditioned model does not have to do.

**What this hypothesis is deliberately not claiming:** that conditioning
closes the gap to BM25, that it revives the tier-A joins problem (Phase 1
found the missing signal there is *lexical overlap itself absent by
construction* — not obviously a language-confusion problem at all), or that
any resulting checkpoint is ready for the demo, a paper claim, or promotion
past `[PROBE — not for citation]` (Gate 4 territory, untouched by this
proposal).

## 3. Falsifier — pre-registered before any run

The conditioned model (Stage 1, arm B below) must exceed the matched
unconditioned-multilingual model (Stage 1, arm A) by **at least +0.02
`in_doc` boundary AUC** on the same held-out dev batches, measured the same
way `Archive/reports/pretrain_report.md` §3 measured D14 (fresh pass,
n≈1920, `in_doc` tier specifically — not the pooled AUC, which the
architecture's own spec says is not the number that matters). The +0.02
threshold is not arbitrary: it matches the magnitude of the smallest
improvement this project has already treated as real and worth recording
elsewhere (`P5_CLOSEOUT.md`'s BM25 edge-window ceiling gain, "+0.022").

**If arm B does not clear arm A by this margin, or if arm B does not exceed
D14's own historical `in_doc` AUC (0.7461) at all:** the hypothesis is
REJECTED. Stage 2 (§7) is NOT authorized by this proposal in that case — a
new proposal, informed by why conditioning failed to help, would be needed
to pursue the remaining charter comparisons (Hittite-only retraining,
sampling ablation, line-vs-word granularity ablation). This mirrors exactly
how D17b was suspended rather than escalated on an inconclusive result.

## 4. Config

- **Model:** identical architecture to D14 (6 layers, d_model=384, 6 heads,
  d_ff=1536, seq_len=512), plus one addition for the conditioned arm: a
  learned language embedding (8 rows — the 7 canonical codes plus
  `<UNRESOLVED>`) summed into the token embedding at each position, sourced
  from the P4-D `effective_lang_canonical` field per token — the same
  governed field the real-gap pipeline already uses, not a second
  implementation of language resolution.
- **Objective:** identical to D14 — masked-span infilling (MLM-style) +
  boundary/edge-continuation head, same losses, same negative-tier
  curriculum (`in_doc` / `cross_genre` / `random`).
- **Steps:** 60,000, matching D14 exactly. A shorter run would make "does
  conditioning help" and "did this run just not train as long" impossible
  to tell apart.
- **Data scope:** TRAIN + discovery-pool ATTESTED sequences for gradient
  updates; DEV for loss curves and the falsifier metric only; TEST untouched
  in any capacity, enforced the same way every other script in this repo
  enforces it (`lib/contracts.assert_no_test`).
- **Seed:** a single fixed seed shared by both Stage 1 arms (proposed:
  `20260802`, this document's date), so a difference between arms reflects
  the conditioning variable and not seed variance. **Not** claiming one
  seed is sufficient evidence on its own — see §8, "what this proposal does
  not establish."

## 5. Sampling policy

**Stage 1 uses natural-frequency language sampling** — the corpus's own
composition (~89% Hittite, per the workbench export's own documented
figure), not rebalanced. The charter's arm 6 (natural vs. controlled
sampling) is a Stage 2 ablation, deliberately not run in Stage 1: mixing two
untested variables (conditioning AND sampling policy) in one comparison
would make a positive result uninterpretable — is it the conditioning, the
rebalancing, or both? Every run's sampling manifest is logged the same way
`AGENTS.md`'s engineering standards already require project-wide.

## 6. Time / GPU budget

**No GPU-hours figure for D14 is recorded anywhere in this repo** — stated
here rather than invented. What is on record: `wall_clock_budget_hours: 24`
per invocation is already a hard, enforced cap in `19_pretrain.py` (the
training loop checks it and stops cleanly, mid-checkpoint, rather than
requiring external monitoring), and D14 reached 60,000/60,000 steps, so
however many 24h sessions it took, it completed within that budget structure
without exceeding it unboundedly.

**Stage 0 (this proposal, if ratified, starts here): no GPU.**
Implementing the language-embedding addition to `HittiteEncoder` and wiring
the P4-D language field through the training data pipeline is ordinary code
work — reviewable, testable, and gated behind the project's normal test
suite before any Stage 1 run touches a GPU. Estimated: not a GPU cost line
item; scoped separately from this budget request.

**Stage 1: two runs, same architecture and step count as D14, budget-capped
at 24h/session each** (matching D14's own per-session cap, not a new,
untested number):

| tag | arm | conditioning | GPU |
|---|---|---|---|
| `multilingual_unconditioned_p4f` | A | off | ≤24h × however many sessions D14 itself needed to complete 60k steps |
| `multilingual_conditioned_p4f` | B | on | same |

Both run on the single-consumer-GPU budget this project has used throughout
(`AGENTS.md`: "corpus is small enough to pre-train on one GPU... if a design
exceeds it, redesign") — no cluster, no multi-GPU ask.

**Reserved tag, forbidden for this work:** `--tag base` (writes to D14's own
path). Any Stage 1 invocation using it is a process error, not a config
choice, and should halt immediately if it happens.

## 7. What ratification does and does not authorize

**Ratifying this proposal authorizes:** Stage 0 (the code change) and Stage
1 (the two named runs, at the named budget, against the named falsifier) —
nothing past that.

**Ratifying this proposal does NOT authorize:** Stage 2 (Hittite-only
retrain, sampling ablation, line-vs-word granularity ablation — charter
arms 2, 5, 6), any use of a language-conditioned checkpoint beyond
`[PROBE — not for citation]`, any P4-G downstream rerun of the real-gap or
witness pipelines against a new checkpoint, or protected-test access in any
form. Each of those remains a separate gate, per `PHASE4_CHARTER.md` §5 and
the standing "Protected-test access and GPU training remain unauthorized"
line this document does not change except for the two Stage 1 runs
specifically named above.

If Stage 1's falsifier is cleared, **Stage 2 requires a follow-up
proposal**, not an automatic continuation — this document commits to that
explicitly so a positive Stage 1 result cannot be read as blanket
authorization for the rest of the charter's comparison grid.

## 8. What this proposal does not establish, even if Stage 1's falsifier clears

- **A single seed per arm is not a robustness claim.** A real effect at
  this scale should be checked against seed variance before it is trusted
  for anything beyond "worth a Stage 2 proposal" — this is flagged as a
  known gap, not silently assumed away.
- **Beating an unconditioned sibling model is not beating BM25.** Every
  number Stage 1 produces stays `[PROBE — not for citation]` regardless of
  outcome (Gate 4), and Phase 1's own finding that BM25 beats this
  architecture family decisively is untouched by anything in this proposal.
- **The conditioned-versus-unconditioned tracer (below) checks plumbing,
  not science.** It cannot tell you conditioning helps; it can only catch
  the specific failure mode that already corrupted a full research phase
  once in this project (`P5_CLOSEOUT.md` §2.4, the E2 content-blind
  scoring bug: five scripts silently fed the model blank-page input for
  months before anyone noticed, because nothing checked that the input
  pipeline was actually wired).

## 9. The conditioned-vs-unconditioned tracer (required before either Stage 1 run starts)

A canary-scale check, in the tradition of `scripts/00_tracers.py`'s T1–T5
and `lib/contracts.py`'s C1–C10 — run before spending any GPU budget, not
after:

1. **The language-embedding table is not collapsed.** After model
   initialization (before training), the 8 language-embedding rows must be
   pairwise distinct (no two closer than some trivial epsilon by cosine
   distance) — catches a dead/no-op embedding layer at initialization,
   before a single training step is wasted on it.
2. **Conditioning measurably changes the forward pass.** On a small fixed
   canary batch, run the SAME input through the conditioned model with the
   language field populated and with it forced to a constant — the two
   output logit sets must differ. If they don't, the conditioning input is
   not reaching the model regardless of what the training loop reports.
3. **The two Stage 1 runs' manifests differ exactly where they should.**
   `language_scope`/config hash differ between arm A and arm B; every other
   config field (seed, steps, architecture dims, data scope) is identical.
   Catches an accidental confound (e.g., arm B silently also getting a
   different learning rate) that would make the falsifier's comparison
   invalid even if both runs "succeed" individually.

Each check is fast (no GPU epoch required — items 1–2 run on a freshly
initialized model and a canary batch; item 3 is a manifest diff) and must
pass before either Stage 1 run is started, not just before its result is
trusted.

## 10. Open question for whoever ratifies this

Item 3's canary batch and item 1's epsilon threshold are not yet chosen —
that is implementation detail properly settled while writing Stage 0's code
and tests, not something to pre-decide in a proposal document days before
anyone has the language-embedding layer in front of them to test against.
Flagged here so it is a visible open item, not a silent gap.
