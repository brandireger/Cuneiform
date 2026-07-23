# Evidence Policy Implementation Specification

Status: implemented, reversible Phase 2 infrastructure. Adapted from
`cuneiform_expert_patch/EVIDENCE_POLICY_SPEC.md` (expert advisory input,
2026-07-22) — see `EXPERT_OPINION.md` for the full rationale. Authority:
advisory; CLAUDE.md, PHASE2_CHARTER.md, SANDBOX_RULES.md, frozen splits,
and ratified human decisions remain controlling.

## Deliverables (this pass)

- `lib/evidence_policy.py`
- `configs/evidence_policies.yaml`
- `configs/evidence_registry.yaml`
- `specs/EVIDENCE_POLICY.md` (this file)
- `tests/test_evidence_policy.py`
- `scripts/evidence_policy_smoke.py` — a tiny standalone smoke script
  (not a full Phase 2 probe; no probe has run yet as of this pass) that
  exercises the policy against a handful of real fragments and writes
  one sample manifest.

Per the implementation request's explicit scope control: this commit
does **not** retrofit `lib/eval_harness.py`, `lib/fracture_engine.py`,
`lib/hittite_tokenizer.py`, or any historical (Phase 1) script. Those
already have their own frozen, reported numbers; changing what they
read would silently change results already written up. Retrofitting
is a `[Decision point]` for a future pass, per the implementation
request's own instruction not to do it in the first commit.

## Python interface

