# Sequence Context Helps Hittite Textual Retrieval, but Not Yet Physical Join Inference

**Provisional mentor-review draft — 2026-08-04.** Development results only;
protected test unopened. The blinded qualitative review was performed by an AI
surrogate and is not specialist validation. Citation formatting and venue
length remain to be completed.

## Abstract

We study evidence-bounded retrieval for fragmentary Hittite cuneiform texts in
TLHdig Beta 0.2.0. The larger goal is expert decision support for missing
textual and structural information, with uncertainty and abstention, rather
than automatic reconstruction. We first isolate a classical sequence-context
channel: BM25 is combined with separately weighted unigram and line-bounded
sign-bigram TF-IDF features, with weights selected by fold and applied only to
held-out development queries. On composition assignment, the line-bounded
bigram channel contributes +0.0940 recall@1 over BM25 plus unigram TF-IDF under
a word-aware Hittite scope. On fragment retrieval it improves all three
pre-registered benchmark cells: editor-encoded joins +0.1111 (95% cluster CI
[+0.0602, +0.1768]), pooled +0.0875 [+0.0591, +0.1230], and a same-CTH
non-join proxy +0.0627 [+0.0378, +0.1076], all significant after
Holm–Bonferroni correction. The join result does not survive its scientifically
important qualification. For joins with no editor-aligned shared lines, the
increment is +0.0294 [−0.0645, +0.1481]; removing aligned lines from Tier C
pairs collapses absolute recall@1 from approximately 0.38 to 0.00–0.04. In a
pre-registered blinded review of 20 gained and lost cases, an AI
transliteration-evidence surrogate usually preferred the expanded candidate in
gained cases, but judged the encoded evidence insufficient for physical-join
adjudication in all eight join cases. One lost join case favored a strong
textual match that was not the editor-encoded physical partner, illustrating
the central distinction between textual affinity and physical joining. We
conclude that local sign sequence is a strong, transparent retrieval signal,
but current evidence supports composition/textual-affinity assistance rather
than physical join inference or duplicate discovery.

## 1. Introduction

Fragmentary cuneiform scholarship is a missing-information problem. A broken
tablet may preserve discontinuous sign sequences, partial lines, document
structure, and relationships to other witnesses, while leaving the target
reading underdetermined. A useful computational system should therefore offer
ranked, evidence-supported possibilities, identify contradiction, preserve an
`other / unsupported` option, and abstain when the encoded record does not
support a defensible answer.

This project asks what textual or structural information is recoverable from
fragmentary Hittite records under explicitly named evidence policies. It uses
composition assignment and pairwise fragment retrieval as evaluation settings,
not as substitutes for the upstream task of reconstruction. The intended user
is a trained Hittite specialist.

The present study began as a control for pretrained encoders. Frozen CANINE
appeared to add value to BM25 on Task A, but a classical character n-gram
control added more, and sign bigrams recovered most of that improvement. That
sequence of controls changed the scientific question: not whether a pretrained
model “understands Hittite,” but what ordinary local sequence context adds once
unigram evidence, rendering boundaries, language scope, and fitting are
separated.

Our contributions are:

1. an attributable factorial decomposition of unigram scoring, separately
   weighted sign-bigram context, line boundaries, and language scope;
2. a cross-fitted evaluation on composition and relation retrieval with
   relation-appropriate clustering and a pre-registered multiple-testing
   family;
3. a negative result showing that apparent join performance is concentrated
   where editor-aligned text is already shared;
4. a blinded qualitative audit that separates textual affinity from physical
   join evidence; and
5. a correction to benchmark semantics: the historical “duplicates” cell is
   a same-CTH non-join proxy, not annotated duplicate/parallel truth.

## 2. Corpus and evidence policy

We use TLHdig Beta 0.2.0 (Müller, Prechel, Rieken, and Schwemer, 2025), pinned
by archive checksum. The corpus contains AOxml/HPM records with transliterated
lines, structural damage markup, language layers, catalog organization, and
editorial join notation. We exclude macOS archive artifacts and log XML parse
failures rather than silently dropping them.

The evaluated text is epigraphically attested transliteration. Editorial
restorations are scholarly hypotheses and are not treated as test truth. The
`lb@cu` field is excluded because it silently renders editor-restored material
as glyphs. Morphological analyses, editor identity, and model-generated content
are not features in this study.

We report the active evidence policy rather than calling the input
“artifact-only.” Transliteration is editorially mediated. The main analyses use
the word-aware `HITTITE_ONLY` scope, which defines an auditable Hittite
estimand but is not an accuracy intervention. It reduces absolute Task A
recall@1 by 0.0131 relative to the boundary-respecting unrestricted rendering,
and it removes 2,832 Task B positive relations, of which 2,825 belong to the
same-CTH proxy. Roughly half of the duplicate-cell loss is caused by missing
coverage in the project's language dataset rather than an affirmative
non-Hittite classification.

