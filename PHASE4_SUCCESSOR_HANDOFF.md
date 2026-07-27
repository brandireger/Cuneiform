# Phase 4 successor handoff — Gates 0–2 complete, P4-D and P4-E done

**Handoff date:** 2026-07-27
**Repository state:** Gate 2 accepted; **P4-D language-aware APIs and P4-E
Unresolved Evidence Workbench implemented and ratified**. Protected-test
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
   update an accepted hash to make a check pass.
5. **Never read `cu`** as semantic input, even for a display field.
6. **Gate 3 remains closed.** Do not begin P4-F, retrain, or alter the frozen
   D14 checkpoint.

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

### 2. P4-G rerun — has a hard deadline

Rerun the P2-E and real-gap artifacts under the P4-D projection. **This must
precede any P7 paper drafting**: current coverage figures are
language-contaminated on both the witness and query sides. Ten affected
reports carry a `[PREDATES P4-D]` stamp (applied by
`scripts/p4d_stamp_stale_reports.py`; idempotent, `--check` for CI) until the
rerun happens. Removing a stamp without rerunning would be a lie.

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
- **Mixed-line policy** stays `EXCLUDE_LINE` (846 lines lost in the measured
  slice). Revisit only if witness coverage proves to be the binding constraint
  on real-gap results — which the P4-G rerun would reveal.

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
