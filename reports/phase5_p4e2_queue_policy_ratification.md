# Phase 5 — P4-E2 queue-policy ratification

**Decided 2026-07-31 by Ixca.** Closes handoff item 2. Policy record:
`configs/p4e2_queue_policy.json`. Queue policy version
`contentful_sequence_length_v1` → **`contentful_sequence_length_v2`**.

| rule | decision |
|---|---|
| contentless-sequence exclusion | **RATIFIED**, with the character set widened |
| minimum sequence length 2 | **UNRATIFIED, DEFERRED** to the second queue |

The two were presented together as a pair since P4-E2. Measuring them
separately showed they are not comparable, which is why they got different
answers.

## The measurement that separated them

**Contentless exclusion is load-bearing.** With the rule off, **21 of the 60
visible same-language clusters (35%)** and **16 of 60 cross-language** become
runs of `x` and `_`, displacing that many real clusters out of view. The
ranking makes it worse than it sounds: order is sequence-length descending, so
*longer* placeholder runs rank *higher*. The top item in the queue would be
`_ _ _ _ _ _ _ _ _ _ _ _` — twelve underscores across one document. All 58
distinct contentless sequences are placeholder variants; `x` alone covers
108,109 occurrences.

**Minimum length 2 is currently a no-op.** Rebuilding with
`--min-sequence-length 1` grows the eligible pool from 2,897 to 4,441 and
leaves the queue content hash **byte-identical**
(`3e4e66ea8d7796739901d379b8bb86cc1cb130c7b19226b7857f2a70ae432bee`). The 60
clusters a specialist sees do not change by one entry, because single-sign
clusters sort to the bottom of a 4,441-cluster pool under length-descending
ranking. **What actually excludes them is the ranking and the payload bound,
not this rule.** Ratifying or rejecting it would have changed nothing.

## A correction made during the analysis

I first eyeballed the rare single-sign tail and reported it as editorial
apparatus. That was wrong — I was reading an alphabetically sorted sample,
which put every punctuation-leading token (`'i`, `(?)`, `:a`, `_bu`) at the
top.

Sorted by frequency, the rare tail is **79.1% plain sign readings**: 468 of the
592 same-language single-sign clusters with ≤2 documents, largely Sumerograms
— `numun` (seed), `kalam` (land), `géštug`, `ereš`, `naga`, `ḫabrud`, `gišnú`
(bed), `giškim` (omen), `ibila` (heir), `gišgigir` (chariot), `iku`, `i₇`
(river).

So the rule's stated justification — *specificity beats recurrence* — holds
for the Zipfian floor (`a` across 3,542 documents) but does **not** describe
its rare tail. Those 468 clusters are specific; they are unreachable for a
different reason.

## What was ratified: the widened character set

The line drawn is **the editor's apparatus is contentless; anything that could
have been on the tablet is not.**

Derived empirically rather than guessed: every distinct cluster sequence
containing no alphabetic character was enumerated (45 of 4,087) and
classified. The additions are exactly the apparatus half.

| added | why |
|---|---|
| `…` (U+2026) | indeterminate-lacuna ellipsis |
| `?` | uncertainty mark |
| `!` | editorial correction |
| `=` | markup |
| `〈` `〉` (U+2329/U+232A) | empty editorial insertion brackets |
| `}` | stray brace |
| `̣` (U+0323) | bare combining dot below, seen attached to ellipsis runs |

**Deliberately kept, and this is the part that mattered:**

- **Digits.** `10` occurs alone in **81 documents** and `d 10` in **70** — that
  is the Storm God with a damaged determinative, and `30` is the Moon God. A
  numeral is content. Excluding digits would have silently deleted divine
  names from expert review.
- **U+12471**, the cuneiform vertical-colon punctuation sign — a mark the
  scribe actually made, not an editor's note about it.
- **`×`**, which belongs to compound sign names such as `SI×SÁ`.

**Safety invariant.** A real reading always contains a letter, and the only
letter in the set is the illegible placeholder `x`. Verified: **0** excluded
sequences contain a non-`x` letter. Asserted in tests rather than left to
inspection.

**Effect.** 26 clusters / 277 occurrences newly excluded across both channels.
The visible top 60 does not change today — the first apparatus cluster sits at
rank 313 of 2,897. The value is that apparatus is now excluded *on the grounds
that it is apparatus*, independently of the deferred minimum-length rule that
had been incidentally catching most of it.

## A homoglyph near-miss, now permanently guarded

The corpus uses U+2329/U+232A angle brackets. U+3008/U+3009 are visually
identical CJK characters that occur in it **zero** times. The first draft of
the test suite pasted the wrong pair — the rule looked correct and caught
nothing.

The character set is now pinned **by codepoint** in
`test_the_character_set_is_pinned_by_codepoint`, and a companion test asserts
the CJK homoglyphs are absent. This class of bug fails silently and survives
code review, because the two strings render identically.

## Why the minimum-length rule was deferred rather than decided

Ratifying it would assert that single signs are uninteresting, which the data
contradicts. Rejecting it would change nothing, since the ranking already
suppresses them. Both answers would be theatre.

The real question is **whether those 468 rare single-sign clusters should be
reviewed**. If yes, the answer is not relaxing this rule but a **second queue
ranked by rarity rather than by length** — the same build the P4-E2 report
already anticipates for the ~13,900 ungrouped occurrences. That is where the
decision has consequences, and that is where it now sits.

The rule stays at 2 in the meantime, recorded as `UNRATIFIED_DEFERRED`. It is
inert, so leaving it in costs nothing and it guards the case where the ranking
or payload bound later changes.

## Implementation

`configs/p4e2_queue_policy.json` is the ratification record, following the
`configs/p2e9_cross_line_calibration.json` pattern. The export **reads its
rules from it** and fails closed on a missing record or an unknown status —
a queue whose rules cannot state whether they were ratified is exactly what
this record prevents.

Per-rule status travels into the manifest as `selection_rule_status` and onto
the screen: the workbench now tags the contentless exclusion **ratified** and
the minimum-length rule **awaiting ratification — deferred**. It previously
said both were unratified, which is now false. `ruleStatusLabel()` reads the
manifest, so the page cannot claim a rule was ratified when the record says
otherwise.

The queue policy name is versioned to `v2` because a changed selection rule
changes the queue an expert worked from, and a reader of their annotations
needs to be able to tell which queue produced them.

## Not ratified by this record

`max_clusters_per_channel` (60), `max_members_displayed_per_cluster` (12), the
ranking, and `context_lines_per_side` (2) are all still unratified parameters,
listed as such in the record so nobody mistakes this for a blanket approval of
the queue's construction.

## Side finding, logged not acted on

28 of the 2,897 kept same-language clusters (1.0%) contain editorial apparatus
*inside* an otherwise contentful sequence — `'7 zeichen'` (German, "7 signs"),
`'? ? ?'` before this change, `'(traces)'`, `'colophon'`, `'(unbeschrieben)'`.
These reach the visible queue. That is **extraction data quality**, not queue
policy: German editorial notes should arguably not be in the token stream at
all. Logged for the extraction, not fixed here.

## Validation

```powershell
python -m unittest discover -s tests                  # 289 pass (was 274)
ruff check lib scripts tests demo                     # clean
python lib/contracts.py                               # 20/20
python scripts/p4d_stamp_stale_reports.py --check     # exit 0
git diff --check                                      # clean
python scripts/phase4_workbench_review_export.py      # rebuild under v2
```

Visible queue content hash unchanged: `3e4e66ea…`. The eligible pool moves
2,897 → 2,895 same-language and is unchanged cross-language.
