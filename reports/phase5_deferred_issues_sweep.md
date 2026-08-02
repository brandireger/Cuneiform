# Deferred-issues sweep — 2026-08-02

Prompted by one bug surfaced as a side effect of the lacuna split-estimand
rerun (item 5a, `reports/phase5_lacuna_scope_decision.md`):
`scripts/line_lang_rebuild.py`'s manifest step threw an `EvidencePolicyError`
that had nothing to do with that work. Asked to do a clean sweep for other
harmless-but-deferred issues of the same shape, rather than leave that one
bug as an isolated, unexplained crash.

**Method.** The same from-scratch, MD5-verified rebuild of the derived-data
chain used for item 5a was reused (nothing here needed re-deriving it). Each
active script in `scripts/` that can run without protected-test access or GPU
training was executed and checked for a clean exit; static greps covered
patterns known to be fragile (hardcoded paths, evidence-policy call sites).
Every finding below was **confirmed by running the fix**, not inferred from
reading code. Two apparent discrepancies turned out to be correctly-frozen
state rather than bugs — both are recorded in detail because dismissing them
without checking would have been the actual mistake.

## Fixed

1. **`scripts/line_lang_rebuild.py` and `scripts/line_lang_audit.py` — stale
   evidence policy.** Both request `"artifact_strict"` while asking for the
   `line_lang` feature. `line_lang` was reclassified from
   `OBSERVED_DOCUMENT_STRUCTURE` to `EDITORIAL_TRANSCRIPTION` by the Gate 0
   ruling (2026-07-25, `configs/evidence_registry.yaml`) — lb@lg is
   source-encoded editorial linguistic annotation, not directly observed
   structure — but neither script's policy request was updated to match.
   Both have thrown on their manifest-generation step ever since (the actual
   parquet/audit output writes successfully *before* the crash, which is why
   this went unnoticed: the visible artifacts looked fine). Fixed by
   requesting `"transcription_assisted"`, the minimal policy that permits
   `EDITORIAL_TRANSCRIPTION` while still denying `cu`/`mrp`/`lemma` fields.
   Verified: both scripts now complete cleanly; the corrected manifests
   report `editorial_content_fraction: 1.0` where they previously would have
   (had they not crashed) claimed `0.0` — a real accuracy improvement in the
   provenance record, not just a crash fix. A regression test now pins the
   registered class against both policies
   (`tests/test_evidence_policy.py::test_line_lang_requires_transcription_assisted_not_artifact_strict`).

2. **`Archive/scripts/07_metadata_patch.py` — broken auto-chain to
   `04_edges.py`.** After patching `corpus.parquet`/`doc_table.parquet`, the
   script re-runs `04_edges.py` via `subprocess.run([sys.executable,
   "04_edges.py", zip_path], ...)` — a bare filename that only resolves if
   the caller's cwd happens to be `Archive/scripts/`, not `Archive/` (the
   directory the script's own documented usage line runs it from, and where
   `p2_out`/`p25_out` actually live). Every invocation under the documented
   usage has silently fallen through to the `sys.exit(1)` after printing
   "Re-running 04_edges.py..." — the corpus patch itself succeeded, but the
   edges rebuild it depends on never ran automatically. Fixed by resolving
   the sibling script path from `Path(__file__).resolve().parent` instead of
   a bare string. Verified end-to-end in an isolated scratch copy (rebuilt
   02→07 from the pinned corpus): the script now completes and prints
   "Reports in: ..." for the first time.