## 3. Tasks and truth sets

### 3.1 Composition assignment

Task A ranks real, non-bin CTH compositions for a fragment. Catch-all catalog
bins are excluded from labels and evaluation because their members are not
known negatives; they remain a discovery pool for later expert review.

### 3.2 Fragment retrieval

Task B ranks fragments under three operational cells:

- **joins:** editor-encoded physical partners derived from authoritative join
  notation;
- **same-CTH affinity:** non-join fragment pairs assigned to the same real CTH
  composition; and
- **pooled:** the union of the two.

Earlier project documents call the second cell “duplicates.” That name is too
strong. The implementation constructs every same-CTH non-join pair, without a
relation-specific duplicate or parallel annotation. We retain historical table
comparability but use the operational name here. No result from this cell alone
licenses a duplicate-discovery claim.

The joins and same-CTH cells use different dependence structures. Join
intervals cluster by connected physical join component; same-CTH and pooled
intervals cluster by composition. Joined fragments and composition witnesses
remain on one split side.

## 4. Methods

### 4.1 Classical retrieval channels

The reference combines BM25 with unigram TF-IDF over sign tokens. The expanded
system adds a line-bounded, bigram-only TF-IDF matrix with its own fitted
weight. Separate weighting matters: concatenating unigrams and bigrams into
one L2-normalized vector caused unigram mass to dominate and made the sequence
channel appear nearly useless.

Line boundaries are preserved. This prevents feature construction from
bridging lines—and, after scope filtering, from bridging lines that were never
adjacent. Forbidding such cross-line bigrams contributes +0.0287 recall@1 to
the Task A conditional increment.

### 4.2 Cross-fitting and inference

Weights are fitted separately inside each fold on the pooled Task B objective,
then applied only to that fold's held-out queries. Held-out predictions are
concatenated before deltas, intervals, p-values, and strata are calculated. One
weight pair serves every relation cell and stratum within a fold. A modal
weight configuration is retained only as a deployment candidate and carries no
development-performance claim.

Cluster bootstrap intervals and randomization tests use physical join
components for joins and compositions for same-CTH/pooled retrieval. The
primary family contains the three `HITTITE_ONLY` cells and is controlled by
Holm–Bonferroni at family-wise alpha 0.05.

### 4.3 Aligned-text stress tests

We stratify joins by the number of editor-aligned shared lines. Tier C is also
evaluated as paired instances under full and overlap-exclusive renderings,
holding the candidate universe fixed. This asks whether a retrieval system can
find a specific partner after the editor-aligned text that directly identifies
the relationship is removed.

### 4.4 Blinded qualitative audit

Before reveal, we sampled 20 development cases: six gained and six lost
same-CTH queries, five gained joins, and all three lost joins. An AI surrogate
saw only attested signs grouped by line, with candidate identity randomized.
It recorded candidate preference, textual support, formulaicity, contradictory
evidence, evidence independence, physical sufficiency, and specialist priority.
The annotations were committed before method and benchmark labels were opened.
This is protocol development and error analysis, not expert validation.

## 5. Results

### 5.1 Task A factor isolation

| change | conditional increment over matching BM25 + unigram reference |
|---|---:|
| merged unigram+bigram parameterization, legacy flat rendering | +0.0026 |
| separately weighted bigram-only channel | +0.0431 |
| line boundaries respected | +0.0718 |
| word-aware `HITTITE_ONLY` scope | +0.0940 |

The final row is not an accuracy gain caused by language filtering. Under the
boundary rendering, the reference/final systems score 0.4608/0.5326; under
`HITTITE_ONLY`, they score 0.4256/0.5196. The increment grows because the
reference falls faster.

A within-sign character-transliteration proxy receives weight zero in every
fold under the legacy and boundary renderings. Across-sign character n-grams
do help, but less than sign bigrams. This supports a sequence-context account,
not a claim about partial physical glyph evidence, which TLHdig does not encode.

### 5.2 Cross-fitted Task B primary family

| cell | n | clusters | recall@1 reference → expanded | delta | 95% cluster CI | p | Holm decision |
|---|---:|---:|---:|---:|---:|---:|:---:|
| joins | 171 | 54 | 0.5439 → 0.6550 | **+0.1111** | [+0.0602, +0.1768] | 0.0010 | reject |
| pooled | 766 | 35 | 0.5013 → 0.5888 | **+0.0875** | [+0.0591, +0.1230] | 0.0010 | reject |
| same-CTH proxy | 766 | 35 | 0.3799 → 0.4426 | **+0.0627** | [+0.0378, +0.1076] | 0.0070 | reject |

The positive average effect is real for these operational benchmarks. Its
scientific meaning differs by cell.

### 5.3 The physical-join qualification

