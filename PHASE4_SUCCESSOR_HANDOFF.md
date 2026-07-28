# Phase 4 successor handoff — Gates 0–2 complete, P4-D/E done, P4-E2 added

**Handoff date:** 2026-07-27 (P4-E2 appended same day)
**Repository state:** Gate 2 accepted; **P4-D language-aware APIs and P4-E
Unresolved Evidence Workbench implemented and ratified; P4-E2 expert interface
implemented, two queue exclusions awaiting ratification**. Protected-test
access and GPU training remain unauthorized; Gate 3 is untouched.

Read `AGENTS.md` first. It remains the design authority. This handoff records
operational state and does not widen any authorization boundary.

## Start here

The single most useful thing to read before touching anything is
`reports/phase4_p4de_ratification.md` — the seven decisions Ixca ratified on
2026-07-27 and, more importantly, *why*. Several of them constrain what you
may do next.

Then, in order of usefulness:

- `reports/phase4_p4d_language_aware_apis.md`
- `reports/phase4_p4e_unresolved_workbench.md`
- `specs/LANGUAGE_LAYERS_V2.md`, `specs/UNRESOLVED_EVIDENCE_WORKBENCH.md`

## Completed work

### Gates 0–2 (2026-07-25)

| gate | artifact | accepted logical hash |
|---|---|---|
| 0 | rule `word_override_else_line_v2`, `configs/language_layers_v2.json` | — |
| 1 | `migrations/language_layers_v2/language_spans.parquet` (389,325 rows) | `d0126c4eacc2c6c58711516e725f90193d9cc964a1700ea2a5def3289c7c9296` |
| 2 | `Phase4/phase4_out/multilingual_tokens_v2.parquet` (2,923,640 rows / 20,711 docs) | `35914a01ff03863f76ee0a56352d2d870881dc581c1253430a2eda102e9bfb6a` |

Rebuild: `python scripts/phase4_language_layers_v2.py`, then
`python scripts/phase4_multilingual_token_dataset.py`.

### P4-D — language-aware APIs (2026-07-26)

`lib/language_scope.py` provides a validated, **required** `LanguageScope`;
`require_language_scope()` fails closed on `None`, bare strings, `auto`,
`default`, and `language_blind`. `lib/language_lookup_v2.py` provides the
word-aware `EffectiveLanguageIndex` over the Gate 2 dataset, with per-line
decisions counted by named reason.

`p2e_witness_recoverability.render_fragments` — the shared anchor-index
construction behind every P2-E and real-gap script — now requires
`language_scope` and `language_index`. All eight call sites were migrated to
`HITTITE_ONLY`. The real-gap **query** side is language-resolved too: a gap may
only ASK under the same explicit scope that governs which witness lines may
ANSWER.

Expert-decision contract **1.1.0** adds a required `language` block. An
unresolved query language obliges an explicit `LANGUAGE_*` limitation, so a
packet can never present itself as language-established when it is not.

Measured delta (probe, not republished): ~9.5% of the real-gap query
denominator was non-Hittite or unresolved; 932 lines the line-granularity
filter admitted are refused as mixed-language; witness-index tokens
248,998 → 233,883.

**Deliberately not migrated:** `lib/hittite_tokenizer.py` and
`scripts/rebuild_tokenizer_hittite_only.py` keep the older line-granularity
argument. That path feeds the frozen D14 vocabulary; changing it risks the
vocab-size mismatch that already broke `runs/pretrain_base/checkpoint.pt` once.
Gate 3 territory.

### P4-E — Unresolved Evidence Workbench (2026-07-26/27)

| component | file |
|---|---|
| Executable contract (1.1.0) | `lib/unresolved_evidence.py` |
| Occurrence extraction | `scripts/phase4_unresolved_extraction.py` |
| Deterministic clustering | `scripts/phase4_unresolved_clustering.py` |
| Event-log backup | `scripts/phase4_workbench_backup.py` |
| Tests (30) | `tests/test_unresolved_evidence.py` |

**238,745 occurrences**, logical SHA-256
`fd387b97a9aeb1cb9b7e9a89f3b20f8b015ef50af524695cec6567b64b191f47`, zero
protected-test occurrences. Clustering: 4,566 same-language and 1,278 opt-in
cross-language proposals, all `SYSTEM_PROPOSAL`, written to separate files so
the two channels stay separable on disk, not merely in a field.

Rebuild:

```powershell
python scripts/phase4_unresolved_extraction.py
python scripts/phase4_unresolved_clustering.py
python scripts/phase4_unresolved_clustering.py --cross-language
```

### P4-E2 — expert interface (2026-07-27)

| component | file |
|---|---|
| Review-queue export | `scripts/phase4_workbench_review_export.py` |
| Interface | `demo/workbench_unresolved_prototype.html` |
| Expert-session ingest | `scripts/phase4_workbench_ingest_events.py` |
| Tests (15) | `tests/test_phase4_workbench_interface.py` |