3. **Four `Archive/scripts/*.py` files — hardcoded Windows git path.**
   `10_resplit.py`, `19_pretrain.py`, `20_biencoder.py`, `26_retrieve.py` all
   call `git rev-parse HEAD` via a literal
   `r"C:\Program Files\Git\bin\git.exe"` instead of the portable `"git"`
   already used everywhere else in this codebase (e.g.
   `lib/evidence_policy.py`). On any non-Windows machine — or a Windows
   machine with git installed anywhere else — this silently falls back to a
   caught exception and a `git_commit: "N/A"` provenance field. Replaced with
   bare `"git"` in all four. Verified for `10_resplit.py` (the only one of
   the four that isn't gated behind Gate 3 training authorization) — a
   fresh rerun now correctly resolves a real commit hash instead of `N/A`.
   The other three were fixed identically (same call shape, same fix) but
   deliberately **not executed** — they belong to the model-ladder/pretrain
   pipeline, which stays untouched per the standing Gate 3 constraint.

## Investigated, confirmed correct, deliberately not touched

These surfaced as large diffs during the empirical sweep and could easily
have been mistaken for bugs. Both turned out to be already-correct frozen
state; the diffs were artifacts of an *incomplete* or *inapplicable* rebuild
on this session's part, not defects in the pipeline.

4. **`configs/tokenizer.json`.** Rerunning
   `scripts/rebuild_tokenizer_hittite_only.py` produces a genuinely different
   1,957-entry vocabulary against the committed 2,374-entry one. `git log`
   shows this was already tried once and deliberately reverted
   (`aecdddb "Revert tokenizer vocab; fix missed render_fragments call
   site"`): the live vocab is embedded in a real 60,000-step pretrained
   checkpoint (`runs/pretrain_base/checkpoint.pt`), and regenerating it would
   break every P2-E script's mandatory embedding-matrix-size tracer check.
   Retraining is explicitly Gate-3 territory. Confirmed the rebuild code path
   itself still works (matches the numbers from the original 905c320
   attempt), then reverted the output without committing it.

5. **`Phase4/phase4_out/workbench_ui_out/workbench_review_queue.js`.** Its
   `channels_logical_sha256` is a pinned invariant per
   `PHASE5_SUCCESSOR_HANDOFF.md` ("if it moves without a deliberate policy
   change, something altered what a specialist sees"). Rerunning
   `scripts/phase4_workbench_review_export.py` produced a different hash.
   Traced to the cause before touching anything: this session only rebuilt
   the `SAME_LANGUAGE_AS_QUERY` candidate file
   (`unresolved_similarity_candidates.jsonl`, via
   `phase4_unresolved_clustering.py`); the `CROSS_LANGUAGE_PARALLEL` channel
   reads a separate file
   (`unresolved_similarity_candidates_cross_language.jsonl`) that was never
   rebuilt this session, so that channel's logical hash came back `None`
   instead of matching. Confirmed via a field-by-field manifest diff, not
   guessed. Reverted the output; the committed queue and its pinned hash are
   untouched.

## Confirmed not-a-bug (missing optional external data)

`scripts/corpus_expansion_audit.py` and `scripts/corpus_migration_design.py`
both fail on `external_corpora/TLHdig_0.3/...zip` not being present. Per
`AGENTS.md`, TLHdig Beta 0.3 is "a quarantined migration candidate, not the
active corpus" — this is expected behavior without that optional, unadopted
corpus on disk, not a defect. Not fetched or otherwise acted on.

## Observed, not fixed: JSON key-order nondeterminism

Several rebuilt JSON/JSONL artifacts (`p2b_materiality_inventory.json`'s
`tag_documents` counter, `join_pairs.jsonl`'s `member_a`/`member_b`
assignment on symmetric pairs, `bins_report.md`'s tie-broken row order) come
back with a different key/row order than the committed version on every
rerun, even though the **values** are identical once compared
order-independently (verified programmatically, not by inspection, for each
case encountered). This is Python's per-process hash randomization affecting
`dict`/`set`/`Counter` iteration order in code that doesn't explicitly sort
before serializing. It does not affect correctness — every case checked
during this sweep confirmed identical underlying data — but it does mean a
rebuilt report is not byte-identical to its committed counterpart, which
could read as a false "something changed" signal to a future reader running
a diff. Not fixed here: pinning `PYTHONHASHSEED=0` (or sorting before
serialization at each affected call site) is a project-wide reproducibility
policy decision, not a discrete bug, and is out of scope for this sweep.
Flagging so it isn't rediscovered from scratch.

## What this sweep did not cover

`00_tracers.py` and `13_bm25.py` require a Phase 3 model/embedding artifact
(`fragment_renderings.parquet`) and touch the model-ladder/retrieval work
respectively — both Gate-3-adjacent and out of scope. `scripts/
phase4_workbench_backup.py` and `phase4_workbench_ingest_events.py` mutate
expert-session state and were not run without a real session to act on.
Every P2-Ex fold-calibration script (`p2e2` through `p2e9`, `p2e10`) already
has committed, ratified output and is individually a multi-minute-plus
computation; their code paths were already exercised indirectly and
validated byte-for-byte during the item 5a rerun (`p2e2`, `p2e8`, `p2e9` are
imported directly by `real_gap_calibration.py`), so they were not
independently re-executed here.

## Validation

```
python -m unittest discover -s tests      # 290 pass (was 289; one new
                                           # regression test added)
ruff check lib scripts tests demo         # clean
python lib/contracts.py                   # 20/20
python scripts/p4d_stamp_stale_reports.py --check   # unchanged from baseline
```
