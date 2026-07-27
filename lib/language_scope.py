"""P4-D: required, fail-closed language scoping for active code paths.

`lib/language_layers_v2.py` holds the ratified Gate 0 rules and the scope
vocabulary. This module is the *calling convention* built on top of them: a
validated `LanguageScope` value object that active renderers, retrievers,
scorers, and calibration entry points must accept as a REQUIRED argument.

Why a value object rather than a string:

- a bare string can be defaulted to `None` in a signature and silently
  reintroduce language-blind behavior -- the exact defect P4-D exists to
  remove (`line_lang_lookup=None` in the pre-Phase-4 call convention);
- `SAME_LANGUAGE_AS_QUERY` and `CROSS_LANGUAGE_PARALLEL` are only meaningful
  together with a resolved query language, so the pair must be validated once,
  at construction, not re-checked ad hoc at each use; and
- run manifests must record the scope, its query language, the contract rule
  id, and the mixed-line policy together. `manifest_entry()` makes that one
  call instead of five hand-assembled dict keys per script.

Construction is the only validation point. `require_language_scope()` then
rejects anything that is not an already-validated instance, so a call site
cannot pass a raw string, `None`, `"auto"`, or a dict.
"""

from dataclasses import dataclass
from pathlib import Path

import language_layers_v2 as llv2


LanguageScopeError = llv2.LanguageScopeError

# How a projection treats a line whose lexical tokens do not all resolve to
# the scope's language.
#
# EXCLUDE_LINE is the only ratified policy. Dropping the offending WORDS and
# splicing the survivors together would manufacture token adjacencies that
# never existed on the tablet -- a bigram anchor spanning a removed Hurrian
# word is a false anchor, and the anchor index is exactly what consumes this
# rendering. Excluding the whole line keeps the "anchors never span a
# language boundary" property that the line-granularity filter had
# implicitly, and fails toward exclusion rather than invention.
#
# A segment-splitting policy (render a mixed line as several independent
# anchor domains) is a coherent future option, but it changes the per-line
# list shape that `line_position_in_fragment` numbering depends on across the
# real-gap path, so it is deliberately NOT offered here as a half-wired
# alternative.
MIXED_LINE_POLICIES = frozenset({"EXCLUDE_LINE"})
DEFAULT_MIXED_LINE_POLICY = "EXCLUDE_LINE"

_QUERY_RELATIVE_SCOPES = frozenset({
    "SAME_LANGUAGE_AS_QUERY",
    "CROSS_LANGUAGE_PARALLEL",
})


@dataclass(frozen=True)
class LanguageScope:
    """A validated, explicit language-selection policy.

    Instances are only produced by `build_language_scope()`; constructing one
    directly bypasses contract validation and is not supported.
    """

    scope: str
    query_language: str | None
    mixed_line_policy: str
    rule_id: str
    contract_path: str

    @property
    def is_query_relative(self):
        return self.scope in _QUERY_RELATIVE_SCOPES

    @property
    def is_ablation(self):
        """ALL_LANGUAGES_UNCONDITIONED intentionally removes language
        identity. It is permitted for ablation only and must be labeled as
        such wherever a result derived from it is reported."""
        return self.scope == "ALL_LANGUAGES_UNCONDITIONED"

    def manifest_entry(self):
        """The run-manifest block for this scope.

        Per CLAUDE.md's Phase 4 engineering standard, language-based semantic
        selection must be registered and included in the run manifest; this
        is the single serialization point for that requirement.
        """
        return {
            "language_scope": self.scope,
            "query_language": self.query_language,
            "mixed_line_policy": self.mixed_line_policy,
            "language_rule_id": self.rule_id,
            "language_contract_path": self.contract_path,
            "ablation_only": self.is_ablation,
        }

    def describe(self):
        if self.query_language:
            return f"{self.scope}(query_language={self.query_language})"
        return self.scope


def build_language_scope(
        scope,
        *,
        query_language=None,
        mixed_line_policy=DEFAULT_MIXED_LINE_POLICY,
        contract=None,
        contract_path=llv2.DEFAULT_CONTRACT_PATH):
    """Validate and freeze one explicit language scope.

    Fails closed on `None`, `"auto"`, `"default"`, `"language_blind"`, unknown
    scope names, a missing query language for a query-relative scope, and a
    supplied query language for a scope that does not accept one -- all
    delegated to the ratified `validate_language_scope()` so precedence lives
    in one place.
    """
    if contract is None:
        contract = llv2.load_language_contract(contract_path)
    llv2.validate_language_scope(
        scope, query_language=query_language, contract=contract)
    if mixed_line_policy not in MIXED_LINE_POLICIES:
        raise LanguageScopeError(
            f"Unknown mixed-line policy: {mixed_line_policy!r}; "
            f"ratified policies are {sorted(MIXED_LINE_POLICIES)}")
    return LanguageScope(
        scope=scope,
        query_language=query_language,
        mixed_line_policy=mixed_line_policy,
        rule_id=contract["effective_rule"]["rule_id"],
        contract_path=str(Path(contract_path)),
    )


def require_language_scope(value, *, label):
    """Guard an ingress argument. Raises unless `value` is a validated scope.

    Call this at the top of every language-sensitive function rather than
    trusting the signature: a keyword-only parameter with no default still
    accepts `None` from a caller that has one in a variable.
    """
    if isinstance(value, LanguageScope):
        return value
    if value is None:
        raise LanguageScopeError(
            f"{label}: language_scope is required and must not be None. "
            "Build one with language_scope.build_language_scope(...); "
            "omitted/auto/default/language_blind selection is prohibited "
            "(PHASE4_CHARTER.md, specs/LANGUAGE_LAYERS_V2.md).")
    raise LanguageScopeError(
        f"{label}: language_scope must be a validated LanguageScope, got "
        f"{type(value).__name__}. A bare scope name is not accepted -- build "
        "it with language_scope.build_language_scope(...) so the query "
        "language and contract rule are validated once.")
