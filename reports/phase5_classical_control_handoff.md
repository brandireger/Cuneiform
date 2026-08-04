# Phase 5 classical-control line — handoff and request for second opinion

**Date: 2026-08-04. Branch merged to `master` at `a293cd4` + follow-ups.**
**Everything here is `[PROBE — not for citation]`: dev split only, dev-only
candidate index, test never loaded, nothing trained, nothing deployed.**

This document is written to serve two readers: a **fresh session** picking up
the work, and a **reviewer giving a second opinion**. Section 6 is addressed
to the reviewer specifically and names the things I most want attacked.

---

## 1. What was asked, and the one-line answer

The session began with an open brief: *continue refining the model* (no
expert available for the workbench, so the specialist session is blocked).

**One-line answer: the two pretrained-model rungs the ladder still owed are
answered negatively, and a classical n-gram context feature — which the repo
has had unused since P3 — is worth ~+0.10 Task A recall@1 on dev, roughly
double what the best pretrained candidate offered.**

## 2. The chain of results, in order

Each step was pre-registered in a committed protocol *before* its run. Commit
hashes are given so the ordering is checkable.

| # | experiment | protocol | verdict |
|---|---|---|---|
| 1 | BM25 + frozen CANINE combiner (Task A) | `50b6455` | REALIZABLE, +0.0462 |
| 2 | Same combiner on Task B | `5b67048` | does **not** transfer |
| 3 | Contamination via sign relabeling | `786db09` | MEMORISATION_REJECTED |
| 4 | Classical char n-gram control | `2580d85` | CANINE_REDUNDANT |
| 5 | Sign-bigram control | `4b74171` | CHARACTER GRANULARITY NOT THE POINT |

### 2.1 The combiner works on Task A (+0.0462)

The withdrawn-rung screen had left an **oracle** bound: a perfect per-query
selector combining BM25 with frozen CANINE would reach 0.7214 against BM25's
0.6312. An oracle is not a result, so I fit a real combiner —
`z(bm25) + α·z(cosine)`, α fit per composition-level fold.

Held-out recall@1 **0.6775 vs 0.6312, +0.0462, 95% CI [+0.0254, +0.0682]**;
51.2% of the oracle recovered; positive in all five folds; α = 0.5 in every
fold. An identity control confirmed α = 0 reproduces BM25's 865 per-query
records exactly, so the combiner family provably contains the baseline.

Qualifications that travel with it: **32 queries regress** against 72 gained;
unfitted equal-weight rank fusion (RRF) is **7–8 points worse than BM25
alone**, so the candidate works only as a down-weighted tie-breaker.

### 2.2 It does not transfer to Task B

Full three-way matrix, as the standing rule requires:

| cell | n | Δ recall@1 | 95% CI |
|---|---|---|---|
| joins | 182 | +0.0165 | [−0.0165, +0.0495] — includes 0 |
| duplicates | 865 | +0.0197 | [−0.0023, +0.0416] — includes 0 |
| pooled | 865 | +0.0266 | [+0.0058, +0.0486] |

**Neither individual cell is significant.** The only significant cell is
pooled — exactly the cell the three-way rule exists to stop us reporting
alone, since its positive set is the union of the other two and its own
recall@10 does not exclude zero either.

### 2.3 It is not contamination — and that is the interesting part

TLHdig is openly licensed and on Zenodo; CANINE saw multilingual Wikipedia.
CommonCrawl cannot be enumerated locally, so the test is behavioural: apply a
**bijective, character-length-preserving permutation** to the 1,339-sign
vocabulary and re-render. Every overlap and co-occurrence pattern is
preserved; memorised Hittite surface content is destroyed.

**BM25 must be exactly invariant** under a consistent bijection — its
statistics depend only on multiset structure. That is a correctness proof on
the permutation itself, asserted in code, and it passed on all five seeds.

Result: CANINE **retention 1.016** (mean Δ +0.0469, CI [+0.0266, +0.0687]),
every individual permutation clearing zero. **MEMORISATION_REJECTED.**

The rule was pre-registered as **one-sided on purpose**: survival rejects
memorisation cleanly, but a collapse would have been ambiguous between
contamination, legitimate transfer, and sensitivity to natural-language
character statistics. We got the clean branch.

