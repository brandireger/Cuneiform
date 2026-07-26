"""Ratified Phase 4 language-layer rules.

This module is the single implementation point for Gate 0 language
canonicalization and effective word-language resolution. Gate 1 migration and
later Gate 2 token construction must call these functions rather than
reimplementing precedence locally.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONTRACT_PATH = Path("configs/language_layers_v2.json")
MALFORMED_CHARS = re.compile(r"[<>=\"'\s]")
SOURCE_LEVELS = frozenset({"DOCUMENT", "LINE", "WORD"})
SOURCE_STATUSES = frozenset(
    {"valid", "missing", "explicit_empty", "malformed", "unrecognized"}
)
LANGUAGE_SCOPES = frozenset({
    "HITTITE_ONLY",
    "SAME_LANGUAGE_AS_QUERY",
    "MULTILINGUAL_CONDITIONED",
    "CROSS_LANGUAGE_PARALLEL",
    "ALL_LANGUAGES_UNCONDITIONED",
})


class LanguageContractError(RuntimeError):
    """Raised when the ratified language contract is missing or inconsistent."""


class LanguageScopeError(RuntimeError):
    """Raised when language behavior is omitted, ambiguous, or unsupported."""


@dataclass(frozen=True)
class LanguageValue:
    raw: str | None
    canonical: str | None
    status: str
    rule_id: str


@dataclass(frozen=True)
class EffectiveLanguage:
    canonical: str | None
    status: str
    source: str
    rule_id: str
    workbench_category: str | None = None


def load_language_contract(path=DEFAULT_CONTRACT_PATH):
    """Load and fail closed on a non-ratified or over-authorized contract."""
    path = Path(path)
    contract = json.loads(path.read_text(encoding="utf-8"))
    authorization = contract.get("authorization", {})
    if contract.get("status") != "GATE0_RATIFIED":
        raise LanguageContractError("Gate 0 language contract is not ratified")
    if not authorization.get("gate_1_migration_implementation"):
        raise LanguageContractError("Gate 1 migration is not authorized")
    if authorization.get("test_access"):
        raise LanguageContractError(
            "Gate 1 contract must not authorize protected-test access")
    if authorization.get("gpu_training"):
        raise LanguageContractError(
            "Gate 1 contract must not authorize GPU training")
    if authorization.get("training_dataset_export"):
        raise LanguageContractError(
            "Gate 1 contract must not authorize training-dataset export")

    codes = contract.get("canonical_codes", [])
    if not codes or len(codes) != len(set(codes)):
        raise LanguageContractError("Canonical language codes must be unique")
    mappings = contract.get("canonical_mappings", {})
    unknown_targets = sorted(set(mappings.values()) - set(codes))
    if unknown_targets:
        raise LanguageContractError(
            f"Canonical mappings have unknown targets: {unknown_targets}")
    if contract.get("effective_rule", {}).get("rule_id") != (
            "word_override_else_line_v2"):
        raise LanguageContractError("Unexpected effective-language rule")
    if set(contract.get("language_scopes", [])) != LANGUAGE_SCOPES:
        raise LanguageContractError(
            "Contract language scopes do not match the governed vocabulary")
    return contract


def classify_language(
        raw: str | None,
        *,
        attribute_present: bool,
        level: str,
        contract) -> LanguageValue:
    """Classify one verbatim source language attribute without guessing."""
    if level not in SOURCE_LEVELS:
        raise LanguageContractError(f"Unknown language level: {level!r}")
    if not attribute_present:
        if raw is not None:
            raise LanguageContractError(
                "Absent language attribute cannot carry a raw value")
        return LanguageValue(None, None, "missing", "attribute_absent_v2")
    if raw is None:
        raise LanguageContractError(
            "Present language attribute must preserve a string value")
    if raw == "":
        return LanguageValue(
            raw, None, "explicit_empty",
            f"explicit_empty_{level.lower()}_v2")
    if MALFORMED_CHARS.search(raw) or len(raw) > 15:
        return LanguageValue(
            raw, None, "malformed", "malformed_quarantine_v2")

    codes = set(contract["canonical_codes"])
    if raw in codes:
        return LanguageValue(raw, raw, "valid", "identity_v2")
    mappings = contract["canonical_mappings"]
    if raw in mappings:
        mapping_id = f"{raw.lower()}_to_{mappings[raw].lower()}_v2"
        return LanguageValue(raw, mappings[raw], "valid", mapping_id)
    return LanguageValue(
        raw, None, "unrecognized", "unrecognized_quarantine_v2")


def language_status_workbench_category(status):
    """Map a source-language anomaly status to its governed intake category."""
    return {
        "explicit_empty": "EMPTY_LANGUAGE_TAG",
        "malformed": "MALFORMED_LANGUAGE_TAG",
        "unrecognized": "UNRECOGNIZED_LANGUAGE_TAG",
    }.get(status)


def resolve_word_language(
        word: LanguageValue,
        line: LanguageValue,
        *,
        word_attribute_present: bool,
        contract) -> EffectiveLanguage:
    """Apply the ratified word-override/line-inheritance rule."""
    rule = contract["effective_rule"]
    rule_id = rule["rule_id"]

    if not word_attribute_present:
        if word.status != "missing":
            raise LanguageContractError(
                "Absent word attribute must have missing source status")
        spec = rule["absent_word_tag"]
        if line.status == "valid":
            return EffectiveLanguage(
                line.canonical,
                spec["effective_status"],
                spec["effective_source"],
                rule_id,
            )
        return EffectiveLanguage(
            None,
            spec["otherwise_effective_status"],
            spec["otherwise_effective_source"],
            rule_id,
        )

    if word.status == "valid":
        spec = rule["valid_explicit_word_tag"]
        return EffectiveLanguage(
            word.canonical,
            spec["effective_status"],
            spec["effective_source"],
            rule_id,
        )

    if word.status == "explicit_empty":
        spec = rule["explicit_empty_word_tag"]
        if line.status == "valid":
            return EffectiveLanguage(
                line.canonical,
                spec["effective_status"],
                spec["effective_source"],
                rule_id,
                spec["workbench_category"],
            )
        return EffectiveLanguage(
            None,
            spec["otherwise_effective_status"],
            spec["otherwise_effective_source"],
            rule_id,
            spec["workbench_category"],
        )

    if word.status in {"malformed", "unrecognized"}:
        spec = rule["malformed_or_unrecognized_word_tag"]
        category = spec["workbench_category_by_status"][word.status]
        return EffectiveLanguage(
            None,
            spec["effective_status"],
            spec["effective_source"],
            rule_id,
            category,
        )

    raise LanguageContractError(
        f"Unsupported explicit word-language status: {word.status!r}")


def validate_language_scope(scope, *, query_language=None, contract):
    """Validate an explicit projection scope and any required query language."""
    if scope is None or scope in {"auto", "default", "language_blind"}:
        raise LanguageScopeError(
            "Language scope must be explicit; defaults are prohibited")
    if scope not in LANGUAGE_SCOPES:
        raise LanguageScopeError(f"Unknown language scope: {scope!r}")
    query_scopes = {"SAME_LANGUAGE_AS_QUERY", "CROSS_LANGUAGE_PARALLEL"}
    if scope in query_scopes:
        if query_language is None:
            raise LanguageScopeError(
                f"{scope} requires a resolved query language")
        if query_language not in set(contract["canonical_codes"]):
            raise LanguageScopeError(
                f"Unresolved/unrecognized query language: {query_language!r}")
    elif query_language is not None:
        raise LanguageScopeError(
            f"{scope} does not accept a query-language argument")
    return scope


def token_in_language_scope(
        scope,
        *,
        effective_language,
        is_structural_token,
        query_language=None,
        contract):
    """Return whether one token belongs to an explicitly named projection.

    Structural layout tokens are retained in every projection but are never
    counted as lexical language evidence.
    """
    validate_language_scope(
        scope, query_language=query_language, contract=contract)
    if is_structural_token:
        return True
    if scope == "ALL_LANGUAGES_UNCONDITIONED":
        return True
    if scope == "MULTILINGUAL_CONDITIONED":
        return effective_language in set(contract["canonical_codes"])
    if scope == "HITTITE_ONLY":
        return effective_language == "Hit"
    if scope == "SAME_LANGUAGE_AS_QUERY":
        return effective_language == query_language
    if scope == "CROSS_LANGUAGE_PARALLEL":
        return (
            effective_language in set(contract["canonical_codes"])
            and effective_language != query_language
        )
    raise LanguageScopeError(f"Unhandled language scope: {scope!r}")


def projected_language_identity(
        scope,
        effective_language,
        *,
        query_language=None,
        contract):
    """Return the language channel exposed by a governed projection."""
    validate_language_scope(
        scope, query_language=query_language, contract=contract)
    if scope == "ALL_LANGUAGES_UNCONDITIONED":
        return None
    return effective_language
