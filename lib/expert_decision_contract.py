"""Canonical expert-decision packets for missing Hittite text.

The contract separates three things that earlier exploratory packets mixed:

1. observable/editorially mediated evidence;
2. group-level audit rates;
3. a human decision that remains quarantined pending adjudication.

It deliberately has no field for an option-level truth probability because
Phase 2 did not establish one.
"""

import hashlib
import json
from copy import deepcopy


CONTRACT_VERSION = "1.1.0"
RECORD_TYPE = "missing_text_suggestion_packet"
DECISION_RECORD_TYPE = "expert_decision_record"
PRESENT_ACTIONS = (
    "SELECT_OPTION",
    "REJECT_ALL",
    "OTHER_OR_UNSUPPORTED",
    "WITHHOLD_JUDGMENT",
)
ABSTAIN_ACTIONS = (
    "OTHER_OR_UNSUPPORTED",
    "WITHHOLD_JUDGMENT",
)
EVIDENCE_CLASSES = {
    "OBSERVED_ARTIFACT",
    "OBSERVED_DOCUMENT_STRUCTURE",
    "CATALOG_METADATA",
    "EDITORIAL_TRANSCRIPTION",
    "EDITORIAL_RESTORATION",
    "EDITORIAL_RELATION",
    "MODEL_DERIVED",
    "SYSTEM_TECHNICAL",
}

# P4-D (contract 1.1.0). Why the query language may be unknown. Only
# RESOLVED permits a non-null query_language; every other status obliges the
# packet to carry a LANGUAGE_* limitation, so a display can never present a
# language-silent packet as though its language had been established.
LANGUAGE_STATUSES = {
    # The ratified word_override_else_line_v2 rule resolved one language.
    "RESOLVED",
    # The packet's source run predates language resolution. Not an assertion
    # that the span is non-Hittite -- an assertion that nobody checked.
    "UNRESOLVED_IN_SOURCE_RUN",
    # A malformed/unrecognized/explicit-empty source tag left it unresolved.
    "UNRESOLVED_SOURCE_ANOMALY",
    # More than one resolved language on the query line.
    "MIXED_LANGUAGE_QUERY_LINE",
}
LANGUAGE_LIMITATION_PREFIX = "LANGUAGE_"


class ContractError(ValueError):
    """Raised when a packet or decision violates a semantic invariant."""


