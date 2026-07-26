# Missing-text demo data export report

Sources: `Phase2/phase2_out/p2e4_candidate_set_packets.jsonl` (16 packets) + `Phase2/phase2_out/p2e6_multisign_packets.jsonl` (12 packets).
Output: `Phase3/demo_out/missing_text_demo_data.js` (213.5 KB).

**28 real packets exported** (16 single-sign, 12 multi-sign; 24 present-candidates, 4 abstain; 3 with a collapsed tail). Every packet is adapted via `lib/expert_decision_contract.py`'s `adapt_p2e4_packet()`/`adapt_p2e6_packet()`, which strips hidden evaluation gold (the raw source's `outcome`, top-level `evidence`/`support`/`contradictions`/`observable_*` fields are never read) and runs `validate_suggestion_packet()` before returning.

**Cleanroom check**: every packet's fragment_id (base doc_id after stripping a trailing `::N` witness-member suffix) was looked up in `Phase1_pipeline/p2_out/splits.parquet`'s frozen `main_split` column. All 28 resolved to `dev`. The export hard-aborts on any packet resolving to `test`, `train`, `discovery`, or an unrecognized doc_id.

| packet_id | fragment_id | mode | status | shown/total (tail) |
|---|---|---|---|---|
| `p2e4-001` | KBo 14.11 | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-002` | KUB 57.79 | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-003` | KBo 54.99+ | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-004` | KBo 11.46 | SINGLE_SIGN | PRESENT_CANDIDATES | 2/2 (0 collapsed) |
| `p2e4-005` | KBo 12.25 | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-006` | KBo 16.23 | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-007` | KBo 19.109a | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-008` | KUB 31.123+ | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-009` | KBo 12.25 | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-010` | HKM 102 | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-011` | KBo 26.81 | SINGLE_SIGN | PRESENT_CANDIDATES | 1/1 (0 collapsed) |
| `p2e4-012` | KBo 53.10 | SINGLE_SIGN | PRESENT_CANDIDATES | 2/2 (0 collapsed) |
| `p2e4-013` | KBo 5.6 | SINGLE_SIGN | PRESENT_CANDIDATES | 2/2 (0 collapsed) |
| `p2e4-014` | CHDS 5.12 | SINGLE_SIGN | PRESENT_CANDIDATES | 2/2 (0 collapsed) |
| `p2e4-015` | KBo 11.52 | SINGLE_SIGN | PRESENT_CANDIDATES | 2/2 (0 collapsed) |
| `p2e4-016` | IBoT 2.18+::2 | SINGLE_SIGN | PRESENT_CANDIDATES | 2/2 (0 collapsed) |
| `p2e6-001` | CHDS 3.71 | MULTI_SIGN | ABSTAIN_INSUFFICIENT_EVIDENCE | 0/0 (0 collapsed) |
| `p2e6-002` | CHDS 3.71 | MULTI_SIGN | PRESENT_CANDIDATES | 12/48 (36 collapsed) |
| `p2e6-003` | FHL 61 | MULTI_SIGN | PRESENT_CANDIDATES | 5/5 (0 collapsed) |
| `p2e6-004` | IBoT 4.346+::1 | MULTI_SIGN | ABSTAIN_INSUFFICIENT_EVIDENCE | 0/0 (0 collapsed) |
| `p2e6-005` | CHDS 3.71 | MULTI_SIGN | PRESENT_CANDIDATES | 12/33 (21 collapsed) |
| `p2e6-006` | IBoT 4.346+::2 | MULTI_SIGN | PRESENT_CANDIDATES | 11/11 (0 collapsed) |
| `p2e6-007` | IBoT 4.346+::1 | MULTI_SIGN | ABSTAIN_INSUFFICIENT_EVIDENCE | 0/0 (0 collapsed) |
| `p2e6-008` | IBoT 4.346+::1 | MULTI_SIGN | PRESENT_CANDIDATES | 4/4 (0 collapsed) |
| `p2e6-009` | KBo 12.27 | MULTI_SIGN | PRESENT_CANDIDATES | 6/6 (0 collapsed) |
| `p2e6-010` | IBoT 4.346+::1 | MULTI_SIGN | ABSTAIN_INSUFFICIENT_EVIDENCE | 0/0 (0 collapsed) |
| `p2e6-011` | IBoT 4.346+::2 | MULTI_SIGN | PRESENT_CANDIDATES | 7/7 (0 collapsed) |
| `p2e6-012` | KBo 12.27 | MULTI_SIGN | PRESENT_CANDIDATES | 12/15 (3 collapsed) |

## Fragment context export

`Phase3/demo_out/fragment_context_data.js` (1909.2 KB): full line-by-line transliteration for the 19 distinct fragments referenced above (948 lines, 3890 words total), sourced directly from `Phase1_pipeline/p2_out/corpus.parquet`.

**Determinative categories**: 513/722 (71.1%) of determinative-marked words matched CLAUDE.md's already-vetted starting inventory (matched at the corpus's real Unicode encoding — Ḫ, subscript digits — not the plain-ASCII prose spelling). The remaining 209 are labeled "uncategorized" in the UI, never guessed. Sample unmapped leading signs: 1EN, 1KAM, 6KAM, 7KAM, 8KAM, 9KAM, A, ANŠE.KUR.RAM, AŠ, AḪI.A, BE, EZEN₄ḪI.A, Fda, Fta, Fḫa. These are real, legitimate determinative/marker categories outside the small list CLAUDE.md happened to name (e.g. MUNUS "woman", M/F personal-name markers, KAM ordinal markers, ḪI.A/MEŠ plural markers) — extending the vetted list is a deliberate follow-up decision, not something this export makes unilaterally.

**CTH titles**: sourced from `Archive/p25_out/cth_titles.csv` (CATALOG_METADATA; the already-fetched hethport.uni-wuerzburg.de/CTH/ catalogue snapshot, not re-fetched here). All 19 fragments' CTH titles were found.

**No machine translation.** Sumerogram words are labeled as such (`is_sum`, a structural fact) with no English gloss attached — a real logogram-gloss curation pass needs a citable reference (CHD/HZL) this export does not have. No Hittite sentence or word is translated anywhere in this output.

## Exact gap location export

`Phase3/demo_out/gap_locations_data.js`: exact word(s)/decomposed-sign(s) for **28/28** packets. Computed from `Phase1_pipeline/p4_out/decomposed_corpus.parquet` (now carrying `word_index_in_line`, added in `lib/decompose_corpus.py` specifically for this — it increments on every `<w>` start and resets on every `<lb>`, verified to match `Archive/scripts/02_parse.py`'s own `word_index_in_line` exactly, the same counter corpus.parquet's word grouping already uses). Every entry was verified end-to-end: the restored/SPECIALS-filtered stream this reads is checked token-for-token against `lib/hittite_tokenizer.encode_fragment_window()`, and the resulting left/right context is checked token-for-token against the packet's own (independently probe-computed) `left_context`/`right_context`. A packet is only included if both checks pass exactly; the 0 that don't are omitted here rather than guessed, and the fragment panel falls back to line-only highlighting for those.