| editor-aligned shared lines | n | clusters | delta | 95% cluster CI |
|---|---:|---:|---:|---:|
| 0 | 34 | 18 | **+0.0294** | **[−0.0645, +0.1481]** |
| 1–2 | 43 | 19 | +0.1163 | [+0.0357, +0.2286] |
| 3–9 | 69 | 30 | +0.1304 | [+0.0541, +0.2154] |
| 10+ | 25 | 15 | +0.1600 | [+0.0385, +0.3203] |

Shared-line count is confounded with join tier, length, and other pair
properties, so this is not a dose-response result. It is nonetheless the
load-bearing qualification: where no aligned text is shared, there is no
evidence of benefit.

On paired Tier C instances, full-rendering recall@1 changes from 0.3039 to
0.3824. Under overlap-exclusive rendering it changes from 0.0392 to 0.0000;
the single-partner sensitivity is 0.0000 for both arms. The incremental bigram
effect within Tier C is unresolved on 23 clusters. The dominant result is the
collapse in absolute retrieval after aligned text is removed.

### 5.4 Blinded case review

| stratum | expanded preferred | unigram preferred | both | neither |
|---|---:|---:|---:|---:|
| same-CTH gained | 5 | 0 | 1 | 0 |
| same-CTH lost | 0 | 4 | 0 | 2 |
| join gained | 4 | 0 | 1 | 0 |
| join lost | 1 | 2 | 0 | 0 |

The expanded candidate was directly preferred in 9/11 gained cases and was
one of two plausible candidates in the remaining 2. Its support in gained
cases was rated strong in 7 and moderate in 4. These balanced counts are not a
performance estimate.

All eight join cases were judged textually non-adjudicable as physical joins.
In `SR020`, the expanded system's non-join candidate looked more textually
compelling than the editor-encoded partner. This is the expected failure mode
of using a textual-affinity channel for a physical relation: it can retrieve a
better textual parallel and still answer the join question incorrectly.

## 6. Discussion

### 6.1 What is established

Local sign sequence is a consequential and transparent retrieval signal. It
adds value beyond BM25 and unigram TF-IDF when parameterized separately and
kept within line boundaries. The effect transfers from composition assignment
to the operational Task B benchmarks under cross-fitting. Task A-selected
weights also retain a positive within-arm Task B benefit without retuning,
although equivalence to Task-B-fitted weights was not established.

### 6.2 What is not established

The experiments do not demonstrate physical join inference on the intended
hard case. They do not validate duplicate discovery, because the duplicate
cell lacks duplicate-specific labels. They do not test physical partial-glyph
evidence, clay geometry, paleography, or restoration quality. They do not show
that a neural architecture is unnecessary for the upstream missing-span task.
Finally, non-significance in any subgroup is not equivalence.

### 6.3 Consequences for system design

The immediate prototype should present sign-bigram retrieval as a
textual-affinity assistance channel. Explanations should show distinct matched
runs, their line locations, corpus frequency, formulaicity, candidate-length
exposure, and contradictory evidence. Same-CTH affinity, passage parallelism,
duplicate witness, and physical join must be separate hypotheses rather than a
single combined score.

Physical-join output should abstain unless an independent structural or
physical channel supports a placement. The planned fragment-as-matrix model
should be evaluated on unknown-gap, multi-row consistency without assuming
seam contiguity; current textual retrieval cannot stand in for that model.

## 7. Limitations and next work

1. A trained specialist must repeat the blinded review. The AI surrogate
   provides protocol rehearsal and case prioritization only.
2. Same-CTH positives must be renamed throughout the paper and, for a true
   duplicate/parallel claim, replaced or supplemented with expert-validated
   relation labels.
3. Formula-aware diagnostics should measure how often each matched n-gram and
   line pattern occurs across the declared corpus universe.
4. The Gate-2 language-coverage deficit should be repaired and re-audited
   before language-scope comparisons are treated as stable product tradeoffs.
5. One final configuration and analysis plan must be frozen before the
   one-shot protected-test run. Nothing in this draft authorizes opening it.
6. The paper should lead with candidate-set utility, calibration, selective
   risk, and abstention once the upstream restoration interface is evaluated;
   top-1 retrieval is a benchmark diagnostic, not the product contract.

## 8. Conclusion

The strongest result is also the boundary of the result. Sign bigrams recover
substantial textual sequence information with a simple classical model. That
information improves composition and fragment-affinity retrieval. It does not,
without independent evidence, identify a fracture seam or establish that two
witnesses are duplicates. Treating those distinctions as first-class is not a
presentation caveat; it is the central scientific requirement for an
evidence-bounded reconstruction system.

## References to verify and format

- Müller, Prechel, Rieken, and Schwemer. 2025. TLHdig Beta 0.2.0. Zenodo.
  https://doi.org/10.5281/zenodo.15459134
- Tyndall. 2012. Composition classification of Hittite fragments. ACL
  Anthology P12-2048.
- Yavasan and Gordin. 2025. “From Clay to Code.” Ancient Language Processing
  workshop. Full bibliographic details to verify before circulation beyond the
  mentor draft.

