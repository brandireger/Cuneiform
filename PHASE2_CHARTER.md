# PHASE2_CHARTER.md — Takšan Phase 2: characterize the data before modeling it

Ratified jointly (Ixca + architect session) 2026-07-22. This is a
CHARTER, not a spec. It states what changed in our beliefs, what
question replaces Phase 1's question, and a menu of cheap probes. It
deliberately does not pre-register success gates on exploratory work
(see SANDBOX_RULES.md for why).

## 1. The reframe

**Phase 1 asked:** can a model rank fragment pairs better than BM25?
It assumed the task was well-posed and the model was the variable.

**Phase 2 asks:** *what is actually recoverable from this corpus,
under what formulation, and what would it take?* The task
formulation, the data's information content, and the label quality
are now variables too.

**Center of gravity (ratified 2026-07-23):** Phase 2 is about
evidence-bounded prediction of missing textual and structural
information, not joins specifically. "Let the artifacts speak" means
predicting only from encoded evidence, naming assistance layers,
preserving alternatives, calibrating uncertainty, and abstaining when
the target is not identifiable. Joins remain one downstream stratum.

Three things forced this:

1. **The no-overlap signature is definitional, not incidental.** The
   fracture engine's calibration states that tier A/B joins have
   `n_shared_lines ≈ 0` — "that IS the no-overlap seam signature."
   We spent Phase 1 building lexical-similarity-adjacent methods for
   a class of pairs defined by the absence of shared text.
2. **Tier A collapses everywhere.** BM25 ceiling@200 = 0.519;
   sighted cascade recall@1 = recall@10 = 0.0 (n=27). The aggregate
   numbers (0.68/0.81) are carried by tier C (ceiling 0.984).
   "Join detection" has been two different problems wearing one name.
3. **Every learned component reduced to a noisier lexical signal, or
   worse.** Even with sight, the boundary head prefers
   lexically-similar impostors. Rather than fix the model again, ask
   whether the question posed to it was answerable.

## 2. Research questions for Phase 2

- **Q0 (recoverability).** Which kinds of missing information can be
  predicted from genuinely attested textual and encoded structural
  context, at what horizon, and with what calibrated uncertainty?
- **Q1 (validity).** Was the boundary head ever asked a well-posed
  question? Can it localize a seam it has been *handed*?
- **Q2 (information).** Is there recoverable signal for no-overlap
  joins in text alone — or does the signal live in materiality
  (paleography, fabric, edge morphology, ruling, curvature) that
  TLHdig does not encode?
- **Q3 (formulation).** Is pairwise ranking the wrong shape? Does
  generate-then-match, graph-constrained assembly, or
  witness-mediated bridging surface signal that pairwise scoring
  destroys?
- **Q4 (labels).** How reliable is the ground truth? Are editorial
  `+` joins uniformly certain, or is the hard set enriched for the
  shakiest editorial calls?
- **Q5 (scale).** Is 182 dev joins / 27 tier-A simply below the
  supervision floor for any learned method — and if so, what n would
  be required?

## 3. The probe menu

Each probe is cheap (hours, not phases), independently killable, and
answers something we cannot currently answer. **They may run in any
order and in parallel.** Ordering guidance only: P2-A and P2-D are
the highest information-per-hour and answer questions the others
depend on.

### P2-A — Seam localization on handed-over truth *(highest priority)*
**Question:** Q1. **Cost:** hours, zero GPU training.
Take known joins whose editorial `{€N}` alignment gives the true
line-level seam. Score the TRUE seam against WRONG offsets *within
the same true pair* using the frozen D14 head. If the head cannot
find the correct offset in a pair it has been told joins, the entire
retrieval-level evaluation was asking an unparseable question, and
every Phase 1 seam number is a statement about task mismatch rather
than model quality.
**Kill/carry:** if the head localizes well above chance, seam scoring
is viable and the failure is retrieval-level. If not, boundary-head
reranking is dead and P2-C/P2-E become the live paths.

**Opening feasibility result (2026-07-23):** the first Phase 2 probe
found that `{€N}` supplies row membership/alignment but not a
member-specific within-line fracture column. Shared rows are stored as
one fused parent line assigned to both members. Therefore P2-A as
worded does not currently have a true seam-column target; do not score
D14 against D17's row-skipping offset and call that seam localization.
See `reports/phase2_p2a_feasibility.md`. A row-alignment reformulation
or evidence for an unmaterialized per-member span would require a new
decision.

