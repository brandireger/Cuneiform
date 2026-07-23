"""lib/evidence_policy.py -- provenance-first evidence-policy
infrastructure, per specs/EVIDENCE_POLICY.md (adapted from expert
advisory input, cuneiform_expert_patch/, 2026-07-22).

Every semantic field consumed by a scorer/model must be registered
with an EvidenceClass. validate_fields() fails closed: unknown fields,
disallowed classes, and explicitly denied fields all raise
EvidencePolicyError rather than defaulting to permit. This is the same
"hard contract at ingress, not a defaulting lookup" shape as
lib/contracts.py -- deliberately, since a permissive .get()-style
default is exactly the mechanism that hid E2 for an entire phase (see
reports/p5c_report.md).

Do not add a wildcard/permissive fallback here. An assert that can be
silently bypassed protects nothing.
"""
import hashlib
import json
import subprocess
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml


class EvidenceClass(str, Enum):
    OBSERVED_ARTIFACT = "OBSERVED_ARTIFACT"
    OBSERVED_DOCUMENT_STRUCTURE = "OBSERVED_DOCUMENT_STRUCTURE"
    CATALOG_METADATA = "CATALOG_METADATA"
    EDITORIAL_TRANSCRIPTION = "EDITORIAL_TRANSCRIPTION"
    EDITORIAL_RESTORATION = "EDITORIAL_RESTORATION"
    EDITORIAL_RELATION = "EDITORIAL_RELATION"
    MODEL_DERIVED = "MODEL_DERIVED"
    SYSTEM_TECHNICAL = "SYSTEM_TECHNICAL"


# Interpretive order, least -> most interpretive/restrictive. Used to
# resolve a derived feature's effective class as the most interpretive
# of itself and its full dependency closure (specs/EVIDENCE_POLICY.md
# "Derived-feature lineage"). EDITORIAL_RELATION and MODEL_DERIVED sit
# at the top: a feature touching either is never "downgraded" by an
# override.
_INTERPRETIVE_ORDER = [
    EvidenceClass.SYSTEM_TECHNICAL,
    EvidenceClass.OBSERVED_ARTIFACT,
    EvidenceClass.OBSERVED_DOCUMENT_STRUCTURE,
    EvidenceClass.CATALOG_METADATA,
    EvidenceClass.EDITORIAL_TRANSCRIPTION,
    EvidenceClass.EDITORIAL_RESTORATION,
    EvidenceClass.EDITORIAL_RELATION,
    EvidenceClass.MODEL_DERIVED,
]
_RANK = {c: i for i, c in enumerate(_INTERPRETIVE_ORDER)}


def _more_interpretive(a: EvidenceClass, b: EvidenceClass) -> EvidenceClass:
    return a if _RANK[a] >= _RANK[b] else b


class EvidencePolicyError(RuntimeError):
    """Raised on any fail-closed violation: unknown field, disallowed
    class, explicitly denied field, or unresolvable dependency lineage."""


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
    explicitly_denied_fields: frozenset[str] = dc_field(default_factory=frozenset)


# ---------------------------------------------------------------- loading

def load_registry(path: str | Path = "configs/evidence_registry.yaml"
                   ) -> Mapping[str, FieldEvidence]:
    """Loads the field registry from YAML. Raises EvidencePolicyError if
    any field's depends_on references a field not itself in the
    registry (no dangling lineage -- fail closed at load time, not at
    first use)."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    registry: dict[str, FieldEvidence] = {}
    for name, spec in raw.get("fields", {}).items():
        try:
            cls = EvidenceClass(spec["class"])
        except (KeyError, ValueError) as e:
            raise EvidencePolicyError(
                f"load_registry: field '{name}' has missing/invalid 'class': {e}") from e
        depends_on = tuple(spec.get("depends_on", []) or [])
        registry[name] = FieldEvidence(
            field=name, evidence_class=cls,
            rationale=spec.get("rationale", ""),
            source_path=spec.get("source_path"),
            depends_on=depends_on,
        )

    for name, entry in registry.items():
        for dep in entry.depends_on:
            if dep not in registry:
                raise EvidencePolicyError(
                    f"load_registry: field '{name}' depends_on unregistered "
                    f"field '{dep}' -- no dangling dependency lineage allowed.")

    return registry


def load_policy(name: str, path: str | Path = "configs/evidence_policies.yaml"
                 ) -> EvidencePolicy:
    """Loads a named policy from YAML. Raises EvidencePolicyError if the
    named policy doesn't exist."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    policies = raw.get("policies", {})
    if name not in policies:
        raise EvidencePolicyError(
            f"load_policy: unknown policy '{name}'; known policies: "
            f"{sorted(policies.keys())}")
    spec = policies[name]
    allowed = frozenset(EvidenceClass(c) for c in spec.get("allow", []))
    denied = frozenset(spec.get("deny_fields", []) or [])
    return EvidencePolicy(name=name, allowed=allowed, explicitly_denied_fields=denied)


# ---------------------------------------------------------------- lineage

def effective_class(field: str, registry: Mapping[str, FieldEvidence],
                     *, _seen: frozenset[str] | None = None) -> EvidenceClass:
    """A field's effective evidence class: the most interpretive class
    among itself and the full transitive closure of its dependencies.
    Raises EvidencePolicyError on an unregistered field or a dependency
    cycle."""
    if field not in registry:
        raise EvidencePolicyError(f"effective_class: field '{field}' not in registry.")
    seen = _seen or frozenset()
    if field in seen:
        raise EvidencePolicyError(f"effective_class: dependency cycle involving '{field}'.")
    entry = registry[field]
    result = entry.evidence_class
    for dep in entry.depends_on:
        dep_class = effective_class(dep, registry, _seen=seen | {field})
        result = _more_interpretive(result, dep_class)
    return result


