# Phase 5 classical-control line — handoff and request for second opinion

> **CORRECTIVE REVIEW ADOPTED 2026-08-04.** Read
> `reports/phase5_classical_control_review.md` and
> `reports/phase5_unigram_tfidf_control_results.md` with this handoff. The
> measurements below remain historical facts, but three conclusions are
> superseded: CI-includes-zero is not equivalence; relabeling does not exclude
> every memorised component; and the approximately +0.10 bigram-arm gain is
> partly (+0.052) unigram TF-IDF scoring complementarity rather than context
> alone.

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

**Corrected one-line answer: in this closed-world dev setup, frozen CANINE has
no measured increment as large as +0.010 over the char arm, while a classical
lexical ensemble reaches about +0.10 Task A recall@1. A post-hoc decomposition
attributes +0.052 to unigram TF-IDF fusion and a further +0.050 to the
separately tuned sign-bigram arm. This is exploratory retrieval evidence, not
closure of pretrained adaptation or a deployment claim.**

## 2. The chain of results, in order

Each step was pre-registered in a committed protocol *before* its run. Commit
hashes are given so the ordering is checkable.

| # | experiment | protocol | verdict |
|---|---|---|---|
| 1 | BM25 + frozen CANINE combiner (Task A) | `50b6455` | REALIZABLE, +0.0462 |
| 2 | Same combiner on Task B | `5b67048` | individual strata inconclusive; pooled positive |
| 3 | Contamination via sign relabeling | `786db09` | historical verdict: MEMORISATION_REJECTED; corrected: correct passage sequence not necessary |
| 4 | Classical char n-gram control | `2580d85` | historical verdict: CANINE_REDUNDANT; corrected: no ≥+0.010 frozen increment in this setup |
| 5 | Sign-bigram control | `4b74171` | historical verdict: CHARACTER GRANULARITY NOT THE POINT; corrected: INCONCLUSIVE |
| 6 | Unigram TF-IDF decomposition | post-hoc review | +0.052 unigram ensemble; +0.050 further bigram-arm difference |

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

### 2.2 The individual Task B strata are inconclusive

Full three-way matrix, as the standing rule requires:

| cell | n | Δ recall@1 | 95% CI |
|---|---|---|---|
| joins | 182 | +0.0165 | [−0.0165, +0.0495] — includes 0 |
| duplicates | 865 | +0.0197 | [−0.0023, +0.0416] — includes 0 |
| pooled | 865 | +0.0266 | [+0.0058, +0.0486] |

Neither individual cell excludes zero, but both intervals permit practically
meaningful positive effects. The pooled any-relation cell is positive. It is
a distinct estimand and must be reported alongside, not substituted for, the
individual cells. These data do not support a categorical “does not
transfer” verdict.

### 2.3 Corrected: correct passage sequence is not necessary

TLHdig is openly licensed and on Zenodo; CANINE saw multilingual Wikipedia.
CommonCrawl cannot be enumerated locally, so the test is behavioural: apply a
**bijective, character-length-preserving permutation** to the 1,339-sign
vocabulary and re-render. Every overlap and co-occurrence pattern is
preserved; memorised Hittite surface content is destroyed.

**BM25 must be exactly invariant** under a consistent bijection — its
statistics depend only on multiset structure. That is a correctness proof on
the permutation itself, asserted in code, and it passed on all five seeds.

Result: CANINE **retention 1.016** (mean Δ +0.0469, CI [+0.0266, +0.0687]),
every individual permutation clearing zero. The historical preregistered
label was **MEMORISATION_REJECTED**. The corrected interpretation is narrower:
**correct Hittite passage sequence is not necessary for aggregate gain.**

The rule was pre-registered as **one-sided on purpose**: survival rejects
memorisation cleanly, but a collapse would have been ambiguous between
contamination, legitimate transfer, and sensitivity to natural-language
character statistics. We got the clean branch.

The replacements remain real Hittite transliteration strings, alpha is refit,
and aggregate retention does not show that the same queries retain their
gains. The test therefore does not exclude a memorised component in the
original run or prove that all surviving signal is non-linguistic. It did
legitimately motivate the classical control.

### 2.4 A classical model does better; no material frozen CANINE increment is measured

If the signal is not linguistic, a classical model should capture it.

| Task A, held-out recall@1 | | Δ vs BM25 | +gained / −lost |
|---|---|---|---|
| BM25 alone | 0.6312 | — | — |
| BM25 + frozen CANINE | 0.6775 | +0.0462 | +72 / −32 |
| **BM25 + char n-gram (4,6)** | **0.7491** | **+0.1179** | +125 / −23 |

CANINE stacked on top has **I = −0.0046, CI [−0.0162, +0.0058]** — nine
gained, thirteen lost. Its upper endpoint is below the declared +0.010 useful
margin, so the corrected statement is: **no material frozen CANINE increment
at +0.010 is measured in this setup**. “Adds nothing” and
“CANINE_REDUNDANT” are historical labels, not current general claims.