### P2-B — Materiality inventory *(what does the corpus NOT contain?)*
**Question:** Q2. **Cost:** hours, mostly reading + counting.
Audit what non-textual signal TLHdig encodes and what it doesn't:
edge states (have), line counts and ruling/parsep (have), column
structure (partial), physical dimensions, clay fabric, sign
paleography, hand identification, curvature, findspot (mostly not).
Cross-reference against what philologists actually use to propose
joins. Deliverable: a table of "signal a human uses" × "encoded in
TLHdig y/n" — which either identifies unused features sitting in the
data, or becomes the paper's specification of what the field should
digitize next.

**Opening inventory result (2026-07-23):** a filename-gated non-test
schema census (20,762 parsed XML files) and the governed non-test edge
universe (21,942 fragments) confirm that TLHdig carries useful symbolic
layout: line labels are nearly complete, side/column are present on
67.3%/51.1% of fragment lines, `parsep` occurs in 80.7% of safe XML
documents, and gaps/damage markup are widespread. Direct physical-edge
direction is sparse (0.5% of lines). The distributed archive contains
no image or 3D files and no schema fields for dimensions, thickness,
curvature, break contours, clay appearance/composition, wedge geometry,
paleography, or ancient scribal hand. See
`reports/phase2_p2b_materiality_inventory.md`.

### P2-C — Edge-prediction inversion *(generate, then match)*
**Question:** Q3. **Cost:** a day, inference only on frozen D14.
Instead of scoring O(n²) pairs, use span-infilling to *predict* the
signs continuing past each fragment's broken edge, then index those
predictions and retrieve fragment-starts against them. Uses D14 for
what it was actually trained to do. The measured horizon is brutal
(exact-match 0.413 at length 1, ~0 by 6), so the honest version of
this probe is: *does a 1–3 sign predicted continuation carry ANY
retrieval signal above chance?* A small positive answer reframes the
architecture; a null answer closes a plausible avenue cheaply.

### P2-D — Ground-truth reliability audit *(highest priority)*
**Question:** Q4. **Cost:** hours, plus optional expert consultation.
Sample the 182 dev joins (and the 46-member hard set) and classify
each by evidential basis where the corpus records it: physical refit
vs inferred-from-content vs proposed. Test whether the hard set is
enriched for weaker editorial claims. If a meaningful share of "gold"
is itself inference, then Phase 1 partly penalized models for
disagreeing with fallible labels — which changes what the negative
results mean and belongs in the paper either way.

**Opening audit result (2026-07-23):** the governed relation artifacts
support three bases, not a certainty scale: 104/182 canonical dev pairs
carry direct `+` notation, 17 carry indirect `(+)` notation, 60 were
expanded from shared-line co-attribution, and 1 is unsupported/unknown.
No `proposed` or certainty field is materialized. The frozen BM25 hard
set is not enriched for weaker bases at its query unit (17/46 versus
76/136 non-hard), while a parent-level robustness view is inconclusive
and changes direction. Therefore keep relation bases separate, but do
not attribute hard-set difficulty to label weakness from this probe.
See `reports/phase2_p2d_reliability.md`.

### P2-E — Witness-bridge supervision *(the novel idea)*
**Question:** Q0, Q3, Q5. **Cost:** a day or two.
Duplicates are plentiful and near-solved; multiple witnesses of one
composition give *parallel text*. First measure how often an
independently attested witness provides bounded evidence for missing
context around a fragment. Then, only where coverage exists, test
witness-mediated reconstruction (A's observed text → sibling witness
→ candidate missing context → B or an intentionally masked attested
span). A parallel is evidence for possible context, not proof of
identical lost wording. Join recovery is one downstream analysis, not
the probe's definition. This uses the corpus's duplicate abundance to
study missing-information recoverability without inventing physical
geometry.

**Opening recoverability result (2026-07-23):** the dev-only,
`catalog_assisted` census confirms that witness coverage is real but sharply
bounded. With two-sign anchors around one intentionally hidden attested sign,
21,069/85,587 structurally eligible spans (24.62%) had any independent
witness-supported middle, 16,597 (19.39%) included the held-out sign, and the
system abstained on 75.38%. The composition-macro support mean/median was
lower (13.68%/10.92%), showing that large compositions inflate the
span-micro rate. Among supported spans, 21.23% supplied only a variant or
omission and 24.58% had multiple alternatives. This is the desired shape:
useful islands of bounded evidence surrounded by explicit abstention, not a
license to fill every lacuna. The secondary join diagnostic found broad
third-witness textual coverage, but it remains a ceiling on textual context,
not physical-fit evidence. See
`reports/phase2_p2e_witness_recoverability.md`.