**The inference that mattered**: the relabeled corpus is not Hittite, and the
gain was unaffected. So whatever CANINE contributes, **it is not knowledge of
Hittite**. That is what motivated everything after.

### 2.4 A classical model does it better, and CANINE adds nothing

If the signal is not linguistic, a classical model should capture it.

| Task A, held-out recall@1 | | Δ vs BM25 | +gained / −lost |
|---|---|---|---|
| BM25 alone | 0.6312 | — | — |
| BM25 + frozen CANINE | 0.6775 | +0.0462 | +72 / −32 |
| **BM25 + char n-gram (4,6)** | **0.7491** | **+0.1179** | +125 / −23 |

**CANINE stacked on top adds nothing: I = −0.0046, CI [−0.0162, +0.0058]** —
nine gained, thirteen lost. Verdict **CANINE_REDUNDANT**.

On Task B the classical signal clears zero in **all three cells on both
metrics** (joins +0.1099, duplicates +0.0879, pooled +0.1098), where CANINE
reached significance in none.

### 2.5 …but it is n-gram context, not character granularity

This is the correction I ran on myself before handing over, because it is the
first thing a reviewer would ask.

`add_bigrams()` has been in `eval_harness` since P3 and **was never
measured** — P3 only reported `bm25_sign`, `bm25_lemma`, `tfidf_cosine_sign`.

| arm | held-out recall@1 | Δ vs BM25 |
|---|---|---|
| BM25 + **sign bigram** | 0.7329 | **+0.1017** |
| BM25 + char n-gram | 0.7491 | +0.1179 |

**Sign bigrams recover 86.3% of it.** Character granularity's increment is
**+0.0162, CI [−0.0012, +0.0324] — includes zero.**

Subtlety worth knowing: given both signals the fold fit set **α_bigram = 0 in
all five folds**, so this measured char *instead of* bigram, not char *on top
of* bigram. The honest statement is that they are **near-substitutes**.

`reports/phase5_char_ngram_control_results.md` has been corrected: its
measurements stand, its mechanistic conclusion did not.

## 3. What I believe, at what confidence

| claim | confidence | basis |
|---|---|---|
| The pretrained candidates are redundant for retrieval here | **high** | direct head-to-head, pre-registered, CI includes zero |
| An n-gram context feature is worth ~+0.10 Task A recall@1 on dev | **high** | two implementations agree, all folds positive |
| Whether that is bigrams or char n-grams | **undetermined** | +0.0162 apart, CI includes zero |
| The gain is not memorisation | **high** | retention 1.016, five seeds, BM25 invariance proof |
| The gain survives at full-corpus scale | **unknown** | never tested; see 6.1 |
| It transfers test-side | **unknown** | gated, one-shot, not run |

## 4. What this changes for the project

**The model ladder.** Rungs 4 and 6 have moved position three times:
withdrawn inductively → reinstated on measurement → answered against a proper
control. Only the third rests on a head-to-head. **Recommendation: do not
write either owed Gate-3 proposal on retrieval grounds.** They were not
dismissed; they were measured and lost.

**The paper.** There is a real, reportable finding here that costs no GPU:
*four pretrained models were screened frozen, the best was combined with
BM25 under pre-registration, its gain was shown not to be memorisation, and a
classical n-gram feature then beat it while the pretrained model added
nothing on top.* That is a stronger negative result than the original
amendment's inductive dismissal, and it is honestly obtained.

**The shipping system.** `P5_CLOSEOUT.md` records BM25-retrieve-deep as the
shipping stage. Adding an n-gram context feature is worth ~+0.10 on dev for
near-zero compute. **This has NOT been done and is not recommended without
three things**: Ixca's decision, test-side validation (one-shot, gated), and
the statistics-universe fix in 6.1.

## 5. State of the repository

- All work merged to `master`, pushed, `origin/master` at the follow-up
  commits. Stale branches deleted (all were fully merged; `--no-merged` was
  empty in both directions before deletion).
- 360 tests pass; ruff clean on `lib scripts tests` (the 62 remaining errors
  are all in the frozen `Archive/` snapshot and must not be rewritten);
  `p4d_stamp_stale_reports.py --check` exits 0.
- New scripts: `phase5_bm25_combiner.py`, `phase5_contamination_relabel.py`,
  `phase5_char_ngram_control.py`, `phase5_bigram_control.py`,
  `phase5_combiner_taskb.py` (`--signal canine|char`).