Implemented per the spec, with one addition (`load_registry`/
`load_policy` YAML loaders, since the original spec described the data
shapes but not how they're read from disk):

```python
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence

class EvidenceClass(str, Enum):
    OBSERVED_ARTIFACT = "OBSERVED_ARTIFACT"
    OBSERVED_DOCUMENT_STRUCTURE = "OBSERVED_DOCUMENT_STRUCTURE"
    CATALOG_METADATA = "CATALOG_METADATA"
    EDITORIAL_TRANSCRIPTION = "EDITORIAL_TRANSCRIPTION"
    EDITORIAL_RESTORATION = "EDITORIAL_RESTORATION"
    EDITORIAL_RELATION = "EDITORIAL_RELATION"
    MODEL_DERIVED = "MODEL_DERIVED"
    SYSTEM_TECHNICAL = "SYSTEM_TECHNICAL"

@dataclass(frozen=True)
class FieldEvidence:
    field: str
    evidence_class: EvidenceClass
    rationale: str
    source_path: str | None = None
    depends_on: tuple[str, ...] = ()

@dataclass(frozen=True)
class EvidencePolicy:
    name: str
    allowed: frozenset[EvidenceClass]
    explicitly_denied_fields: frozenset[str] = frozenset()

class EvidencePolicyError(RuntimeError):
    pass

def validate_fields(fields, registry, policy) -> Sequence[FieldEvidence]:
    """Return classifications or fail closed on unknown/prohibited fields."""
```

## Fail-closed rules

`validate_fields()` raises `EvidencePolicyError` when:

- a requested field is absent from the registry;
- a field belongs to a disallowed evidence class for the active policy;
- a field, or any field in its dependency closure, is explicitly denied,
  even when its broad class is allowed;
- a derived feature's recorded dependency is itself absent from the
  registry (no dependency lineage).

No wildcard approval for unknown fields, ever — this is enforced by
`validate_fields` raising rather than defaulting to permit, and by
`build_registry_from_yaml` raising if a `depends_on` entry doesn't
resolve to another registered field.

## Derived-feature lineage

`configs/evidence_registry.yaml` records `depends_on` for every derived
feature; `lib/evidence_policy.py::effective_class()` computes a
feature's effective class as the *most interpretive* class among
itself and its full dependency closure (interpretive order below).
Manual override toward a less interpretive class is rejected at
registry-load time.

Interpretive order (least -> most restrictive/interpretive), used to
resolve "most interpretive of X and Y":

```
SYSTEM_TECHNICAL
< OBSERVED_ARTIFACT
< OBSERVED_DOCUMENT_STRUCTURE
< CATALOG_METADATA
< EDITORIAL_TRANSCRIPTION
< EDITORIAL_RESTORATION
< EDITORIAL_RELATION
< MODEL_DERIVED
```

This project has no fields currently registered as bare
`OBSERVED_ARTIFACT` — see "Registry decisions and uncertainties" below;
TLHdig transliteration is editorially mediated throughout, so nothing
in the accessible corpus currently qualifies as unmediated artifact
observation. `artifact_strict` in practice permits
`OBSERVED_DOCUMENT_STRUCTURE` + `SYSTEM_TECHNICAL` on this corpus,
which is disclosed explicitly rather than silently implied.

## Registry decisions and uncertainties (verified against actual
parser output, 2026-07-22 — not the spec's original abstract examples)

Checked directly against `p2_out/corpus.parquet`, `p2_out/edges.parquet`,
`p2_out/doc_table.parquet`, `p2_out/splits.parquet`,
`p4_out/decomposed_corpus.parquet`, and
`eval_harness.load_fragment_universe()`'s rendered columns — every
field below is a real, present column, not a guess.

**High-confidence classifications** (match the expert opinion's own
named examples, or are unambiguous):

| field | source | class |
|---|---|---|
| `doc_id`, `fragment_id`, `parent_doc`, `siglum`, `member_siglum` | various | `SYSTEM_TECHNICAL` |
| `main_split`, `site_split`, `is_bin`, `parse_status` | splits/doc_table | `SYSTEM_TECHNICAL` |
| `cth`, `site`, `prefix` | corpus/doc_table | `CATALOG_METADATA` |
| `sign_damage_states`, `damage_state` (decomposed) | corpus/decomposed | `OBSERVED_DOCUMENT_STRUCTURE` — parsed from editorial markup representing preservation state, not itself a reading |
| `line_index_in_doc`, `word_index_in_line`, `paragraph_index`, `side`, `column`, `line_label`, `on_physical_edge` | corpus/edges | `OBSERVED_DOCUMENT_STRUCTURE` |
| `top_edge_lost`, `bottom_edge_lost`, `*_gap_desc`, `*_confirmed_preserved`, `preserves_left_edge`, `preserves_right_edge`, `left_edge_states`, `right_edge_states` | edges.parquet | `OBSERVED_DOCUMENT_STRUCTURE` |
| `attested_sign_count`, `restored_sign_count`, `laes_sign_count`, `illegible_sign_count`, `restored_sign_fraction`, `n_attested_signs`, `line_count`, `word_count` | doc_table/rendered | `OBSERVED_DOCUMENT_STRUCTURE` (aggregate counts over damage-state markup) |
| `space_c` | corpus.parquet | `OBSERVED_DOCUMENT_STRUCTURE` (`<space c="N"/>` blank-run width) |
| `surface_translit`, `trans`, `signs`, `sign_full`, `sign_attested`, `token` (decomposed) | corpus/rendered | `EDITORIAL_TRANSCRIPTION` — matches the expert opinion's explicit ruling that transliteration is not unqualified `OBSERVED_ARTIFACT` |
| restored sign streams (any full-vs-attested-only pair) | rendered | `EDITORIAL_RESTORATION` |
| `cu` (raw cuneiform rendering) | AOxml, not currently in any parsed parquet | `EDITORIAL_RESTORATION`, **explicitly denied in every policy** — per CLAUDE.md's own extensive prior documentation, never cleanroom-safe |
| `mrp_selected`, `mrp_lemma_candidates` | corpus.parquet | **explicitly denied in every policy** (not merely classified) — CLAUDE.md's standing rule: "morphological glossing... out of scope; do not build features off `mrp*`." This is stricter than the original spec's registry list, which didn't mention `mrp*` at all; the denial follows an existing project rule, not a new invention |
| join/duplicate/witness relation labels (`p2_out/join_pairs.jsonl` tier/join_type, `p4_out/p5_query_sets.json`'s join_by_frag/dup_by_frag) | derived | `EDITORIAL_RELATION` |
| any embedding, generated continuation, pseudo-label, D14/D17/D18 score output | model runs | `MODEL_DERIVED` |

**Flagged uncertainties — tentative classification given, explicitly
open for Ixca's review, not silently resolved:**

- `line_lang` (the per-line multilingual-layer signal, e.g. Hit/Akk/
  Hattian) — tentatively `OBSERVED_DOCUMENT_STRUCTURE` (it is the `lg`
  XML attribute, a source-encoded tag, not a free transcription
  choice). **Data-quality finding surfaced while verifying this
  field**: a sample of `line_lang` values contains malformed entries
  with leftover XML fragments (e.g. `"Hit> <w><del_in/> ... <del_fin/
  ></w"`, `"Hit> <w><note n='15' c=..."`) — a parser issue, not an
  evidence-policy issue. Not fixed here (out of this task's scope,
  and fixing the parser is exactly the kind of historical-script
  change the implementation request says not to do without asking);
  flagged for a decision on whether/when to patch `02_parse.py`.
- `is_sum`, `is_akk`, `is_det`, `is_num`, `is_syllabic`, `is_space`,
  `is_empty` — tentatively `OBSERVED_DOCUMENT_STRUCTURE` (tag-delimited
  per CLAUDE.md, `<sGr>`/`<aGr>`/`<d>`, not case-inferred), but could
  reasonably be argued `EDITORIAL_TRANSCRIPTION` since sumerogram/
  determinative identification is itself a philological judgment
  embedded in the source markup. Not resolved unilaterally.
- `corr_flags`, `reading_uncertain` — verified non-trivial content
  (`corr_flags` holds Assyriological correction markers: `?`, `!`,
  `!?`, `(?)`; `reading_uncertain` is true for 177,274/1,525,888 word
  rows). Classified `EDITORIAL_TRANSCRIPTION` (part of the editorial
  reading apparatus), not flagged uncertain, but noted here since
  neither field was named in the original spec's registry list.
- `lemma_full`, `lemma_attested` (eval_harness-rendered) — these fall
  back to `trans`/`signs` when `mrp_lemma_candidates` is empty, so
  they are a **mixed-dependency derived feature** whose most
  interpretive dependency is the denied `mrp_lemma_candidates`. Per
  this spec's own lineage rule (effective class = most interpretive
  dependency; denial cannot be overridden toward a more permissive
  class), these are registered as **denied**, consistent with
  CLAUDE.md's out-of-scope ruling on `mrp*` — flagged as a decision
  point since the original patch didn't name these two fields
  explicitly.
- `annot@editor` / `annot@date` — CLAUDE.md's corpus notes describe
  these as present in the raw AOxml ("per-edit provenance metadata...
  never use as a model feature"), but **no parsed artifact in this
  pipeline currently materializes them** (absent from `corpus.parquet`,
  `doc_table.parquet`, `edges.parquet`, and the decomposed cache). Not
  registered, because a field that isn't accessible anywhere in the
  pipeline can't be validated against real data — `validate_fields`
  would raise "absent from registry" if anything tried to request it,
  which is the correct fail-closed behavior regardless.

## Standard policies

Implemented exactly as specified (`configs/evidence_policies.yaml`),
with `cu` and `mrp_selected`/`mrp_lemma_candidates` denied in every
policy including `discovery_assisted`:

```yaml
policies:
  artifact_strict:
    allow: [OBSERVED_ARTIFACT, OBSERVED_DOCUMENT_STRUCTURE, SYSTEM_TECHNICAL]
    deny_fields: [cu, mrp_selected, mrp_lemma_candidates, lemma_full, lemma_attested]
  transcription_assisted:
    allow: [OBSERVED_ARTIFACT, OBSERVED_DOCUMENT_STRUCTURE, EDITORIAL_TRANSCRIPTION, SYSTEM_TECHNICAL]
    deny_fields: [cu, mrp_selected, mrp_lemma_candidates, lemma_full, lemma_attested]
  catalog_assisted:
    allow: [OBSERVED_ARTIFACT, OBSERVED_DOCUMENT_STRUCTURE, EDITORIAL_TRANSCRIPTION, CATALOG_METADATA, SYSTEM_TECHNICAL]
    deny_fields: [cu, mrp_selected, mrp_lemma_candidates, lemma_full, lemma_attested]
  scholar_assisted:
    allow: [OBSERVED_ARTIFACT, OBSERVED_DOCUMENT_STRUCTURE, EDITORIAL_TRANSCRIPTION, EDITORIAL_RESTORATION, CATALOG_METADATA, SYSTEM_TECHNICAL]
    deny_fields: [cu, mrp_selected, mrp_lemma_candidates, lemma_full, lemma_attested]
  discovery_assisted:
    allow: [OBSERVED_ARTIFACT, OBSERVED_DOCUMENT_STRUCTURE, EDITORIAL_TRANSCRIPTION, EDITORIAL_RESTORATION, CATALOG_METADATA, MODEL_DERIVED, SYSTEM_TECHNICAL]
    deny_fields: [cu, mrp_selected, mrp_lemma_candidates, lemma_full, lemma_attested]
```

`EDITORIAL_RELATION` is omitted from every standard policy's `allow`
list, per the original spec: it is normally a label/evaluation
relation, not a feature. No specialized diagnostic policy permitting
it is created in this pass (a `[Decision point]`, not improvised).

## Tests (`tests/test_evidence_policy.py`)

Covers all 10 cases from the original spec: unknown field raises;
`cu` raises in every standard policy; restoration field raises under
strict/transcription-assisted; catalog field raises under strict/
transcription-assisted; model-derived field raises outside discovery
mode; derived feature inherits the strongest dependency class;
manifest lists all consumed fields and classes; policy behavior is
deterministic; semantic fields cannot be accessed by an unregistered
alias; technical IDs are permitted for control flow but rejected in a
semantic feature matrix. Plus two cases specific to this corpus:
`mrp_lemma_candidates` denied in every policy including discovery;
`lemma_full`/`lemma_attested` denied via mixed-dependency lineage.
Repository-hardening regressions additionally cover explicit denial
propagating through a derived feature's dependency closure and rejection
of a manifest whose displayed policy label differs from the policy object
used for validation.

## Scope control

This commit adds infrastructure plus `scripts/evidence_policy_smoke.py`
(a standalone smoke script over real fragments, not a Phase 2 probe —
no probe has been run against this yet). No historical script was
modified. Historical reports remain immutable. Future promoted
measurements should use the policy system going forward, per Ixca's
decision on when to apply it to P2-A/P2-D or later probes.