**Abstention-calibration follow-up (P2-E2, 2026-07-23):** a
composition-disjoint dev calibration/evaluation split found a small
high-agreement island, not a portable reliability guarantee. For two-sign
anchors around one hidden sign, the evidence-only unique-top baseline reached
74.90% agreement at 18.19% held-out coverage. A stricter calibration-selected
rule reached 90.37% point agreement at 4.73% coverage, but its held-out 95%
Wilson lower bound was 89.0%. The calibration-selected 80% rule transferred
at only 75.18%. Across all 12 anchor/mask cells, a 90%-lower-bound
calibration rule existed only for one-sign masks; no two-to-five-sign cell
qualified, and no cell reached 95%. Preserve this as evidence for narrow,
abstaining reconstruction and against broad automatic completion. Before any
new reconstruction model, measure threshold stability with
composition-folded calibration and stratify the failures by composition,
formulaicity, and witness coverage. See
`reports/phase2_p2e2_abstention_calibration.md`.

### P2-F — Graph/constraint assembly
**Question:** Q3. **Cost:** a day.
Joins obey hard structural constraints: a given edge joins at most
one partner; joins are transitive within a reconstructed tablet;
fragments of one composition form paths, not cliques. Take BM25's
top-k candidate graph and apply global constraint satisfaction
(matching/assignment rather than independent ranking). Question: does
enforcing one-edge-one-partner recover joins that per-query ranking
buries? This is how philologists reason natively.

### P2-G — Supervision-floor estimate
**Question:** Q5. **Cost:** hours (learning curves on existing runs).
Retrain nothing new; instead, subsample the existing training
positives at 25/50/75/100% and plot the dev-join curve for the
already-trained configurations where checkpoints or cheap refits
allow. If performance is flat in n, the ceiling is representational;
if it is still climbing at 100%, the honest claim is "under-powered,"
and the paper can state what n would likely be needed.

### P2-H — Fracture-engine release *(low cost, high transferability)*
**Question:** none — this is packaging.
The calibrated damage/fracture simulator is corpus-general
infrastructure (Akkadian, Ugaritic, papyrology). Package it as a
standalone artifact with its calibration methodology and the
documented caveat that vertical gap-width sampling is a modeling
assumption, not corpus-calibrated. Possibly the most reusable thing
Phase 1 produced.

### Premise audit 1 — after P2-A, P2-D, and P2-B (2026-07-23)

The first three probes jointly reject continued direct pairwise seam
modeling as the default formulation for tier-A no-overlap joins:
the seam-column target is absent, the hard set is not explained by
weaker relation labels, and the decisive physical modalities are not
encoded. Preserve textual-affinity/duplicate work, symbolic structural
compatibility, explicit abstention, and typed evidence packets.

The next justified probe is a **coverage-first P2-E**: map where an
independently attested same-composition witness supplies bounded
evidence for missing textual context before running any mediated
inference. Dev joins remain a diagnostic subset, not the organizing
target. P2-C is secondary; P2-F cannot create missing evidence. Full reasoning:
`reports/phase2_premise_audit_1.md`.

## 4. Constraints carried forward (non-negotiable)

- **Test side untouched.** Every probe runs on train/dev/discovery.
- **Tracers before scoring.** `00_tracers.py` runs at the top of any
  scoring pass; T1 (scramble sensitivity) is mandatory for any new
  content-consuming scorer.
- **Contracts at ingress.** C1–C10 apply to new code by default.
- **Canonical encoding only.** `encode_fragment_window()`; strict
  mode on.
- **Corpus statistics over declared universes.** Never query-derived.
- **Splits stay frozen** (git 7b010cde) unless a corpus migration is
  formally opened (TLHdig 0.3 is a separate future decision).
- **Demo track continues unchanged** on BM25, per Ixca's decision of
  2026-07-22. Phase 2 must not destabilize it.

## 5. What "done" looks like for Phase 2

Not a recall number. Phase 2 succeeds if it produces a recoverability
map: which missing-information targets are identifiable, from which
evidence, at what horizon, with what uncertainty, and where abstention
is required. Tier-A joins are one stress test. A well-supported "this
information is not recoverable from the encoded evidence, and here is
what would change that" is a complete and publishable result.

## 6. Deliberately NOT doing (unless a probe justifies it)

Training new models; scaling the encoder; hyperparameter search;
retrying the bi-encoder; D17b; anything touching the test side;
corpus migration; public launch of the demo.