- `eval_harness.run_retrieval` gained `precomputed_scores`, mirroring
  `run_task_a`; both are tested to reproduce the BM25 path exactly when
  handed BM25's own matrix, and to fail closed on a misshapen matrix.
- Frozen-embedding caches are `.npz` and gitignored; JSON results and reports
  are tracked.

## 6. For the second opinion — what I want attacked

I am more interested in being wrong here than in being agreed with. In rough
order of how much they could damage the headline:

### 6.1 The statistics universe (my biggest self-doubt)

`AGENTS.md` requires corpus statistics to be fit over the declared universe
for the phase, "never over query-derived subsets." **Every arm in this line
fits its statistics on the 876 dev fragments** — BM25's IDF, the TF-IDF
vocabularies, all of it.

Both arms share the deviation, so I believe the *deltas* are fair. But I have
not ruled out that **TF-IDF over n-grams benefits differently from a small
fitting set than BM25 over unigrams does** — n-gram vocabularies are far
larger and sparser, and IDF estimated on 876 documents may be optimistic in a
way that will not survive a full-universe refit. If that is true, +0.10 is an
overestimate of unknown size. **Is this a real threat, and what is the
cheapest way to test it?**

### 6.2 Dev-only candidate index (876 fragments)

Task B duplicates read 0.5642 here against a published full-scale 0.3727 —
three orders of magnitude fewer distractors. An n-gram feature's advantage
could grow with more distractors (more chances to discriminate) or shrink
(more chances for spurious n-gram overlap). **I have no principled prediction
and would like one.**

### 6.3 Selection pressure inside the folds

α came from a 12-value grid and n-gram range from 4 options, both fit on fit
folds and applied held-out. But the **candidate index is shared across
folds** — only queries are partitioned. With one scalar plus one categorical
I judged the exposure small. **Is that judgement right, and is composition-
level query-only folding sufficient here?**

### 6.4 Is the joins result telling a story I want to hear?

Char n-grams gain most on **joins** (+0.1099, α = 2.0), and I offered a
philological reading: a seam is where signs are partially preserved, which
whole-token matching scores as a miss. It is a satisfying story and I do not
trust it. Sign bigrams — which cannot match a partial sign — recover 86% of
the Task A gain, so **context alone may explain it**. The separating
measurement (Task B joins, rerun with bigrams) has not been done. **Worth
doing, or is the story already dead?**

### 6.5 Did I retire CANINE against the right comparator?

I measured CANINE's increment over **char n-grams** and got zero. I did
**not** measure its increment over **sign bigrams**, which are slightly
weaker. Transitivity is suggestive, not proof. If the recommendation becomes
bigrams, that gap matters.

### 6.6 Process question

Five pre-registered protocols in one session, each committed before its run,
each with a two-clause rule. I think this was the right discipline and it
caught me twice (my ByT5/CANINE predictions were backwards; my
duplicates-over-joins expectation was falsified; my character-granularity
conclusion was overstated). **Is there a point at which this becomes
ceremony rather than rigour — and did I pass it?**

## 7. Suggested next steps, in priority order

1. **Statistics-universe refit** (6.1) — cheapest thing that could
   invalidate the headline; do it before anything else.
2. **Task B with sign bigrams** — closes 6.4 and 6.5 together, ~10 minutes.
3. **Decide bigrams vs char n-grams** and whether the feature enters the
   shipping recommendation at all (Ixca).
4. **Then** the specialist session, which remains the real paper blocker and
   is unaffected by any of this.
5. P6 test-side runs remain one-shot, gated, and untouched.

## 8. Related documents

- `reports/phase5_bm25_combiner_{protocol,results}.md`
- `reports/phase5_combiner_taskb_{protocol,results}.md`
- `reports/phase5_contamination_{protocol,results}.md`
- `reports/phase5_char_ngram_control_{protocol,results}.md` *(carries a
  correction banner)*
- `reports/phase5_bigram_control_{protocol,results}.md`
- `reports/phase5_ladder_screen_results.md`,
  `reports/phase5_model_ladder_amendment.md` *(both updated)*
- `PHASE5_SUCCESSOR_HANDOFF.md` item 8 *(current operational state)*
