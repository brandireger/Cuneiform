# Evidence Policy Implementation Specification

Status: proposed, reversible Phase 2 infrastructure change.

## Deliverables

Create:

- `lib/evidence_policy.py`
- `configs/evidence_policies.yaml`
- `specs/EVIDENCE_POLICY.md` (this specification, adapted as needed)
- `tests/test_evidence_policy.py`
- a small manifest writer integrated into the next new probe, not retrofitted across every historical script in the first commit.

## Python interface

Recommended minimal API:

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

@dataclass(frozen=True)
class EvidencePolicy:
    name: str
    allowed: frozenset[EvidenceClass]
    explicitly_denied_fields: frozenset[str] = frozenset()

class EvidencePolicyError(RuntimeError):
    pass

def validate_fields(
    fields: Iterable[str],
    registry: Mapping[str, FieldEvidence],
    policy: EvidencePolicy,
) -> Sequence[FieldEvidence]:
    """Return classifications or fail closed on unknown/prohibited fields."""
```

## Fail-closed rules

`validate_fields()` must raise when:

- a requested field is absent from the registry;
- a field belongs to a disallowed evidence class;
- a field is explicitly denied, even when its broad class is allowed;
- a derived feature has no recorded dependency lineage.

No wildcard approval for unknown dataframe columns.

## Derived-feature lineage

Derived features need recursive dependencies:

```yaml
features:
  attested_sign_bigrams:
    class: EDITORIAL_TRANSCRIPTION
    depends_on: [sign_attested]
    transform: sign_bigram_v1
  edge_damage_ratio:
    class: OBSERVED_DOCUMENT_STRUCTURE
    depends_on: [sign_damage_states]
    transform: edge_damage_ratio_v1
```

A derived feature’s effective evidence class is at least as interpretive as its most interpretive dependency. Manual override toward a less interpretive class is prohibited.

## Initial registry decisions

These are starting classifications and must be checked against actual parser output:

- `doc_id`, internal row IDs, split labels: `SYSTEM_TECHNICAL`.
- `sign_damage_states`: likely `OBSERVED_DOCUMENT_STRUCTURE`, with a rationale noting that it is parsed from editorial markup representing preservation state.
- `sign_attested`, attested transliteration token streams: `EDITORIAL_TRANSCRIPTION`, not unqualified `OBSERVED_ARTIFACT`.
- restored sign streams: `EDITORIAL_RESTORATION`.
- `cu`: `EDITORIAL_RESTORATION` or explicit deny; never cleanroom-safe input.
- CTH, publication series, site, folder path: `CATALOG_METADATA`.
- plus-join labels, duplicate labels, witness alignment: `EDITORIAL_RELATION`.
- generated continuation, embedding, pseudo-label: `MODEL_DERIVED`.
- `<parsep>`, `<clb>`, line number/order, structural gaps/spaces: `OBSERVED_DOCUMENT_STRUCTURE`, subject to parser verification.

## Standard policies

```yaml
policies:
  artifact_strict:
    allow:
      - OBSERVED_ARTIFACT
      - OBSERVED_DOCUMENT_STRUCTURE
      - SYSTEM_TECHNICAL
    deny_fields:
      - cu

  transcription_assisted:
    allow:
      - OBSERVED_ARTIFACT
      - OBSERVED_DOCUMENT_STRUCTURE
      - EDITORIAL_TRANSCRIPTION
      - SYSTEM_TECHNICAL
    deny_fields:
      - cu

  catalog_assisted:
    allow:
      - OBSERVED_ARTIFACT
      - OBSERVED_DOCUMENT_STRUCTURE
      - EDITORIAL_TRANSCRIPTION
      - CATALOG_METADATA
      - SYSTEM_TECHNICAL
    deny_fields:
      - cu

  scholar_assisted:
    allow:
      - OBSERVED_ARTIFACT
      - OBSERVED_DOCUMENT_STRUCTURE
      - EDITORIAL_TRANSCRIPTION
      - EDITORIAL_RESTORATION
      - CATALOG_METADATA
      - SYSTEM_TECHNICAL
    deny_fields:
      - cu

  discovery_assisted:
    allow:
      - OBSERVED_ARTIFACT
      - OBSERVED_DOCUMENT_STRUCTURE
      - EDITORIAL_TRANSCRIPTION
      - EDITORIAL_RESTORATION
      - CATALOG_METADATA
      - MODEL_DERIVED
      - SYSTEM_TECHNICAL
    deny_fields:
      - cu
```

`EDITORIAL_RELATION` is omitted from ordinary feature policies because it is normally a label or evaluation relation. A specialized, clearly named diagnostic policy may permit it, but such results are never clean evaluation.

## Tests

At minimum:

1. unknown field raises;
2. `cu` raises in every standard policy;
3. restoration field raises under strict and transcription-assisted modes;
4. catalog field raises under strict/transcription-assisted modes;
5. model-derived field raises outside discovery mode;
6. derived feature inherits the strongest dependency class;
7. manifest lists all consumed fields and classes;
8. policy behavior is deterministic;
9. semantic fields cannot be accessed by an unregistered alias;
10. technical IDs are permitted for joins/control flow but rejected if passed into a semantic feature matrix.

## Scope control

First commit should add infrastructure and apply it to one new Phase 2 probe. Do not refactor every historical script at once. Historical reports remain immutable; future promoted measurements must use the policy system.
