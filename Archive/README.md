# Hittite Fragment Matching

Content-based join/duplicate suggester for fragmentary Hittite cuneiform
texts, built on the openly-licensed TLHdig corpus. **Start with
[`CLAUDE.md`](CLAUDE.md)** — it is the design authority for this
project (research question, corpus schema, cleanroom rules, task
definitions, phase sequence). This file is just a map of what's on
disk and how to run it; if the two ever disagree, `CLAUDE.md` wins.

Division of labor: an AI assistant (Claude Code) writes the code, this
laptop runs it (single consumer GPU, per the project's compute
budget). Only small artifacts — reports, metrics, configs — round-trip
through chat; the raw corpus and model checkpoints never do.

## Where things are

```
CLAUDE.md               design authority -- read this first
README.md               this file -- orientation only
requirements.txt        pip dependencies (pandas/pyarrow/torch/sklearn/...)
TLHdig_0.2.0-beta.zip    pinned corpus snapshot (gitignored, see "Corpus" below)

scripts/                numbered P1-P4 pipeline scripts (01_inventory.py ...
                        21_pretrain_report.py) + run_d15_grid.py -- run in
                        numeric order; see "Pipeline" below for what each does
lib/                    reusable modules imported by scripts/ -- eval_harness.py
                        (retrieval-eval, BM25/TF-IDF, metrics, H1 patch),
                        hittite_tokenizer.py (sign-level tokenizer),
                        hittite_model.py (transformer encoder + masking/
                        boundary code), fracture_engine.py (synthetic-fracture
                        cut operators), decompose_corpus.py (tag-boundary-
                        aware XML re-walk for sign decomposition, P4-only)
configs/                pretrain_config.json, biencoder_config.json,
                        tokenizer.json -- active configs read by scripts/
demo/                   Takšan demo (DM) track -- PARALLEL to the P-pipeline,
                        never blocks/contaminates it (specs/TAKSAN_DEMO_SPEC.md).
                        dm0_cu_verification.py, cu_alignment.py, dm_out/

specs/                  frozen, point-in-time phase specifications (written
                        BEFORE each phase's implementation; not updated
                        retroactively -- CLAUDE.md is the living record)
reports/                small human-readable phase reports (the artifacts
                        that get shared back to the architect/mentor),
                        including the DM track's dm0_cu_report.md
references/             cited papers (Tyndall 2012, Yavasan & Gordin 2025, ...)

p1_out/ … p4_out/       derived outputs per phase (parquet/json/jsonl;
                        parquet is gitignored -- regenerable from the corpus)
results/, results_p3_patched/   P3 baseline metrics (pre-/post-H1-patch)
runs/                   training run directories (gitignored entirely --
                        loss curves + checkpoints; "no checkpoints" is a
                        standing rule for what leaves this machine)
```

**Invocation convention: always run scripts from the project root**, e.g.
`python scripts/19_pretrain.py --config configs/pretrain_config.json`, never
`cd scripts` first. Every script's data paths (`p2_out/`, `p4_out/`, `runs/`,
`configs/...`) are relative to the current working directory, not the
script's own location — `sys.path` for `lib/` imports is the only thing
resolved relative to the script file itself.

## Corpus setup

Pinned snapshot: **TLHdig Beta 0.2.0**, CC BY 4.0, DOI
[10.5281/zenodo.15459134](https://zenodo.org/records/15459134).

    https://zenodo.org/records/15459134/files/TLHdig_0.2.0-beta.zip?download=1

Verify integrity (expected MD5 `93e71e2560f5e109c87713d5590cb059`):

    Get-FileHash TLHdig_0.2.0-beta.zip -Algorithm MD5   # Windows
    md5sum TLHdig_0.2.0-beta.zip                        # macOS/Linux

Keep the zip as-is at the repo root; every script reads it directly,
never extracted. Cite: Müller, Prechel, Rieken & Schwemer (2025).

## Pipeline (run in numeric order; each phase's report lands in `reports/` or its own `p*_out/`)

| # | Script | Phase | Status |
|---|---|---|---|
| 01 | `scripts/01_inventory.py` | P1 — schema census (stdlib only) | done |
| 02-06 | `scripts/02_parse.py` … `06_dataset_report.py` | P2 — parser + dataset builder | done, frozen |
| 07-11 | `scripts/07_metadata_patch.py` … `11_p25_report.py` | P2.5 — bin reframe, join tiers, resplit | done, **frozen** (git `7b010cde`) |
| 13 | `scripts/13_bm25.py` | P3 — BM25/TF-IDF baselines | done |
| 14 | `scripts/14_tyndall.py` | P3 — Tyndall (2012) MaxEnt replication | done |
| 15 | `scripts/15_p3_report.py` | P3 — master acceptance report | done |
| 16 | `scripts/16_h1_patch.py` | P4 H1 — docID-family harness patch deltas | done |
| 17 | `scripts/17_tokenizer.py` | P4 D12 — sign-level tokenizer | done |
| 18 | `scripts/18_fracture.py` | P4 D13 — synthetic fracture engine | done |
| 19 | `scripts/19_pretrain.py` | P4 D14 — encoder pretraining | done (60,000/60,000 steps) |
| 20 | `scripts/20_biencoder.py` | P4 D15 — contrastive bi-encoder | done (3-mix ablation grid) |
| 21 | `scripts/21_pretrain_report.py` | P4 D14 acceptance-check report | done |
| — | `scripts/run_d15_grid.py` | drives D15's 3-mix ablation grid sequentially | done |

Numbering quirk: `specs/P4_NEURAL_SPEC.md` originally suggested
`12_tokenizer.py` … `15_biencoder.py`, but P3's baseline scripts had
already claimed `13`-`16` by the time P4 started, so the actual P4
deliverables landed at `17`-`21` instead. `CLAUDE.md`'s phase-sequence
section is the authoritative mapping if in doubt.

## Demo track (DM)

`specs/TAKSAN_DEMO_SPEC.md` governs a separate, private demo workbench
("Takšan") that runs parallel to the P-pipeline and must never block or
contaminate it — it's a display layer over precomputed artifacts, no model
runs at demo time. `demo/dm0_cu_verification.py` is DM0 (the `cu`-glyph
verification gate, run first, gates the glyph layer); `demo/cu_alignment.py`
is the resulting reusable glyph/token alignment module DM1/DM2 import for
rendering. See `reports/dm0_cu_report.md` for the full investigation
(including two rejected structural hypotheses) and current CONDITIONAL GO
status.

## Long-running jobs

Training runs that exceed a single working session (D14's base pretrain,
D15's three-way ablation grid) are launched as **detached Windows Scheduled
Tasks**, not background shell processes — a background process tied to the
assistant's session does NOT survive session teardown (learned the hard way
during P3's Tyndall replication). Both D14 and D15 have completed; check
status/history with:

    Get-ScheduledTask -TaskName CuneiformPretrainBase | Select TaskName,State
    Get-ScheduledTask -TaskName CuneiformBiencoderGrid | Select TaskName,State

Every such script follows the same engineering law: checkpoint at
natural step intervals, atomic writes (`.tmp` + `os.replace`), full
resumability (model + optimizer + RNG state), seed + git commit +
corpus version logged in every checkpoint.

## Cleanroom rules (summary — full detail in `CLAUDE.md`)

Test-side data is never touched by anything in P4; dev is for model
selection only; restorations are training signal but never evaluation
ground truth; splits are frozen and composition-disjoint; novel
model-proposed joins/duplicates are quarantined, never counted as
positives.