On Task B the classical signal clears zero in **all three cells on both
metrics** (joins +0.1099, duplicates +0.0879, pooled +0.1098), where CANINE
reached significance in none.

### 2.5 Corrected twice: context helps, but +0.10 is not all context

This is the correction I ran on myself before handing over, because it is the
first thing a reviewer would ask.

`add_bigrams()` has been in `eval_harness` since P3 and **was never
measured** — P3 only reported `bm25_sign`, `bm25_lemma`, `tfidf_cosine_sign`.

| arm | held-out recall@1 | Δ vs BM25 |
|---|---|---|
| BM25 + **sign bigram** | 0.7329 | **+0.1017** |
| BM25 + char n-gram | 0.7491 | +0.1179 |

Sign bigrams recover 86.3% of the char-arm gain. Character granularity's
increment is **+0.0162, CI [−0.0012, +0.0324]**. Because the interval permits
both zero and effects larger than +0.010, character-over-bigram is
**inconclusive**, not an equivalence result.

Subtlety worth knowing: given both signals the fold fit set **α_bigram = 0 in
all five folds**, so this measured char *instead of* bigram, not char *on top
of* bigram. The present sample does not resolve which representation is
better.

The reviewer-requested unigram control then found BM25 + unigram TF-IDF
+0.0520 and the separately tuned bigram arm a further +0.0497 over it. The
original +0.1017 therefore combines scoring-rule complementarity and sequence
context; it cannot all be attributed to n-grams.

`reports/phase5_char_ngram_control_results.md` has been corrected: its
measurements stand, its mechanistic conclusion did not.

## 3. What I believe, at what confidence

| claim | confidence | basis |
|---|---|---|
| Frozen CANINE lacks a ≥+0.010 increment over the char arm in this setup | **moderate** | CI upper +0.0058; cluster/full-universe confirmation still owed |
| The bigram arm is worth ~+0.10 Task A recall@1 in this dev setup | **moderate-high** | composition-cluster audit positive; no external confirmation |
| Sequence context's separately tuned contribution beyond unigram TF-IDF is ~+0.05 | **moderate** | post-hoc decomposition, composition-cluster CI positive |
| Whether bigrams or char n-grams are better | **undetermined** | +0.0162 CI permits zero and >+0.010 effects |
| Correct passage sequence is unnecessary for aggregate relabeled gain | **high** | retention 1.016 under five permutations |
| No memorised component contributed originally | **unsupported** | relabeling design cannot establish this |
| The gain survives at full-corpus scale | **unknown** | never tested; see 6.1 |
| It transfers test-side | **unknown** | gated, one-shot, not run |

## 4. What this changes for the project

**The model ladder.** The frozen mean-pooling retrieval probe is bounded, but
fine-tuned adaptation and non-retrieval tasks are not answered. The current
recommendation remains not to write a Gate-3 proposal before the specialist
session, as a priority decision rather than a general scientific closure.

**The paper.** There is a real, reportable finding here that costs no GPU:
*four pretrained models were screened frozen, the best was combined with
BM25 under preregistration, correct passage sequence was shown unnecessary
for the relabeled aggregate gain, and a classical lexical ensemble performed
better while no ≥+0.010 frozen CANINE increment was measured over the char
arm.* The claim remains dev-side and retrieval-specific.

**The shipping system.** `P5_CLOSEOUT.md` records BM25-retrieve-deep as the
shipping stage. Adding a unigram+bigram lexical arm is worth ~+0.10 on this
dev setup for near-zero compute; about half is unigram TF-IDF complementarity.
**This has NOT been done and is not recommended without
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

1. **Statistics-universe refit plus full labeled distractor index**; keep the
   unlabeled discovery pool distinct from scored negatives.
2. **Factorial unigram/bigram/character control** with composition-cluster
   inference, explicit language scope, and boundary-preserving rendering.
3. **Task B and join-tier stratification**, including direct/indirect,
   shared-line count, and tier-A/no-overlap cases.
4. **First specialist session**, still the real product and paper blocker.
5. Freeze one final configuration and plan before any one-shot P6 access.

## 8. Related documents

- `reports/phase5_classical_control_review.md` *(current corrective authority)*
- `reports/phase5_unigram_tfidf_control_{protocol,results}.md`
- `reports/phase5_bm25_combiner_{protocol,results}.md`
- `reports/phase5_combiner_taskb_{protocol,results}.md`
- `reports/phase5_contamination_{protocol,results}.md`
- `reports/phase5_char_ngram_control_{protocol,results}.md` *(carries a
  correction banner)*
- `reports/phase5_bigram_control_{protocol,results}.md`
- `reports/phase5_ladder_screen_results.md`,
  `reports/phase5_model_ladder_amendment.md` *(both updated)*
- `PHASE5_SUCCESSOR_HANDOFF.md` item 8 *(current operational state)*