Rebuild: `python scripts/phase4_workbench_review_export.py`, then open the HTML
file. Judgments leave the browser as a session JSON and come back through
`python scripts/phase4_workbench_ingest_events.py <session.json>` — the only
supported path into the log.

The queue exists because clustering is Zipfian and it only bites when a person
is put in front of it: the largest same-language proposal has 95,530 members
whose whole shared sequence is `x`, and ranking by document count instead
surfaces the single signs `a` (3,542 documents), `i`, `e`. Policy
`contentful_sequence_length_v1` excludes placeholder-only sequences and
sequences under 2 signs, then ranks by sequence length before document count.
**Both exclusions await ratification** — they decide what a specialist is
shown, and `--min-sequence-length 1` reverses the second one today.

Two things about it that are load-bearing:

- **A queue is a view.** It never mutates an occurrence, a proposal, or an
  accepted hash. Selection lives in the export precisely so the ratified
  logical hashes stay untouched.
- **Whole canonical records travel with it**, because the event contract binds
  a judgment to `canonical_sha256(reviewed_record)`. A trimmed display object
  would bind the judgment to something that exists nowhere.

Ingest recomputes each event's `reviewed_record_sha256` from the record on
disk and refuses on mismatch, refuses to append when the log's current head
appears in no backup-ledger entry, and re-chains the session onto the real
head. **The page has not been opened in a browser** — no browser was available
in the implementing session. Field-contract, hash-vector, and every Python
path were verified; rendering and interaction were not.

## Standing constraints you must not violate

1. **Do not change the workbench category vocabulary casually.** Occurrence
   identity hashes location *and* category set, and run boundaries are cut on
   category change. Every vocabulary change orphans existing expert
   annotations. This is why the contract decisions were settled before first
   expert use, while the cost was zero.
2. **`LEXICAL_UNKNOWN` is reserved for expert assertion.** Extraction never
   sets it. A frequency detector can establish that a form is rare in this
   corpus; it cannot establish that a form is unknown to Hittitology. Use
   `RARE_FORM` for the frequency signal, and keep the two distinct.
3. **Run `scripts/phase4_workbench_backup.py` before and after every expert
   session.** The event log is append-only and hash-chained; a lost file is
   unrecoverable *and* un-reconstructable. Occurrences rebuild from the pinned
   corpus at any time; a specialist's judgments do not.
4. **Determinism is checked logically, not by file bytes.** Parquet footer
   metadata and run timestamps differ between builds — an early P4-E
   reproducibility check failed for exactly this reason. Compare
   `*_logical_sha256`. If a logical hash changes, stop and diagnose; never
   update an accepted hash to make a check pass. The clustering channel was
   missing such a hash entirely until 2026-07-27 (it recorded only a file
   digest over a JSONL whose records embed `created_utc` and `git_commit`, so
   it moved on every rerun by construction); it now reports
   `candidates_logical_sha256`, and the review queue reports
   `channels_logical_sha256`.
5. **Never read `cu`** as semantic input, even for a display field.
6. **Gate 3 remains closed.** Do not begin P4-F (language-conditioned
   pretraining), retrain, or alter the frozen D14 checkpoint. Note the letter:
   the expert interface built on 2026-07-27 is **P4-E2**, a continuation of
   P4-E, precisely because P4-F is this forbidden training item and P4-G's
   reruns are gated behind it.

## Next work, in recommended order

### 1. Expert interface for the workbench (ratified as the next build)

The data layer is complete and has no UI; a Hittitologist cannot currently use
it. `specs/UNRESOLVED_EVIDENCE_WORKBENCH.md` § "Expert interface" is the
contract. `demo/taksan_missing_text_prototype.html` is the closest existing
artifact — a different contract and record shape, but the two could share a
shell, and it already renders limitations, an assistance profile, and (as of
P4-D) a language panel.

Non-negotiables: same-language clusters by default with cross-language as a
visibly enabled channel; competing hypotheses rather than one forced reading;
an always-available withhold-judgment action; no similarity score labeled a
probability; contradictory occurrences never hidden.

### 2. ~~P4-G rerun~~ — **DONE 2026-07-27**

All ten artifacts recomputed under the required word-aware `HITTITE_ONLY`
scope in under five minutes total; see `reports/phase4_p4g_rerun.md`.
Ratification decision 5 is closed and P7 is no longer blocked on
language-contaminated numbers.

Nine stamps are gone because the reports are current. **The census keeps its
note**: it is a deliberately language-blind structural count, so that note was
a scope disclosure, not a staleness claim — regenerating it stripped something
still true, and the newly-wired CI guard caught that within minutes.
`scripts/p4d_stamp_stale_reports.py --check` now runs in CI and enforces both
directions: a stale report cannot lose its warning, and a report listed in
`RERUN_UNDER_P4D` cannot keep one.