# ---------------------------------------------------------------- validation

def validate_fields(fields: Iterable[str], registry: Mapping[str, FieldEvidence],
                     policy: EvidencePolicy) -> Sequence[FieldEvidence]:
    """Returns the FieldEvidence for each requested field (with its
    EFFECTIVE, lineage-resolved class), or raises EvidencePolicyError
    fail-closed on the first violation:
      - field absent from the registry;
      - field explicitly denied by this policy (checked before the
        class check -- denial always wins, even if the class is allowed);
      - field's effective class not in this policy's allowed set.
    No wildcard approval for unknown fields. Technical IDs (SYSTEM_TECHNICAL)
    are valid for control flow but this function makes no exception for
    them being passed into a semantic feature matrix -- callers must
    request only fields meant to be model features."""
    out = []
    for name in fields:
        if name not in registry:
            raise EvidencePolicyError(
                f"validate_fields[{policy.name}]: field '{name}' is not in the "
                f"registry. Unknown fields are rejected, never silently permitted.")
        if name in policy.explicitly_denied_fields:
            raise EvidencePolicyError(
                f"validate_fields[{policy.name}]: field '{name}' is explicitly "
                f"denied by this policy, regardless of its evidence class.")
        eff = effective_class(name, registry)
        if eff not in policy.allowed:
            raise EvidencePolicyError(
                f"validate_fields[{policy.name}]: field '{name}' has effective "
                f"class {eff.value}, not permitted by policy '{policy.name}' "
                f"(allowed: {sorted(c.value for c in policy.allowed)}).")
        entry = registry[name]
        out.append(FieldEvidence(field=name, evidence_class=eff,
                                  rationale=entry.rationale,
                                  source_path=entry.source_path,
                                  depends_on=entry.depends_on))
    return out


def validate_semantic_features(fields: Iterable[str], registry: Mapping[str, FieldEvidence],
                                policy: EvidencePolicy) -> Sequence[FieldEvidence]:
    """Like validate_fields(), but ADDITIONALLY rejects SYSTEM_TECHNICAL
    fields unconditionally -- even though every standard policy's
    `allowed` set includes SYSTEM_TECHNICAL (row IDs are needed for
    joins/control flow, per configs/evidence_policies.yaml), a
    technical identifier must never be passed into a semantic model
    feature matrix. Use validate_fields() for control-flow/bookkeeping
    contexts (e.g. joining a score back onto a fragment_id); use THIS
    function immediately before constructing model input."""
    out = validate_fields(fields, registry, policy)
    technical = [fe.field for fe in out if fe.evidence_class == EvidenceClass.SYSTEM_TECHNICAL]
    if technical:
        raise EvidencePolicyError(
            f"validate_semantic_features[{policy.name}]: SYSTEM_TECHNICAL field(s) "
            f"{technical} requested as semantic features -- technical identifiers "
            f"are permitted for control flow/joins only, never as model input.")
    return out


# ---------------------------------------------------------------- manifest

def _git_commit() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                 text=True, check=True)
        return result.stdout.strip()
    except Exception as e:  # noqa: BLE001
        return f"N/A: {e}"


def _hash_file(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        return "N/A: file not found"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def build_manifest(*, task: str, evidence_policy: str, features_requested: Sequence[str],
                    registry: Mapping[str, FieldEvidence], policy: EvidencePolicy,
                    dataset_manifest_path: str | Path | None = None,
                    split_manifest_path: str | Path | None = None,
                    config_path: str | Path | None = None,
                    seed: int | None = None,
                    corpus_version: str = "TLHdig 0.2.0-beta",
                    declared_statistics_universe: str = "") -> dict:
    """Validates features_requested against (registry, policy) -- raises
    on the first violation, fail-closed, per validate_fields(). On
    success, returns the manifest dict per EXPERT_OPINION.md section 4.
    A manifest is only ever produced for a field set that already
    passed validation; there is no path to a manifest describing a
    run that used a prohibited field silently. Uses
    validate_semantic_features() (not the more permissive
    validate_fields()), since a manifest describes what went into
    model input -- SYSTEM_TECHNICAL fields must not appear here even
    though they're policy-"allowed" for control flow elsewhere."""
    observed = validate_semantic_features(features_requested, registry, policy)
    evidence_classes_used = sorted({fe.evidence_class.value for fe in observed})

    def frac(cls: EvidenceClass) -> float | None:
        if not observed:
            return None
        n = sum(1 for fe in observed if fe.evidence_class == cls)
        return n / len(observed)

    return {
        "task": task,
        "evidence_policy": evidence_policy,
        "features_requested": list(features_requested),
        "features_observed": [fe.field for fe in observed],
        "evidence_classes_used": evidence_classes_used,
        "prohibited_features_encountered": [],
        "editorial_content_fraction": frac(EvidenceClass.EDITORIAL_TRANSCRIPTION),
        "restored_content_fraction": frac(EvidenceClass.EDITORIAL_RESTORATION),
        "model_derived_content_fraction": frac(EvidenceClass.MODEL_DERIVED),
        "dataset_manifest_hash": _hash_file(dataset_manifest_path) if dataset_manifest_path else "",
        "split_manifest_hash": _hash_file(split_manifest_path) if split_manifest_path else "",
        "config_hash": _hash_file(config_path) if config_path else "",
        "git_commit": _git_commit(),
        "corpus_version": corpus_version,
        "seed": seed,
        "declared_statistics_universe": declared_statistics_universe,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_manifest(manifest: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