def canonical_sha256(value):
    """Hash one JSON-compatible value using canonical compact serialization."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require(mapping, fields, label):
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise ContractError(f"{label} is missing required fields: {missing}")


def _validate_rate(rate, label):
    _require(
        rate,
        [
            "kind",
            "scope",
            "estimand",
            "estimate",
            "interval",
            "sample_size",
            "instance_truth_probability",
            "ui_label",
        ],
        label,
    )
    if rate["kind"] == "UNAVAILABLE":
        if rate["scope"] != "NONE":
            raise ContractError(f"{label}: unavailable rate must have NONE scope")
        if any(
                rate[field] is not None
                for field in ("estimand", "estimate", "interval", "sample_size")):
            raise ContractError(
                f"{label}: unavailable rate cannot carry numeric estimates")
    elif rate["kind"] == "GROUP_AUDIT_RATE":
        if rate["scope"] not in {"OPTION_RANK", "CANDIDATE_SET"}:
            raise ContractError(f"{label}: invalid audit-rate scope")
        estimate = rate["estimate"]
        interval = rate["interval"]
        if not isinstance(estimate, (int, float)) or not 0 <= estimate <= 1:
            raise ContractError(f"{label}: estimate must be in [0, 1]")
        _require(interval, ["method", "level", "lower", "upper"], label)
        if (
                interval["method"] != "WILSON_SCORE"
                or interval["level"] != 0.95
                or not 0 <= interval["lower"] <= estimate
                or not estimate <= interval["upper"] <= 1):
            raise ContractError(f"{label}: invalid Wilson interval")
        if not isinstance(rate["sample_size"], int) or rate["sample_size"] <= 0:
            raise ContractError(f"{label}: invalid sample size")
    else:
        raise ContractError(f"{label}: unknown uncertainty kind")
    if rate["instance_truth_probability"] is not False:
        raise ContractError(
            f"{label}: group audit rates cannot be instance probabilities")


def _validate_option_display(option):
    """Enforce the option `display` block, and require it where it matters.

    Two-sided on purpose. A malformed block is rejected, and an option that
    proposes no signs is REQUIRED to carry one -- an empty-middle option
    reaching a renderer without it is exactly the defect this exists to stop,
    and it fails silently (the UI draws an empty candidate) rather than
    loudly, so the schema has to catch it.
    """
    display = option.get("display")
    if display is None:
        if is_empty_middle_option(option):
            raise ContractError(
                "option: an option proposing no signs must carry a display "
                "block; call annotate_empty_middle_options(). Without it a "
                "renderer shows an empty candidate as if it were a reading.")
        return
    _require(
        display,
        ["kind", "query_kind", "is_a_reading", "render_signs_as",
         "headline", "detail"],
        "option.display",
    )
    if display["kind"] != "EMPTY_MIDDLE":
        raise ContractError(
            f"option.display: unknown kind {display['kind']!r}")
    if display["query_kind"] not in EMPTY_MIDDLE_QUERY_KINDS:
        raise ContractError(
            f"option.display: unknown query kind {display['query_kind']!r}")
    if display["is_a_reading"] is not False:
        raise ContractError(
            "option.display: an empty middle is never a reading")
    if not is_empty_middle_option(option):
        raise ContractError(
            "option.display: EMPTY_MIDDLE display on an option that proposes "
            "signs")
    if option["option_audit"]["kind"] != "UNAVAILABLE":
        raise ContractError(
            "option.display: an empty-middle option must not carry a "
            "rank-level group audit rate; its estimand is agreement with the "
            "true attested middle, which this option cannot be")


def _validate_language_block(packet):
    """Enforce the P4-D language-transparency invariants on one packet.

    The point is not to record a language for its own sake. It is that an
    expert reading a candidate set must be able to see which language the
    system believed it was working in, whether that belief was established
    or merely assumed, and whether any displayed evidence came from a
    different language than the query.
    """
    language = packet["language"]
    _require(
        language,
        [
            "language_scope",
            "query_language",
            "query_language_status",
            "mixed_language_query_line",
            "source_languages",
            "cross_language_source_languages",
            "cross_language_assistance_enabled",
            "language_rule_id",
            "language_evidence_class",
        ],
        "language",
    )
    if language["query_language_status"] not in LANGUAGE_STATUSES:
        raise ContractError("language: unknown query_language_status")
    # Gate 0 decision 7: language annotations are editorial transcription,
    # never observed artifact. A packet must not upgrade their evidence class.
    if language["language_evidence_class"] != "EDITORIAL_TRANSCRIPTION":
        raise ContractError(
            "language: language fields are EDITORIAL_TRANSCRIPTION evidence")

    resolved = language["query_language_status"] == "RESOLVED"
    if resolved and not language["query_language"]:
        raise ContractError(
            "language: RESOLVED status requires a query_language")
    if not resolved and language["query_language"] is not None:
        raise ContractError(
            "language: unresolved status cannot carry a query_language")

    if language["mixed_language_query_line"] not in (True, False):
        raise ContractError("language: mixed_language_query_line must be bool")

    cross = list(language["cross_language_source_languages"])
    if not language["cross_language_assistance_enabled"] and cross:
        raise ContractError(
            "language: cross-language evidence present while the "
            "cross-language assistance channel is disabled")
    if language["query_language"] in cross:
        raise ContractError(
            "language: the query language cannot appear in the "
            "cross-language channel -- the two channels must stay separable")

    if not resolved:
        codes = [
            item.get("code", "") for item in packet["limitations"]]
        if not any(
                code.startswith(LANGUAGE_LIMITATION_PREFIX) for code in codes):
            raise ContractError(
                "language: an unresolved query language requires an explicit "
                f"{LANGUAGE_LIMITATION_PREFIX}* limitation on the packet")


def build_language_context(
        *,
        language_scope,
        query_language=None,
        query_language_status,
        mixed_language_query_line=False,
        source_languages=(),
        cross_language_source_languages=(),
        cross_language_assistance_enabled=False,
        language_rule_id=None):
    """Assemble the packet `language` block from explicit values.

    Every argument is explicit and there is no inferred default for the
    query language: a caller that does not know it must say
    `UNRESOLVED_IN_SOURCE_RUN` rather than let a blank field read as Hittite.
    """
    return {
        "language_scope": language_scope,
        "query_language": query_language,
        "query_language_status": query_language_status,
        "mixed_language_query_line": bool(mixed_language_query_line),
        "source_languages": sorted(set(source_languages)),
        "cross_language_source_languages": sorted(
            set(cross_language_source_languages)),
        "cross_language_assistance_enabled": bool(
            cross_language_assistance_enabled),
        "language_rule_id": language_rule_id,
        "language_evidence_class": "EDITORIAL_TRANSCRIPTION",
    }


def validate_suggestion_packet(packet):
    """Validate one canonical suggestion packet and return it unchanged."""
    _require(
        packet,
        [
            "record_type",
            "contract_version",
            "packet_id",
            "task",
            "mode",
            "status",
            "source_provenance",
            "query",
            "candidate_set",
            "supporting_evidence",
            "contradictory_evidence",
            "limitations",
            "assistance",
            "language",
            "workflow",
            "abstention",
        ],
        "packet",
    )
    if packet["record_type"] != RECORD_TYPE:
        raise ContractError("packet: wrong record_type")
    if packet["contract_version"] != CONTRACT_VERSION:
        raise ContractError("packet: unsupported contract_version")
    if packet["task"] != "MISSING_TEXT":
        raise ContractError("packet: unsupported task")
    if packet["mode"] not in {"SINGLE_SIGN", "MULTI_SIGN"}:
        raise ContractError("packet: unsupported mode")
    if packet["status"] not in {
            "PRESENT_CANDIDATES", "ABSTAIN_INSUFFICIENT_EVIDENCE"}:
        raise ContractError("packet: unsupported status")
    if "dev_evaluation_only" in packet:
        raise ContractError("packet: hidden evaluation payload must be stripped")

    query = packet["query"]
    _require(
        query,
        [
            "fragment_id",
            "cth",
            "location",
            "gap_extent",
            "left_context",
            "right_context",
            "context_evidence_class",
        ],
        "query",
    )
    if query["context_evidence_class"] != "EDITORIAL_TRANSCRIPTION":
        raise ContractError("query: context must be named editorial transcription")
    extent = query["gap_extent"]
    _require(extent, ["kind", "minimum_signs", "maximum_signs"], "gap_extent")
    if extent["kind"] not in {"EXACT", "BOUNDED", "UNKNOWN"}:
        raise ContractError("gap_extent: unsupported kind")
    if extent["kind"] == "EXACT":
        if (
                extent["minimum_signs"] is None
                or extent["minimum_signs"] != extent["maximum_signs"]):
            raise ContractError("gap_extent: EXACT requires equal bounds")

    candidate_set = packet["candidate_set"]
    _require(
        candidate_set,
        [
            "options",
            "shown_option_count",
            "total_option_count",
            "tail_collapsed",
            "collapsed_tail_count",
            "ranking_boundary_policy",
            "silent_truncation_allowed",
            "other_or_unsupported_available",
            "set_audit",
        ],
        "candidate_set",
    )
    options = candidate_set["options"]
    if candidate_set["shown_option_count"] != len(options):
        raise ContractError("candidate_set: shown count disagrees with options")
    if candidate_set["total_option_count"] < len(options):
        raise ContractError("candidate_set: total smaller than shown")
    collapsed = candidate_set["total_option_count"] - len(options)
    if candidate_set["collapsed_tail_count"] != collapsed:
        raise ContractError("candidate_set: collapsed-tail count mismatch")
    if candidate_set["tail_collapsed"] != (collapsed > 0):
        raise ContractError("candidate_set: collapsed-tail flag mismatch")
    if candidate_set["silent_truncation_allowed"] is not False:
        raise ContractError("candidate_set: silent truncation is forbidden")
    if candidate_set["other_or_unsupported_available"] is not True:
        raise ContractError("candidate_set: other/unsupported action is mandatory")
    if candidate_set["ranking_boundary_policy"] not in {
            "COMPLETE_AVAILABLE_SET", "TIE_COMPLETE"}:
        raise ContractError("candidate_set: invalid boundary policy")
    _validate_rate(candidate_set["set_audit"], "candidate_set.set_audit")

    option_ids = set()
    for option in options:
        _require(
            option,
            [
                "option_id",
                "rank",
                "signs",
                "evidence_class",
                "support",
                "option_audit",
            ],
            "option",
        )
        if option["option_id"] in option_ids:
            raise ContractError("option: duplicate option_id")
        option_ids.add(option["option_id"])
        if not isinstance(option["rank"], int) or option["rank"] <= 0:
            raise ContractError("option: rank must be a positive integer")
        if option["evidence_class"] not in EVIDENCE_CLASSES:
            raise ContractError("option: unknown evidence class")
        support = option["support"]
        _require(
            support,
            [
                "independent_witness_family_count",
                "supporting_witness_families",
                "share",
                "share_is_probability",
            ],
            "option.support",
        )
        if support["share_is_probability"] is not False:
            raise ContractError("option.support: support share is not probability")
        if support["share"] is not None and not 0 <= support["share"] <= 1:
            raise ContractError("option.support: share must be in [0, 1]")
        _validate_rate(option["option_audit"], "option.option_audit")
        _validate_option_display(option)

    for field in ("supporting_evidence", "contradictory_evidence"):
        for item in packet[field]:
            _require(
                item,
                [
                    "evidence_id",
                    "type",
                    "polarity",
                    "evidence_class",
                    "summary",
                    "source_refs",
                ],
                field,
            )
            if item["evidence_class"] not in EVIDENCE_CLASSES:
                raise ContractError(f"{field}: unknown evidence class")

    assistance = packet["assistance"]
    _require(
        assistance,
        [
            "evidence_policy",
            "enabled_layers",
            "editorial_features_used",
            "model_features_used",
            "model_generated_content_present",
        ],
        "assistance",
    )
    if assistance["model_generated_content_present"] != bool(
            assistance["model_features_used"]):
        raise ContractError("assistance: model-content flag mismatch")

    _validate_language_block(packet)

    workflow = packet["workflow"]
    _require(
        workflow,
        [
            "expert_action_required",
            "automatic_completion_allowed",
            "selection_becomes_ground_truth_automatically",
            "ground_truth_effect",
            "allowed_actions",
        ],
        "workflow",
    )
    if (
            workflow["expert_action_required"] is not True
            or workflow["automatic_completion_allowed"] is not False
            or workflow["selection_becomes_ground_truth_automatically"]
            is not False
            or workflow["ground_truth_effect"]
            != "QUARANTINED_PENDING_ADJUDICATION"):
        raise ContractError("workflow: unsafe automation or ground-truth policy")

    if packet["status"] == "PRESENT_CANDIDATES":
        if not options:
            raise ContractError("packet: presented status requires options")
        if tuple(workflow["allowed_actions"]) != PRESENT_ACTIONS:
            raise ContractError("workflow: presented packet actions mismatch")
        if packet["abstention"]["reason"] is not None:
            raise ContractError("packet: presented packet cannot have abstention reason")
    else:
        if options or candidate_set["total_option_count"] != 0:
            raise ContractError("packet: abstention cannot contain options")
        if tuple(workflow["allowed_actions"]) != ABSTAIN_ACTIONS:
            raise ContractError("workflow: abstention packet actions mismatch")
        if not packet["abstention"]["reason"]:
            raise ContractError("packet: abstention reason is required")
    return packet


def validate_expert_decision(decision, packet):
    """Validate a human decision against the immutable packet it reviewed."""
    validate_suggestion_packet(packet)
    _require(
        decision,
        [
            "record_type",
            "contract_version",
            "decision_id",
            "packet_id",
            "packet_sha256",
            "action",
            "selected_option_id",
            "proposed_other_signs",
            "reviewer",
            "rationale",
            "created_utc",
            "assistance_acknowledged",
            "ground_truth_status",
            "requires_adjudication",
        ],
        "decision",
    )
    if decision["record_type"] != DECISION_RECORD_TYPE:
        raise ContractError("decision: wrong record_type")
    if decision["contract_version"] != CONTRACT_VERSION:
        raise ContractError("decision: unsupported contract_version")
    if decision["packet_id"] != packet["packet_id"]:
        raise ContractError("decision: packet_id mismatch")
    if decision["packet_sha256"] != canonical_sha256(packet):
        raise ContractError("decision: packet hash mismatch")
    if decision["action"] not in packet["workflow"]["allowed_actions"]:
        raise ContractError("decision: action was not available")
    option_ids = {
        option["option_id"] for option in packet["candidate_set"]["options"]}
    if decision["action"] == "SELECT_OPTION":
        if decision["selected_option_id"] not in option_ids:
            raise ContractError("decision: selected option is absent")
        if decision["proposed_other_signs"] is not None:
            raise ContractError("decision: selection cannot propose other signs")
    elif decision["action"] == "OTHER_OR_UNSUPPORTED":
        if decision["selected_option_id"] is not None:
            raise ContractError("decision: other action cannot select an option")
    elif (
            decision["selected_option_id"] is not None
            or decision["proposed_other_signs"] is not None):
        raise ContractError("decision: action cannot carry option content")
    if (
            decision["assistance_acknowledged"] is not True
            or decision["ground_truth_status"]
            != "QUARANTINED_EXPERT_JUDGMENT"
            or decision["requires_adjudication"] is not True):
        raise ContractError("decision: expert judgment must remain quarantined")
    _require(
        decision["reviewer"],
        ["reviewer_id", "declared_role"],
        "decision.reviewer",
    )
    return decision


def unavailable_rate(reason):
    return {
        "kind": "UNAVAILABLE",
        "scope": "NONE",
        "estimand": None,
        "estimate": None,
        "interval": None,
        "sample_size": None,
        "instance_truth_probability": False,
        "ui_label": reason,
    }


def _group_rate(scope, calibration):
    if calibration is None:
        return unavailable_rate("No transferable group audit rate is available.")
    if scope == "OPTION_RANK":
        estimate = calibration["calibrated_empirical_agreement"]
        sample_size = calibration["calibration_contexts_with_rank_available"]
    else:
        estimate = calibration["candidate_set_calibration_rate"]
        sample_size = calibration["calibration_presented_contexts"]
    return {
        "kind": "GROUP_AUDIT_RATE",
        "scope": scope,
        "estimand": calibration["estimand"],
        "estimate": estimate,
        "interval": {
            "method": "WILSON_SCORE",
            "level": 0.95,
            "lower": calibration["wilson_95"][0],
            "upper": calibration["wilson_95"][1],
        },
        "sample_size": sample_size,
        "instance_truth_probability": False,
        "ui_label": (
            "Historical group audit rate; not the probability that this "
            "option or set is correct."
        ),
    }


def _option(source, index, scope):
    calibration = source.get("calibration") if scope == "OPTION_RANK" else None
    share = source.get("witness_support_share")
    return {
        "option_id": f"option-{index:03d}",
        "rank": int(source["rank"]),
        "signs": list(source["middle"]),
        "evidence_class": source["evidence_class"],
        "support": {
            "independent_witness_family_count":
                int(source["independent_witness_family_count"]),
            "supporting_witness_families":
                list(source["supporting_witness_families"]),
            "share": share,
            "share_is_probability": False,
        },
        "option_audit": _group_rate(scope, calibration),
    }


def _supporting_evidence(options):
    return [
        {
            "evidence_id": f"support-{option['option_id']}",
            "type": "INDEPENDENT_WITNESS_SUPPORT",
            "polarity": "SUPPORTS_OPTION",
            "evidence_class": option["evidence_class"],
            "summary": (
                f"{option['support']['independent_witness_family_count']} "
                "independent witness family/families preserve this sequence."
            ),
            "source_refs": list(
                option["support"]["supporting_witness_families"]),
        }
        for option in options
    ]


# ---------------------------------------------------------------- empty middle
#
# A witness proposal is whatever sits between the query's two anchors in an
# independent witness. The anchor indices deliberately admit a middle of
# length zero, so "the two anchors stand adjacent in this witness" is a
# first-class proposal and can rank first on real witness support.
#
# For a single-sign query it is not a reading. The query asserts a sign stood
# there -- whether by damage markup or, in a synthetic evaluation context, by
# hiding a known attested one -- and a witness with no sign contradicts that
# assertion. Rendered as a ranked candidate with a rate beside it, it reads as
# "the missing sign is: nothing", which is a claim no calibration measured.
#
# The remedy here is DISPLAY-ONLY and that is the point. The option keeps its
# rank and its witness support, so the applied ranking stays the construction
# that P2-E4/P2-E9 calibrated; removing it would decouple the rate from the
# thing it rates. What changes is that it is labelled as contradictory
# evidence rather than as a reading, and its rank-level group rate is withheld
# -- that rate's estimand is "the fraction whose hidden/true attested middle
# occurs at that rank", and an option that cannot be an attested middle is not
# in that estimand's support.
#
# Measured incidence, real gaps (reports/phase5_empty_middle_census.md):
# 109 of 577 accepted cross-line gaps, and 5 of 16 P2-E4 packets.

EMPTY_MIDDLE_LIMITATION_CODE = "EMPTY_MIDDLE_CONTRADICTS_QUERY_STRUCTURE"

# Why the query believes a sign is there. The branches are not cosmetic: they
# are four different epistemic situations, and "witnesses show nothing here"
# means something different in each. Collapsing them into one sentence is the
# defect this replaces.
EMPTY_MIDDLE_QUERY_KINDS = {
    # Editor saw a trace and could not read it (damage_state illegible_x).
    # 57 of the 109 measured real-gap cases.
    "ILLEGIBLE_TRACE": {
        "headline": "Witnesses show no sign here — the trace is off-formula.",
        "detail": (
            "Independent witnesses attest the two anchors directly adjacent, "
            "with nothing between them. That does not read the illegible "
            "trace; it establishes that the parallel tradition has no sign in "
            "this position. Either the trace is not a separate sign, or this "
            "manuscript carries a variant the witnesses do not."
        ),
    },
    # Editor proposed a specific sign. 41 of the 109. This is the
    # cleanroom-rule-6 case: a bracket contradicted by the witness tradition.
    "EDITORIAL_RESTORATION": {
        "headline": "Witnesses contradict the editorial restoration.",
        "detail": (
            "Independent witnesses attest the two anchors directly adjacent, "
            "with nothing between them, while the edition restores a sign "
            "here. Restorations are scholarly hypotheses, not attested text, "
            "so this is a disagreement between two editorial judgements and "
            "not a correction of one by the other."
        ),
    },
    # Editor marked an indeterminate-length lacuna (an ellipsis token).
    # 11 of the 109. Here "nothing" is close to an answer.
    "INDETERMINATE_LACUNA": {
        "headline": "Witnesses show no gap here at all.",
        "detail": (
            "The edition marks a lacuna of undetermined length. Independent "
            "witnesses attest the two anchors directly adjacent, so the "
            "parallel tradition has no gap in this position. Note that the "
            "query's own gap length was never established, so this bears on "
            "whether a gap exists, not on how long it is."
        ),
    },
    # Synthetic evaluation context: a known attested sign was deliberately
    # hidden. Nothing is damaged; the sign is known to exist.
    "HIDDEN_ATTESTED_SIGN": {
        "headline": "Witnesses show no sign where one is known to stand.",
        "detail": (
            "This is an evaluation context: a genuinely attested sign was "
            "hidden on purpose, so a sign certainly stood here. Independent "
            "witnesses nevertheless attest the two anchors adjacent, which "
            "makes this proposal a measure of witness divergence rather than "
            "a candidate reading. It cannot be correct by construction."
        ),
    },
}

EMPTY_MIDDLE_AUDIT_WITHHELD = (
    "No applicable group audit rate. The rank-level rate estimates how often "
    "the true attested middle appears at this rank; this option proposes no "
    "sign at all and so cannot be that middle."
)


# The editorial ellipsis. In TLHdig this marks a lacuna of undetermined
# length, so a run consisting of one is NOT a one-sign gap in the way a
# restored sign is -- it is "an unknown amount is missing". It reaches the
# single-sign population anyway (2,725 of 46,118 cross-line eligible gaps),
# which is a separate open scope question; what matters here is that the
# display must not describe it as though the editor had proposed a sign.
INDETERMINATE_LACUNA_TOKEN = "…"


def is_empty_middle_option(option):
    """True when an option proposes no signs at all."""
    return not option.get("signs")


def empty_middle_query_kind_for_damage(damage_state, token=None):
    """Map a real-gap run's encoded damage to its empty-middle branch.

    Real gaps carry `damage_state` from the document-order state machine over
    `<del_in>/<del_fin>` and `<laes_in>/<laes_fin>`. Synthetic evaluation
    contexts (P2-E4/P2-E6) have no damage at all and must not come through
    here -- their adapters pass `HIDDEN_ATTESTED_SIGN` directly.

    Fails closed on anything unrecognized rather than defaulting, for the same
    reason `classify_empty_middle` does.
    """
    if token is not None and token == INDETERMINATE_LACUNA_TOKEN:
        return "INDETERMINATE_LACUNA"
    if damage_state == "illegible_x":
        return "ILLEGIBLE_TRACE"
    if damage_state in ("restored", "laes"):
        return "EDITORIAL_RESTORATION"
    raise ContractError(
        f"empty_middle_query_kind_for_damage: unrecognized damage state "
        f"{damage_state!r} (token {token!r}). An 'attested' run is not a gap, "
        "and a synthetic hidden-sign context must pass "
        "'HIDDEN_ATTESTED_SIGN' directly rather than being inferred here.")


def classify_empty_middle(query_kind):
    """Return the display copy for one empty-middle situation.

    Fails closed on an unknown kind rather than emitting a generic sentence:
    the whole purpose of the branch is that these situations differ, so a
    caller that has not decided which one applies must not get a default.
    """
    if query_kind not in EMPTY_MIDDLE_QUERY_KINDS:
        raise ContractError(
            f"classify_empty_middle: unknown query kind {query_kind!r}; "
            f"expected one of {sorted(EMPTY_MIDDLE_QUERY_KINDS)}. There is no "
            "default -- 'witnesses show nothing' means something different in "
            "each case.")
    return dict(EMPTY_MIDDLE_QUERY_KINDS[query_kind], query_kind=query_kind)


def annotate_empty_middle_options(packet, *, query_kind):
    """Label any empty-middle option as contradictory evidence, in place.

    Does NOT reorder, drop, or reweight anything. The candidate set, the ranks,
    and the witness support counts are exactly what the calibrated ranking
    produced.
    """
    classification = classify_empty_middle(query_kind)
    annotated = []
    for option in packet["candidate_set"]["options"]:
        if not is_empty_middle_option(option):
            continue
        option["display"] = {
            "kind": "EMPTY_MIDDLE",
            "query_kind": classification["query_kind"],
            "is_a_reading": False,
            "render_signs_as": "(no sign)",
            "headline": classification["headline"],
            "detail": classification["detail"],
        }
        option["option_audit"] = unavailable_rate(EMPTY_MIDDLE_AUDIT_WITHHELD)
        annotated.append(option)

    for option in annotated:
        packet["contradictory_evidence"].append({
            "evidence_id": f"contradiction-{option['option_id']}",
            "type": "WITNESS_ANCHORS_ADJACENT",
            "polarity": "CONTRADICTS_QUERY_STRUCTURE",
            "evidence_class": option["evidence_class"],
            "summary": (
                f"{option['support']['independent_witness_family_count']} "
                "independent witness family/families attest the left and "
                "right anchors directly adjacent, with no sign between them. "
                + classification["headline"]
            ),
            "source_refs": list(
                option["support"]["supporting_witness_families"]),
        })

    if annotated:
        packet["limitations"].append({
            "code": EMPTY_MIDDLE_LIMITATION_CODE,
            "message": (
                f"{len(annotated)} option(s) in this set propose no sign at "
                "all. They are retained at their measured rank because the "
                "calibration was fit over rankings that included them, but "
                "they are contradictory evidence about the query's structure, "
                "not candidate readings, and carry no rank-level rate. "
                + classification["detail"]
            ),
        })
    return packet


def _base_packet(
        source, packet_id, source_provenance, mode, mask_length,
        language_context):
    query = source["query"]
    if not language_context:
        raise ContractError(
            "_base_packet: language_context is required (contract 1.1.0). "
            "Build it with build_language_context(); a packet may not be "
            "emitted without stating what language it believed it was in.")
    status = (
        "PRESENT_CANDIDATES"
        if source["decision"] == "PRESENT_CANDIDATE_SET"
        else "ABSTAIN_INSUFFICIENT_EVIDENCE"
    )
    return {
        "record_type": RECORD_TYPE,
        "contract_version": CONTRACT_VERSION,
        "packet_id": packet_id,
        "task": "MISSING_TEXT",
        "mode": mode,
        "status": status,
        "source_provenance": deepcopy(source_provenance),
        "query": {
            "fragment_id": query["fragment_id"],
            "cth": query["cth"],
            "location": {
                "line_index_in_doc": query["line_index_in_doc"],
                "sign_offset_in_line": query["sign_offset_in_line"],
                "span_ordinal": query["span_ordinal"],
            },
            "gap_extent": {
                "kind": "EXACT",
                "minimum_signs": mask_length,
                "maximum_signs": mask_length,
            },
            "left_context": list(query["left_anchor"]),
            "right_context": list(query["right_anchor"]),
            "context_evidence_class": "EDITORIAL_TRANSCRIPTION",
        },
        "candidate_set": {},
        "supporting_evidence": [],
        "contradictory_evidence": [],
        "limitations": [],
        "language": deepcopy(language_context),
        "assistance": {
            "evidence_policy": source["evidence_policy"],
            "enabled_layers": list(source["enabled_assistance_layers"]),
            "editorial_features_used":
                list(source["editorial_features_used"]),
            "model_features_used": list(source["model_features_used"]),
            "model_generated_content_present":
                bool(source["model_features_used"]),
        },
        "workflow": {
            "expert_action_required": True,
            "automatic_completion_allowed": False,
            "selection_becomes_ground_truth_automatically": False,
            "ground_truth_effect": "QUARANTINED_PENDING_ADJUDICATION",
            "allowed_actions": list(
                PRESENT_ACTIONS if status == "PRESENT_CANDIDATES"
                else ABSTAIN_ACTIONS),
        },
        "abstention": {
            "reason": source["abstention_reason"],
            "encoded_evidence_insufficient": status
            == "ABSTAIN_INSUFFICIENT_EVIDENCE",
        },
    }


_LANGUAGE_LIMITATION_MESSAGES = {
    "UNRESOLVED_IN_SOURCE_RUN": (
        "This packet's source run predates word-aware language resolution, "
        "so the language of the query span was never established. Treat the "
        "displayed evidence as language-unverified rather than assuming "
        "Hittite."
    ),
    "UNRESOLVED_SOURCE_ANOMALY": (
        "The source language tag for this span is empty, malformed, or "
        "unrecognized, and was deliberately not guessed at. The language of "
        "the query span is unknown."
    ),
    "MIXED_LANGUAGE_QUERY_LINE": (
        "More than one language is resolved on the query line, so a single "
        "query language cannot be stated for this span."
    ),
}


def _append_language_limitation(packet):
    """Add the mandatory LANGUAGE_* limitation when language is unresolved.

    `_validate_language_block` refuses a packet that lacks it, so this keeps
    the adapters honest by construction rather than by remembering.
    """
    status = packet["language"]["query_language_status"]
    if status == "RESOLVED":
        return
    packet["limitations"].append({
        "code": f"{LANGUAGE_LIMITATION_PREFIX}{status}",
        "message": _LANGUAGE_LIMITATION_MESSAGES[status],
    })


def adapt_p2e4_packet(
        source, packet_id, source_provenance, language_context):
    """Convert a P2-E4 single-sign packet without copying hidden gold.

    `language_context` is required (contract 1.1.0); build it with
    `build_language_context()`.
    """
    packet = _base_packet(
        source, packet_id, source_provenance, "SINGLE_SIGN", 1,
        language_context)
    alternatives = source["candidate_set"]["alternatives"]
    options = [
        _option(alternative, index, "OPTION_RANK")
        for index, alternative in enumerate(alternatives, 1)
    ]
    total = int(source["candidate_set"]["total_alternatives"])
    packet["candidate_set"] = {
        "options": options,
        "shown_option_count": len(options),
        "total_option_count": total,
        "tail_collapsed": total > len(options),
        "collapsed_tail_count": total - len(options),
        "ranking_boundary_policy": "COMPLETE_AVAILABLE_SET",
        "silent_truncation_allowed": False,
        "other_or_unsupported_available": True,
        "set_audit": unavailable_rate(
            "Single-sign audit rates apply to option rank, not the set."),
    }
    packet["supporting_evidence"] = _supporting_evidence(options)
    packet["limitations"] = [
        {
            "code": "RANK_GROUP_RATE_NOT_INSTANCE_PROBABILITY",
            "message": source["candidate_set"]["probability_warning"],
        },
        {
            "code": "NO_ENCODED_CONTRADICTION_DOES_NOT_MEAN_CONFIRMED",
            "message": (
                "An empty contradictory-evidence list means no contradiction "
                "was encoded in this packet, not that the option is true."
            ),
        },
    ]
    _append_language_limitation(packet)
    # P2-E4 contexts are synthetic by construction: a genuinely attested sign
    # was hidden, so a sign certainly stood here. The kind is fixed rather
    # than passed in, so a caller cannot mislabel it.
    annotate_empty_middle_options(packet, query_kind="HIDDEN_ATTESTED_SIGN")
    return validate_suggestion_packet(packet)


def adapt_p2e6_packet(
        source, packet_id, source_provenance, language_context):
    """Convert a P2-E6 multi-sign packet without copying hidden gold.

    `language_context` is required (contract 1.1.0); build it with
    `build_language_context()`.
    """
    mask_length = int(source["query"]["mask_length"])
    packet = _base_packet(
        source, packet_id, source_provenance, "MULTI_SIGN", mask_length,
        language_context)
    alternatives = source["candidate_set"]["tie_complete_alternatives"]
    options = [
        _option(alternative, index, "CANDIDATE_SET")
        for index, alternative in enumerate(alternatives, 1)
    ]
    total = int(source["candidate_set"]["total_tie_complete_alternatives"])
    packet["candidate_set"] = {
        "options": options,
        "shown_option_count": len(options),
        "total_option_count": total,
        "tail_collapsed": total > len(options),
        "collapsed_tail_count": total - len(options),
        "ranking_boundary_policy": "TIE_COMPLETE",
        "silent_truncation_allowed": False,
        "other_or_unsupported_available": True,
        "set_audit": _group_rate(
            "CANDIDATE_SET",
            source["candidate_set"]["set_level_calibration"],
        ),
    }
    packet["supporting_evidence"] = _supporting_evidence(options)
    packet["limitations"] = [
        {
            "code": "SET_GROUP_RATE_NOT_OPTION_PROBABILITY",
            "message": source["candidate_set"]["probability_warning"],
        },
        {
            "code": "VARIABLE_WITNESS_MIDDLE_LENGTH",
            "message": (
                "Witness alternatives may contain a different number of "
                "signs than the intentionally masked audit span."
            ),
        },
    ]
    _append_language_limitation(packet)
    if total > len(options):
        packet["limitations"].append({
            "code": "EQUAL_SUPPORT_TAIL_COLLAPSED",
            "message": (
                f"{total - len(options)} additional equal-support or "
                "lower-display alternatives are preserved by count and must "
                "remain inspectable; they may not be silently discarded."
            ),
        })
    # Same reasoning as the single-sign path. The multi-sign set is NOT free
    # of this: 5 of the 12 exported P2-E6 packets carry an empty middle, one
    # of them at rank 1 on 19 independent families. Here the withheld rate is
    # the set-inclusion rate, on the same grounds -- an option that proposes
    # no signs cannot be the masked span the set is audited against.
    annotate_empty_middle_options(packet, query_kind="HIDDEN_ATTESTED_SIGN")
    return validate_suggestion_packet(packet)