Corrected headline: calibrated coverage is **839 of 181,051 corpus real gaps
(0.46%)**, and cross-line anchors are **89.9% of anchored gaps with no
calibration at all**. That is now the highest-leverage backend item — see
"Next work" below.

### 2b. Cross-line calibration — census DONE, folds still open

`scripts/p2e8_cross_line_recoverability.py` (2026-07-27) is the prerequisite
census; see `reports/phase2_p2e8_cross_line_recoverability.md`. **It is a
census, not a calibration** — nothing in it may be presented beside a
candidate as a rate.

It settles the question the prohibition rested on. At `a2_m1`, same-line spans
include the true reading in 20.94% of eligible cases; cross-line spans in
**4.27%**. Borrowing the same-line rate would have overstated the evidence by
roughly **5×**, on 89.9% of anchored real gaps.

Three things a successor needs from it:

- **Two witness-admission rules, both measured, both awaiting ratification.**
  `STRICT` admits only boundary-crossing witnesses; `LAYOUT_AGNOSTIC` also
  admits same-line ones, on the ground that line division is scribal layout
  rather than textual structure. `LAYOUT_AGNOSTIC` roughly doubles gold
  inclusion (4.27% → 7.21%) and is philologically defensible, but it is a
  philological call, not an engineering one.
- **Where the break falls barely matters** — 2.87–3.62% across all five
  boundary regions. That a break is crossed at all is the cost, which argues
  for one cross-line stratum rather than five.
- **41.5% of adjacent line boundaries are refused, not crossed**, because a
  neighbouring line is out of scope. Crossing one would fabricate adjacency.

**Fold structure DONE (P2-E9, 2026-07-28)** — and it returned a negative
result worth more than a positive one would have been. Every fold abstains
under both admission rules: cross-line tops out at ~80% rank-1 against the
inherited **0.90** target that same-line clears at ~91%. The pipeline refusing
to present any cross-line candidate is correct behaviour, not a gap.

**Two ratifications now block cross-line real gaps**, and both are
philological, not engineering:

1. `STRICT` vs `LAYOUT_AGNOSTIC` (does scribal line division bear on textual
   evidence?).
2. Whether cross-line gets its **own declared calibration target**. A
   sensitivity sweep is reported and is deliberately *not* a proposal —
   picking a target because it produced output would report a search as a
   measurement.

Until both are ratified, `real_gap_calibration.py` correctly keeps gating on
`if not g["is_cross_line"]`.

### 3. Gate 3 (training) — still requires a full proposal

Named hypothesis, config, compute estimate, GPU budget, falsifier, new output
paths that cannot overwrite the frozen D14 run, sampling policy, and the
conditioned-versus-unconditioned tracer.

## Known open items

- **`Phase4/phase4_out/annotation_backups/`** does not exist yet; it is created
  on first backup. No expert events have been recorded, so the workbench has
  not yet been used for real labor.
- **112 non-test documents** in the historical decomposed cache have no Gate 2
  language coverage. **Investigated and closed 2026-07-26**: 18
  `QUARANTINE_DUPLICATE_STEM`, 93 identifier-form mismatches whose real archive
  stems classified `QUARANTINE_UNMATCHED`, and 1 XML parse error
  (`KUB 12.24`, `mismatched tag: line 45, column 2`). All explained by stated
  Gate 1 admission rules; not a defect. The identifier-form problem is the same
  canonical-identifier-group issue already flagged in
  `reports/corpus_expansion_tlhdig_03_migration_design.md`, now confirmed to
  bound Phase 4's document universe too.
- **The historical decomposed cache** carries 9,940 rows under duplicated
  `(doc_id, line_index_in_doc, word_pos)` keys across 28 documents. The
  word-aware lookup refuses any line whose caller-side token count disagrees
  with Gate 2, rather than trusting a doc-id blocklist. Do not "fix" the cache;
  it is immutable.
- **Mixed-line policy** stays `EXCLUDE_LINE` — and the P4-G rerun has now
  answered the question that was waiting on it. Mixed-language lines cost
  **943 of 25,559 gaps (3.7%)** in the measured witness-check slice, 101 in
  the single-sign calibration slice and 47 in the multi-sign one. It is not
  the binding constraint on real-gap results; cross-line calibration is, by
  more than an order of magnitude. `EXCLUDE_LINE` stands, and revisiting it
  would be optimizing the wrong term.

## Validation at handoff

```powershell
python -m unittest discover -s tests
ruff check lib scripts tests demo --output-format concise
git diff --check
```

- **162 unit tests pass** (107 at the Gate 2 handoff; +25 from P4-D, +30 from
  P4-E).
- Ruff clean for `lib`, `scripts`, `tests`, `demo`.
- `git diff --check` clean.
- 4,000 sampled occurrences and all 5,844 cluster proposals validate against
  the ratified schema; every `RARE_FORM` carries a named detector; no
  extraction-set `LEXICAL_UNKNOWN`.
