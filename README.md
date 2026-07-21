# Hittite Fragment Matching — Local Compute Setup

Division of labor: Claude writes code; this laptop runs it. Only small
artifacts (reports, metrics) go back into the chat — never the corpus
or model weights.

## Phase 0 — Acquire and verify the corpus

Download the pinned snapshot (TLHdig 0.2.0-beta, CC BY 4.0,
DOI 10.5281/zenodo.15459134):

    https://zenodo.org/records/15459134/files/TLHdig_0.2.0-beta.zip?download=1

Verify integrity (expected MD5: 93e71e2560f5e109c87713d5590cb059):

    # Windows PowerShell
    Get-FileHash TLHdig_0.2.0-beta.zip -Algorithm MD5

    # macOS / Linux
    md5sum TLHdig_0.2.0-beta.zip

Keep the zip as-is; scripts read it directly without extraction.

## Phase 1 — Inventory (this deliverable)

Requires only Python 3.9+ standard library. No pip installs.

    python 01_inventory.py /path/to/TLHdig_0.2.0-beta.zip

Outputs (into ./inventory_out/):

    inventory_report.md     — human-readable summary  <- upload this to chat
    inventory_report.json   — machine-readable full census
    sample_documents.txt    — 3 raw XML samples, truncated  <- and this

Upload `inventory_report.md` and `sample_documents.txt` back to the
chat. Those two small files let Claude design the real parser against
observed reality instead of assumptions.

## What the inventory answers

1. Document/file count and size distribution
2. Full XML tag + attribute census (schema discovery)
3. Where CTH composition numbers live and their coverage
4. Join notation ("+" conventions in manuscript identifiers) — our
   ground-truth positives for physical joins
5. Publication-prefix histogram (KBo, KUB, HKM, Or., KuT, KpT ...) —
   the provenance signal for the Hattusa-vs-provincial split
6. Bracket/restoration marker frequencies — feasibility data for the
   restoration-verified refinement loop and leakage controls

## Phase 2 — parser + dataset builder (done)

Requires Python 3.9+ plus pandas/pyarrow (`pip install -r requirements.txt`).
Spec: `P2_PARSER_SPEC.md`. Run in order (each reads the same corpus zip):

    python 02_parse.py TLHdig_0.2.0-beta.zip      # -> corpus.parquet, doc_table.parquet
    python 03_unjoin.py TLHdig_0.2.0-beta.zip      # -> join_pairs.jsonl
    python 04_edges.py TLHdig_0.2.0-beta.zip       # -> edges.parquet
    python 05_splits.py                            # -> splits.parquet, splits.json
    python 06_dataset_report.py                    # -> dataset_report.md (master report)

Outputs (into ./p2_out/): `corpus.parquet` (word-token grain, ~1.52M
rows) and `doc_table.parquet` stay local (too large for chat);
`parse_report.md`, `unjoin_semantics.md`, `join_stats.md`,
`edges_report.md`, `split_report.md`, `dataset_report.md` are the
small human-readable artifacts to upload back to chat.

## Coming phases (each arrives as scripts like this one)

    Phase 3 — BM25 + Tyndall-replication baselines
    Phase 4 — sign-tokenizer + masked-span pretraining (single GPU)
    Phase 5 — bi-encoder retrieval + edge-continuation join scorer
    Phase 6 — evaluation matrix: joins / duplicates / pooled
