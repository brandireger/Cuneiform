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


CONTRACT_VERSION = "1.0.0"
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


def _base_packet(source, packet_id, source_provenance, mode, mask_length):
    query = source["query"]
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


def adapt_p2e4_packet(source, packet_id, source_provenance):
    """Convert a P2-E4 single-sign packet without copying hidden gold."""
    packet = _base_packet(
        source, packet_id, source_provenance, "SINGLE_SIGN", 1)
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
    return validate_suggestion_packet(packet)


def adapt_p2e6_packet(source, packet_id, source_provenance):
    """Convert a P2-E6 multi-sign packet without copying hidden gold."""
    mask_length = int(source["query"]["mask_length"])
    packet = _base_packet(
        source, packet_id, source_provenance, "MULTI_SIGN", mask_length)
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
    if total > len(options):
        packet["limitations"].append({
            "code": "EQUAL_SUPPORT_TAIL_COLLAPSED",
            "message": (
                f"{total - len(options)} additional equal-support or "
                "lower-display alternatives are preserved by count and must "
                "remain inspectable; they may not be silently discarded."
            ),
        })
    return validate_suggestion_packet(packet)
