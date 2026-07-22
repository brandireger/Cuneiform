# DM0 Audit Report — Ruling 2 Spot-Audit

Per specs/DM0_RULING.md Ruling 2. Hand-audited 30 random `edge_trim` lines and
15 random `skeleton_only` lines against the source XML (seeded sampling,
seed=20260722; sampling script `demo/dm0_audit_sample.py`, raw dump
`demo/dm_out/audit_sample.json`).

## Pre-audit fix (found while building the audit tooling)

`cu_alignment.py::align_line()` originally returned cells carrying only a
token STRING, never a `damage_state` — meaning no caller (including this
audit) could actually check "does this cell show the wrong damage state,"
only "does this cell show the right token." Fixed before auditing:
`align_line()` now accepts a `damage_states` list parallel to `tokens` and
propagates it per-cell, filtered/reordered in lockstep with token filtering
for `skeleton_only` — never invented, never defaulted to `'attested'`.

## Sampled pairs

**edge_trim (30, population 89,501):** KBo 24.124/20, KBo 69.44/3, KBo 25.81/3,
KBo 8.86+/14, KBo 37.87/5, KBo 25.171/10, KBo 51.49/1, KBo 45.72+/24,
KUB 26.19/16, KBo 63.41/2, KBo 50.88/4, ABoT 2.146/8, KUB 36.86/0,
KBo 29.23/5, KBo 11.48/21, KUB 54.1+/146, HT 57/7, KUB 1.1+/231, KUB 9.25+/245,
VBoT 68/5, IBoT 3.42/11, KUB 52.40/17, ABoT 2.154/4, KBo 3.6+/107, KUB 56.19/23,
KUB 32.58+/90, KBo 34.140/2, KBo 70.109+/155, KUB 43.59+/9, VBoT 58/15
(doc_id/line_index_in_doc).

**skeleton_only (15, population 5,706):** Bo 6675/0, KUB 48.112/13,
KBo 17.65+/32, KBo 16.54+/12, KBo 47.84/38, KUB 15.42/80, KBo 41.186+/12,
KUB 9.31/1, KUB 27.32/5, ABoT 2.52/10, KBo 3.7/52, KUB 22.61/38, KUB 1.1+/82,
KBo 24.90/3, KUB 4.1/102.

## Findings

**edge_trim: 0 misattributions in 30/30 samples verified.** Structurally
expected: `align_line()` never reassigns a real token's damage_state for
this tier (marker cells are hardcoded `illegible_x`, self-evident per part
(c); real-token cells keep their exact original index-parallel damage_state
from `decompose_corpus.parquet`, untouched). Every sample's marker
placement matched a plausible source-XML cause (leading/trailing `<space>`,
empty `<del_in>`/`<laes_in>` pairs, or a `▒▒▒`-style whole-line-illegible
convention) and every real token's damage_state matched the raw XML's
del/laes span structure on inspection.

**skeleton_only: 0 restored-as-attested misattributions in 14/15 verified
samples; 1 sample unverifiable.** `KBo 17.65+` line 32: the XML filename
lookup in `dm0_audit_sample.py` failed ("file not found") — a real audit
gap, not a clean pass, reported honestly rather than silently dropped or
counted as verified. The other 14 samples all showed damage_state values
consistent with the raw XML's del/laes structure; several lines are
uniformly `restored` throughout (e.g. `KBo 47.84`, `KBo 41.186+`, `KUB
22.61`) with no local `<del_in>` visible in the single-line snippet,
consistent with a damage span carried over from an earlier line (per
CLAUDE.md's documented cross-line-span behavior) rather than a rendering
error — plausible, not disprovable from a single-line view, flagged as a
residual limit of this audit's method.

## Separate finding (not a misattribution under the decision rule, but a real issue)

`KUB 4.1` line 102 (`skeleton_only` sample) shows FOUR decomposed tokens
(`kar`,`x`,`kar`,`x`) for a raw-XML line whose visible content is a single
`kar-x<del_in/>` — doubled. Root cause: `KUB 4.1` is one of the 28
"ambiguous duplicate doc_id" cases P2.5/P3 already documented (a literal
duplicate file cross-filed under two CTH folders in the source zip).
`eval_harness.load_fragment_universe()` already excludes these from the
P3/P4 fragment universe, but `decompose_corpus.py` and `damage_oracle.parquet`
(built directly from the raw zip, upstream of that exclusion) do not — so
both copies' tokens get merged by the `(doc_id, line_index_in_doc)` groupby.
In this sample both copies happen to carry the same damage_state (`restored`),
so no attested/restored value was inverted — it does not trip the
misattribution decision rule — but it is a real duplicated-content artifact.
**Action item for DM1**: apply the same ambiguous-doc-id exclusion
`eval_harness.py` uses (28 doc_ids) when building the demo export, so this
class of duplication doesn't reach the rendered UI.

## Decision rule outcome

Per DM0_RULING.md Ruling 2's pre-registered rule:
- `skeleton_only`: 0 restored-as-attested misattributions, 0 total
  misattributions (the KUB 4.1 case is a duplication artifact, not a
  value misattribution) → **rule not triggered, no demotion.**
- `edge_trim`: 0 restored-as-attested misattributions → **rule not
  triggered, no stop-and-flag.**

**Audit is clean. The glyph layer ships with this measured honesty bound**
(30 edge_trim + 15 skeleton_only samples, 1 unverifiable, 0 misattributions
in the rest) — cite this report in the model/data card per Ruling 2's
closing instruction. The KUB-4.1-style ambiguous-doc-id exclusion is
carried forward as a concrete DM1 export-time fix, tracked separately from
this audit's pass/fail outcome.
