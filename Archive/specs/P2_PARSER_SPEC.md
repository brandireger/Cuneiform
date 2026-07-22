# P2_PARSER_SPEC.md — Parser + Dataset Builder Contract

Implementation happens locally (Claude Code). This spec is the design
authority for Phase 2; deviations get flagged, not improvised.
Inventory findings (inventory_out/, 2026-07) supersede all prior
schema assumptions and answer CLAUDE.md open questions 1–4 as follows:
(1) schema = AOxml per below; (2) joins = 866 merged docs, un-join to
recover pairs, pooled training / separate eval stands; (3) provincial
≈ 200 docs → eval-only; (4) duplicates derived via shared CTH folder.
Update CLAUDE.md accordingly.

## Verified schema facts (from inventory + samples)

- Root `<AOxml>`; header `<AOHeader><docID>`; body
  `<div1 type="transliteration"><text xml:lang=...>`.
- CTH label = parent folder name `CTH ###_XML`. 662 compositions,
  100% coverage. THIS is the composition label; in-body CTH strings
  are unreliable (530 docs only).
- `<AO:Manuscripts><AO:TxtPubl>` lists members; joined docs use
  sigla: `KBo 64.15 {€1} + KUB 7.38 {€2}`.
- Lines: `<lb txtid=.. lnr=.. lg=.. cu=..>` (384k). `lnr` encodes
  side (Vs./Rs. = obverse/reverse), optional column (Roman), line
  number, prime ′ (= numbering counted from a break), and for joined
  docs a sigla block like `{€2+1}` plus slash-separated per-member
  numbering. `lg` = per-line language (Hit/Akk/Hat/...). `cu` =
  Unicode cuneiform with ▒ at damaged sign positions.
- Words: `<w>` with text content = hyphenated sign transliteration.
  Child/inline elements: `<sGr>` Sumerogram, `<aGr>` Akkadogram,
  `<d>` determinative, `<num>` numeral, `<c type="sign">`.
  Attributes: `trans` (normalized form), `mrp0sel` (selected
  analysis; "DEL" = word in broken context), `mrp1..mrp9`
  (candidate analyses `lemma@gloss@morph@paradigm`).
- Damage markup (state machine, NOT brackets):
  - `<del_in/>` opens a broken-away span; `<del_fin/>` closes it.
    Text inside an open del-span = editor-restored/lost (the
    logical equivalent of [...]). Spans cross word and line
    boundaries; parser must carry state across both.
  - `<laes_in/>`/`<laes_fin/>` = damaged-but-legible (⸢...⸣);
    treat as ATTESTED (damaged), not restored.
  - `x` as a word/sign = illegible traces (attested-illegible).
  - `<gap>` = lost content; `gap@t="line"` = missing line(s);
    `gap@c` strings like "Vs. bricht ab" / "Rs. bricht ab" are
    TOP/BOTTOM EDGE EVENTS. `(Rasur)` = erasure, not a break.
  - `<corr c=..>` editorial correction/uncertainty flags.
  - `<parsep/>` paragraph divider; `<space c=N>` physical blank
    width (column-offset signal).
- VALIDATION ORACLE: per line, the ▒ positions in `lb@cu` must
  correlate with the del/laes state of that line's signs. Implement
  `validate_damage_states()` computing agreement; report
  distribution; investigate systematic disagreement before
  proceeding. Target: high agreement on a 500-line sample.

## Deliverable 1 — `02_parse.py` → `corpus.parquet` (or JSONL)

One row per WORD-TOKEN with: doc_id, cth (int), site (prefix map +
"unknown"), member_siglum (€n or null), side, column, line_label,
line_index_in_doc, line_lang, word_index_in_line, surface_translit,
signs (list, hyphen-split), trans, word_class flags (sum/akk/det/num/
syllabic), damage_state per sign (attested | laes | restored |
illegible_x), mrp_selected, mrp_lemma_candidates (list of lemmas
only), space_offset_before, paragraph_index, corr_flags.
Plus a doc-level table: doc_id, cth, member list, line count,
attested-sign count, restored-sign fraction, parse status.
229 parse errors and unknown prefixes: emit `parse_errors.csv` and
`unknown_prefixes.csv` (prefix, count, 3 example docIDs) — never
silently drop.

## Deliverable 2 — `03_unjoin.py` → join ground truth

For the 866 multi-member docs: verify sigla semantics FIRST on ~20
full docs (hypothesis: `{€2+1}` = line attested in both members;
slash-separated lnr = per-member numbering; single-siglum lines
belong to one member). Report findings in `unjoin_semantics.md`
with confidence, THEN implement:
- Reconstruct per-member pseudo-fragments (each member's line set
  with its own numbering; shared lines duplicated to both members
  with overlap flagged).
- Emit `join_pairs.jsonl`: member_a, member_b, parent_doc, cth,
  n_shared_lines, junction geometry where recoverable (which edge:
  horizontal within-line vs vertical across-lines).
- Emit `join_stats.md`: pair count, members-per-doc histogram,
  overlap-line stats. If semantics resist confident recovery for a
  subset, quarantine those docs into an "ambiguous" list — they are
  excluded from eval positives, documented, and counted.

## Deliverable 3 — `04_edges.py` → fragment edge profiles

Per fragment (standalone doc or reconstructed member): left/right
break profile per line (del state at line start/end + space offsets
+ ▒ positions), top/bottom events (gap "bricht ab", prime ′
numbering on first/last preserved lines, gap t="line"), and a
compact silhouette summary. Output `edges.parquet`.

## Deliverable 4 — `05_splits.py` → leakage-safe splits

- Unit of splitting = CTH composition. ALL docs (and all
  reconstructed members) of one composition land in exactly one of
  train/dev/test (80/10/10). Joined-doc members automatically
  co-travel (same doc, same CTH).
- Stratify by composition size band and genre band (CTH number
  ranges approximate genre; document the banding used).
- Provincial-site docs (HKM/Or/KuSa/KuT/Msk/RS/AT): mark
  `cross_site_eval=True`; they may appear in train ONLY for the
  main-split experiments, and are the held-out set for the
  train-Hattusa/test-provincial experiment — implement both split
  variants, clearly named.
- Log seed, git commit, corpus version (0.2.0-beta), and counts to
  `splits.json` + `split_report.md`.

## Cleanroom enforcement (restate; applies to all deliverables)

Two renderings per fragment, computed once here: FULL (everything,
train-time use) and ATTESTED (del-span content removed, laes kept,
x kept as mask token; mrp of restored words excluded). Test-set
evaluation consumes ATTESTED only. The restored-content delta is
the leakage-ablation lever — preserve both renderings in the
corpus table, do not fork datasets later.

## Acceptance checks (run + report before Phase 3)

1. Word-token count within ~10% of 1.52M `<w>` elements; line count
   ≈ 384k. Explain deviations.
2. damage-state oracle agreement reported.
3. ≥ 90% of the 866 joined docs successfully un-joined or
   explicitly quarantined with reasons.
4. Zero composition-leakage across splits (assert programmatically).
5. `dataset_report.md`: per-split fragment/composition/pair counts,
   attested-vs-restored sign totals, per-site counts, top-20
   largest compositions (witness counts), and 5 sample fragments
   rendered FULL vs ATTESTED side-by-side for human sanity check.

Small artifacts (all .md/.csv/.json reports above) go back to the
browser-Claude session; parquet/JSONL stay local.
