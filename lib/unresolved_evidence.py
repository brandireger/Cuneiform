"""P4-E: the Unresolved Evidence Workbench contract, executable.

`specs/UNRESOLVED_EVIDENCE_WORKBENCH.md` is the prose contract and
`configs/unresolved_evidence_contract.schema.json` the machine schema. This
module is the single implementation point for both, so extraction, clustering,
the expert interface, and any future adjudication export all agree on what a
record means rather than each re-deriving it.

The workbench exists to retain material the pipeline cannot resolve, in a form
a trained specialist can compare and annotate. Three properties are load-bearing
and are enforced here rather than left to caller discipline:

1. **Categories stay distinct.** A tokenizer OOV is an engineering vocabulary
   miss; a rare form is rare in this corpus; neither is evidence that a word
   is unknown to Hittitology. `RARE_FORM` and `LEXICAL_UNKNOWN` each require a
   named detector or judgment in `context`, so neither can be inferred from a
   tokenizer OOV or a bare frequency count. Extraction may assert `RARE_FORM`
   from a governed detector; `LEXICAL_UNKNOWN` is reachable only through
   expert adjudication (ratified 2026-07-27).

2. **Nothing here is corpus truth.** Occurrences and clusters carry
   `NOT_CORPUS_TRUTH`; expert events carry `QUARANTINED_EXPERT_JUDGMENT` and
   `requires_adjudication`. `EXPERT_SUPPORTED` means one recorded expert
   supports a hypothesis -- not consensus, not truth.

3. **Events are append-only and hash-bound.** Each event stores the SHA-256 of
   the record it reviewed and of the prior event, forming a chain. A snapshot
   is a deterministic projection of that chain, never an independently mutated
   state.

Test-side material cannot enter: `main_split` is constrained to
train/dev/discovery at the schema level and re-checked here.
"""

import hashlib
import json
from datetime import datetime, timezone


CONTRACT_VERSION = "1.1.0"
OCCURRENCE_RECORD_TYPE = "unresolved_occurrence"
CLUSTER_RECORD_TYPE = "unresolved_cluster_proposal"
EVENT_RECORD_TYPE = "unresolved_expert_annotation_event"

CATEGORIES = (
    "ILLEGIBLE_SIGN",
    "PARTIALLY_PRESERVED_READING",
    "UNCERTAIN_TRANSCRIPTION",
    "RARE_FORM",
    "LEXICAL_UNKNOWN",
    "TOKENIZER_OOV",
    "UNRECOGNIZED_LANGUAGE_TAG",
    "EMPTY_LANGUAGE_TAG",
    "MISSING_LANGUAGE_TAG",
    "MALFORMED_LANGUAGE_TAG",
    "SYMBOL_OR_ENCODING_ANOMALY",
    "PARSER_ANOMALY",
)

# Source language-status -> workbench category. `missing` is the case the
# 1.0.0 vocabulary could not express: an attribute that is absent is not the
# same as one that is present-but-empty, malformed, or unrecognized, and
# collapsing them would destroy the distinction Gate 0 deliberately drew.
LANGUAGE_STATUS_CATEGORY = {
    "explicit_empty": "EMPTY_LANGUAGE_TAG",
    "malformed": "MALFORMED_LANGUAGE_TAG",
    "unrecognized": "UNRECOGNIZED_LANGUAGE_TAG",
    "missing": "MISSING_LANGUAGE_TAG",
}
LANGUAGE_CATEGORIES = frozenset(LANGUAGE_STATUS_CATEGORY.values())
OCCURRENCE_STATUSES = (
    "UNREVIEWED", "GROUPED", "HYPOTHESIS", "EXPERT_SUPPORTED", "REJECTED",
    "WITHHELD",
)
CLUSTER_STATUSES = (
    # A deterministic, non-model grouping is SYSTEM_PROPOSAL. Labeling it
    # MODEL_PROPOSAL would tell an expert a model was consulted when none was.
    "SYSTEM_PROPOSAL",
    "MODEL_PROPOSAL",
    "EXPERT_CURATED",
    "REJECTED",
    "WITHHELD",
)
# Statuses a system may assign to its own output. Only a recorded expert
# action can produce EXPERT_CURATED.
SYSTEM_ASSIGNABLE_CLUSTER_STATUSES = frozenset(
    {"SYSTEM_PROPOSAL", "MODEL_PROPOSAL"})

# Categories that assert something about the FORM rather than its physical
# state, and therefore require a named detector rather than a bare claim.
#
# RARE_FORM and LEXICAL_UNKNOWN are deliberately distinct (ratified
# 2026-07-27). A frequency detector can establish that a form is rare in this
# corpus; it cannot establish that the form is unknown to Hittitology. Only a
# trained specialist can assert the latter, so extraction never sets
# LEXICAL_UNKNOWN -- it is reachable solely through expert adjudication.
DETECTOR_REQUIRED_CATEGORIES = {
    "RARE_FORM": "rare_form_detector",
    "LEXICAL_UNKNOWN": "lexical_unknown_detector",
}
ACTIONS = (
    "ADD_TO_CLUSTER",
    "REMOVE_FROM_CLUSTER",
    "MERGE_CLUSTERS",
    "SPLIT_CLUSTER",
    "PROPOSE_READING",
    "PROPOSE_LANGUAGE",
    "PROPOSE_LEXICAL_IDENTITY",
    "PROPOSE_PHRASE",
    "REJECT_HYPOTHESIS",
    "WITHHOLD_JUDGMENT",
)
PERMITTED_SPLITS = ("train", "dev", "discovery")
EFFECTIVE_STATUSES = (
    "RESOLVED", "RESOLVED_WITH_SOURCE_ANOMALY", "MISSING", "EXPLICIT_EMPTY",
    "MALFORMED", "UNRECOGNIZED", "UNRESOLVED_EXPLICIT_WORD_TAG",
    "UNRESOLVED_LINE_LANGUAGE",
)
EFFECTIVE_SOURCES = (
    "WORD_EXPLICIT", "LINE_INHERITED", "LINE_INHERITED_AFTER_EMPTY_WORD_TAG",
    "UNRESOLVED",
)
LANGUAGE_SCOPES = (
    "HITTITE_ONLY", "SAME_LANGUAGE_AS_QUERY", "MULTILINGUAL_CONDITIONED",
    "CROSS_LANGUAGE_PARALLEL", "ALL_LANGUAGES_UNCONDITIONED",
)

# Actions that express a substantive hypothesis and therefore require one.
HYPOTHESIS_ACTIONS = frozenset({
    "PROPOSE_READING", "PROPOSE_LANGUAGE", "PROPOSE_LEXICAL_IDENTITY",
    "PROPOSE_PHRASE",
})
# Organizational actions. These also use the `hypothesis` object, but only to
# carry the cluster identifiers they operate on -- structure, not a claim
# about the text. The required key differs per action.
CLUSTER_ACTION_KEYS = {
    "ADD_TO_CLUSTER": "cluster_id",
    "REMOVE_FROM_CLUSTER": "cluster_id",
    "MERGE_CLUSTERS": "merged_cluster_ids",
    "SPLIT_CLUSTER": "split_into",
}
# Withholding judgment while attaching a hypothesis is a contradiction the log
# should not be able to record.
NO_HYPOTHESIS_ACTIONS = frozenset({"WITHHOLD_JUDGMENT"})


class WorkbenchError(ValueError):
    """Raised when a workbench record violates a contract invariant."""


def canonical_sha256(value):
    """Hash a JSON-compatible value using canonical compact serialization.

    Identical to the expert-decision contract's hashing so a missing-text
    decision and a workbench event bind records the same way.
    """
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _require(mapping, fields, label):
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise WorkbenchError(f"{label}: missing required field(s) {missing}")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ location

def build_location(
        *, doc_id, fragment_id, line_index_in_doc, word_index_in_line,
        token_start, token_end, main_split, source_archive_member,
        source_payload_sha256):
    """One occurrence's exact source location.

    `line_index_in_doc` and the token span are nullable as of contract 1.1.0:
    a PARSER_ANOMALY recorded outside the primary `<text>` has no enclosing
    line, and a sentinel would be fabricated location data.
    """
    if main_split not in PERMITTED_SPLITS:
        raise WorkbenchError(
            f"location: main_split {main_split!r} is not permitted in the "
            "workbench development universe; protected-test material must "
            "never be extracted or displayed")
    return {
        "doc_id": doc_id,
        "fragment_id": fragment_id,
        "line_index_in_doc": line_index_in_doc,
        "word_index_in_line": word_index_in_line,
        "token_start": token_start,
        "token_end": token_end,
        "main_split": main_split,
        "source_archive_member": source_archive_member,
        "source_payload_sha256": source_payload_sha256,
    }


def build_language_assignment(
        *, document, line, word, effective, effective_status,
        effective_source):
    """Document/line/word/effective language, kept separate by design.

    Gate 0 decision 5: document language is provenance only and is never an
    effective-language fallback. Preserving all four values lets an expert see
    not just which language was assigned but which source span decided it.
    """
    if effective_status not in EFFECTIVE_STATUSES:
        raise WorkbenchError(
            f"language: unknown effective_status {effective_status!r}")
    if effective_source not in EFFECTIVE_SOURCES:
        raise WorkbenchError(
            f"language: unknown effective_source {effective_source!r}")
    return {
        "document": document,
        "line": line,
        "word": word,
        "effective": effective,
        "effective_status": effective_status,
        "effective_source": effective_source,
    }


def build_provenance(
        *, split_manifest_hash, language_layer_hash, config_hash, git_commit,
        seed, evidence_policy, created_utc=None,
        corpus_version="TLHdig_0.2.0-beta"):
    return {
        "corpus_version": corpus_version,
        "split_manifest_hash": split_manifest_hash,
        "language_layer_hash": language_layer_hash,
        "config_hash": config_hash,
        "git_commit": git_commit,
        "seed": seed,
        "evidence_policy": evidence_policy,
        "created_utc": created_utc or utc_now(),
    }


# ---------------------------------------------------------------- occurrence

def build_occurrence(
        *, occurrence_id, categories, location, language, display, context,
        evidence_classes, assistance_layers, provenance,
        status="UNREVIEWED"):
    occurrence = {
        "record_type": OCCURRENCE_RECORD_TYPE,
        "contract_version": CONTRACT_VERSION,
        "occurrence_id": occurrence_id,
        "categories": sorted(set(categories)),
        "status": status,
        "location": location,
        "language": language,
        "display": display,
        "context": context,
        "evidence_classes": sorted(set(evidence_classes)),
        "assistance_layers": sorted(set(assistance_layers)),
        "provenance": provenance,
        "ground_truth_status": "NOT_CORPUS_TRUTH",
    }
    return validate_occurrence(occurrence)


def validate_occurrence(occurrence):
    """Validate one occurrence and return it unchanged."""
    _require(
        occurrence,
        ["record_type", "contract_version", "occurrence_id", "categories",
         "status", "location", "language", "display", "context",
         "evidence_classes", "assistance_layers", "provenance",
         "ground_truth_status"],
        "occurrence",
    )
    if occurrence["record_type"] != OCCURRENCE_RECORD_TYPE:
        raise WorkbenchError("occurrence: wrong record_type")
    if occurrence["contract_version"] != CONTRACT_VERSION:
        raise WorkbenchError("occurrence: unsupported contract_version")
    if occurrence["ground_truth_status"] != "NOT_CORPUS_TRUTH":
        raise WorkbenchError(
            "occurrence: an extracted occurrence is never corpus truth")
    if occurrence["status"] not in OCCURRENCE_STATUSES:
        raise WorkbenchError("occurrence: unknown status")

    categories = occurrence["categories"]
    if not categories:
        raise WorkbenchError("occurrence: categories must be non-empty")
    unknown = sorted(set(categories) - set(CATEGORIES))
    if unknown:
        raise WorkbenchError(f"occurrence: unknown categories {unknown}")
    if len(set(categories)) != len(categories):
        raise WorkbenchError("occurrence: duplicate categories")

    # Categories remain distinct: an engineering vocabulary miss is not
    # evidence about Hittite lexis, and a rare form is not an unknown one.
    # Each claim about the form itself must name the detector or judgment
    # that produced it, so none can be inferred from a tokenizer OOV alone.
    for category, detector_key in DETECTOR_REQUIRED_CATEGORIES.items():
        if category in categories and not occurrence["context"].get(
                detector_key):
            raise WorkbenchError(
                f"occurrence: {category} requires context.{detector_key} "
                "naming the governed detector or expert judgment that "
                "produced it; it may never be inferred from a tokenizer OOV "
                "or a frequency count alone")

    location = occurrence["location"]
    _require(
        location,
        ["doc_id", "fragment_id", "line_index_in_doc", "word_index_in_line",
         "token_start", "token_end", "main_split", "source_archive_member",
         "source_payload_sha256"],
        "occurrence.location",
    )
    if location["main_split"] not in PERMITTED_SPLITS:
        raise WorkbenchError(
            "occurrence.location: protected-test or unknown split reached the "
            "workbench")
    sha = location["source_payload_sha256"]
    if not isinstance(sha, str) or len(sha) != 64:
        raise WorkbenchError(
            "occurrence.location: source_payload_sha256 must be a sha256 hex "
            "digest -- every occurrence is checksum-anchored to its payload")
    start, end = location["token_start"], location["token_end"]
    if (start is None) != (end is None):
        raise WorkbenchError(
            "occurrence.location: token span must be wholly present or wholly "
            "absent")
    if start is not None and end < start:
        raise WorkbenchError("occurrence.location: token_end precedes start")

    language = occurrence["language"]
    _require(
        language,
        ["document", "line", "word", "effective", "effective_status",
         "effective_source"],
        "occurrence.language",
    )
    if language["effective_status"] not in EFFECTIVE_STATUSES:
        raise WorkbenchError("occurrence.language: unknown effective_status")
    if language["effective_source"] not in EFFECTIVE_SOURCES:
        raise WorkbenchError("occurrence.language: unknown effective_source")

    # An occurrence whose effective language could not be resolved must SAY
    # so through a category, or an expert filtering by language anomaly would
    # never see it. This exists because the first extraction pass dropped 71
    # such tokens on the floor: their line carried no language attribute at
    # all, a state the 1.0.0 category vocabulary could not name.
    if language["effective"] is None and not (
            set(categories) & (LANGUAGE_CATEGORIES | {"PARSER_ANOMALY"})):
        raise WorkbenchError(
            "occurrence: unresolved effective language must be reported "
            f"through a language category {sorted(LANGUAGE_CATEGORIES)} or "
            "PARSER_ANOMALY; an unresolved occurrence may not be filed under "
            "damage categories alone, where a language-anomaly filter would "
            "never surface it")

    # `cu` renders editor-restored content as real glyphs (CLAUDE.md); it is a
    # display field only and must stay out of the clean fields.
    if "cu" in occurrence["display"] and not occurrence["display"].get(
            "cu_is_editorial_restoration_bearing"):
        raise WorkbenchError(
            "occurrence.display: a `cu` preview must be labeled "
            "cu_is_editorial_restoration_bearing=true")

    _require(
        occurrence["provenance"],
        ["corpus_version", "split_manifest_hash", "language_layer_hash",
         "config_hash", "git_commit", "seed", "evidence_policy",
         "created_utc"],
        "occurrence.provenance",
    )
    return occurrence


# ------------------------------------------------------------------ clusters

def build_cluster_proposal(
        *, cluster_id, member_occurrence_ids, method_name, evidence_class,
        model_derived, language_scope, supporting_evidence,
        contradictory_evidence, provenance, status=None):
    """A grouping SUGGESTION over occurrences.

    `status` defaults to the honest one for how the grouping was produced:
    `MODEL_PROPOSAL` when a model was consulted, `SYSTEM_PROPOSAL` when the
    channel is deterministic (contract 1.1.0). Before 1.1.0 the vocabulary had
    no system-proposed value, so a plain string match was labeled a model
    proposal -- which told an expert a model was involved when none was.
    """
    if status is None:
        status = "MODEL_PROPOSAL" if model_derived else "SYSTEM_PROPOSAL"
    cluster = {
        "record_type": CLUSTER_RECORD_TYPE,
        "contract_version": CONTRACT_VERSION,
        "cluster_id": cluster_id,
        "member_occurrence_ids": list(member_occurrence_ids),
        "status": status,
        "method": {
            "name": method_name,
            "evidence_class": evidence_class,
            "model_derived": bool(model_derived),
        },
        "language_scope": language_scope,
        "supporting_evidence": list(supporting_evidence),
        "contradictory_evidence": list(contradictory_evidence),
        # A similarity value is not a probability. The UI is forbidden from
        # relabeling it as one; the flag travels with the record.
        "scores_are_probabilities": False,
        "provenance": provenance,
        "ground_truth_status": "NOT_CORPUS_TRUTH",
    }
    return validate_cluster_proposal(cluster)


def validate_cluster_proposal(cluster):
    _require(
        cluster,
        ["record_type", "contract_version", "cluster_id",
         "member_occurrence_ids", "status", "method", "language_scope",
         "supporting_evidence", "contradictory_evidence",
         "scores_are_probabilities", "provenance", "ground_truth_status"],
        "cluster",
    )
    if cluster["record_type"] != CLUSTER_RECORD_TYPE:
        raise WorkbenchError("cluster: wrong record_type")
    if cluster["contract_version"] != CONTRACT_VERSION:
        raise WorkbenchError("cluster: unsupported contract_version")
    if cluster["status"] not in CLUSTER_STATUSES:
        raise WorkbenchError("cluster: unknown status")
    if cluster["scores_are_probabilities"] is not False:
        raise WorkbenchError(
            "cluster: similarity values are not probabilities")
    if cluster["ground_truth_status"] != "NOT_CORPUS_TRUTH":
        raise WorkbenchError(
            "cluster: even an expert-curated cluster is an annotation "
            "collection, not a corpus fact")
    members = cluster["member_occurrence_ids"]
    if not members:
        raise WorkbenchError("cluster: at least one member is required")
    if len(set(members)) != len(members):
        raise WorkbenchError("cluster: duplicate member occurrence ids")
    if cluster["language_scope"] not in LANGUAGE_SCOPES:
        raise WorkbenchError("cluster: unknown language_scope")
    # A model-derived grouping may not present itself as a deterministic one.
    if cluster["status"] == "SYSTEM_PROPOSAL" and cluster["method"][
            "model_derived"]:
        raise WorkbenchError(
            "cluster: SYSTEM_PROPOSAL asserts a deterministic grouping and "
            "cannot carry method.model_derived=true")
    _require(
        cluster["method"], ["name", "evidence_class", "model_derived"],
        "cluster.method")
    return cluster


# -------------------------------------------------------------------- events

def build_annotation_event(
        *, event_id, action, target_id, reviewed_record, prior_event_sha256,
        reviewer_id, declared_role, hypothesis=None, rationale=None,
        created_utc=None):
    """One append-only expert action, hash-bound to what was reviewed.

    `reviewed_record` is the full record the expert saw; its canonical hash is
    stored so a later mutation of that record is detectable rather than
    silently inherited by the annotation.
    """
    event = {
        "record_type": EVENT_RECORD_TYPE,
        "contract_version": CONTRACT_VERSION,
        "event_id": event_id,
        "action": action,
        "target_id": target_id,
        "reviewed_record_sha256": canonical_sha256(reviewed_record),
        "prior_event_sha256": prior_event_sha256,
        "reviewer": {"reviewer_id": reviewer_id, "declared_role": declared_role},
        "hypothesis": hypothesis,
        "rationale": rationale,
        # Not a checkbox: the expert is recorded as having been told which
        # assistance layers shaped what they saw.
        "assistance_acknowledged": True,
        "created_utc": created_utc or utc_now(),
        "ground_truth_status": "QUARANTINED_EXPERT_JUDGMENT",
        "requires_adjudication": True,
    }
    return validate_annotation_event(event)


def validate_annotation_event(event):
    _require(
        event,
        ["record_type", "contract_version", "event_id", "action", "target_id",
         "reviewed_record_sha256", "prior_event_sha256", "reviewer",
         "hypothesis", "rationale", "assistance_acknowledged", "created_utc",
         "ground_truth_status", "requires_adjudication"],
        "event",
    )
    if event["record_type"] != EVENT_RECORD_TYPE:
        raise WorkbenchError("event: wrong record_type")
    if event["contract_version"] != CONTRACT_VERSION:
        raise WorkbenchError("event: unsupported contract_version")
    if event["action"] not in ACTIONS:
        raise WorkbenchError(f"event: unknown action {event['action']!r}")
    if event["assistance_acknowledged"] is not True:
        raise WorkbenchError("event: assistance must be acknowledged")
    if event["ground_truth_status"] != "QUARANTINED_EXPERT_JUDGMENT":
        raise WorkbenchError(
            "event: an expert judgment is quarantined, never corpus truth")
    if event["requires_adjudication"] is not True:
        raise WorkbenchError(
            "event: promotion to a training artifact requires a separate "
            "adjudication gate")
    sha = event["reviewed_record_sha256"]
    if not isinstance(sha, str) or len(sha) != 64:
        raise WorkbenchError("event: reviewed_record_sha256 must be a digest")
    prior = event["prior_event_sha256"]
    if prior is not None and (not isinstance(prior, str) or len(prior) != 64):
        raise WorkbenchError("event: prior_event_sha256 must be a digest/null")
    _require(event["reviewer"], ["reviewer_id", "declared_role"], "event.reviewer")

    action = event["action"]
    if action in HYPOTHESIS_ACTIONS and not event["hypothesis"]:
        raise WorkbenchError(
            f"event: {action} requires an explicit hypothesis")
    if action in NO_HYPOTHESIS_ACTIONS and event["hypothesis"]:
        raise WorkbenchError(f"event: {action} cannot carry a hypothesis")
    if action in CLUSTER_ACTION_KEYS:
        key = CLUSTER_ACTION_KEYS[action]
        if not (event["hypothesis"] or {}).get(key):
            raise WorkbenchError(
                f"event: {action} requires hypothesis.{key} naming the "
                "cluster(s) it operates on")
    return event


class AnnotationEventLog:
    """Append-only, hash-chained expert event log.

    Appending is the only mutation. The chain makes a silent rewrite of
    history detectable: each event stores its predecessor's hash, so removing
    or editing an earlier event breaks every later link.
    """

    def __init__(self, events=()):
        self._events = []
        for event in events:
            self._append_validated(validate_annotation_event(dict(event)))

    def _append_validated(self, event):
        expected = self.head_sha256()
        if event["prior_event_sha256"] != expected:
            raise WorkbenchError(
                "event log: prior_event_sha256 does not match the current "
                f"head ({expected!r}); the log is append-only and its chain "
                "may not be rewritten or reordered")
        self._events.append(event)

    def head_sha256(self):
        return canonical_sha256(self._events[-1]) if self._events else None

    def append(self, **kwargs):
        """Build, validate, and append one event onto the current head."""
        kwargs.setdefault("prior_event_sha256", self.head_sha256())
        event = build_annotation_event(**kwargs)
        self._append_validated(event)
        return event

    def __len__(self):
        return len(self._events)

    def __iter__(self):
        return iter(self._events)

    @property
    def events(self):
        return list(self._events)

    def verify_chain(self):
        """Re-verify the whole chain; raises on the first broken link."""
        prior = None
        for index, event in enumerate(self._events):
            if event["prior_event_sha256"] != prior:
                raise WorkbenchError(
                    f"event log: chain broken at event {index} "
                    f"({event['event_id']!r})")
            prior = canonical_sha256(event)
        return True


def project_snapshot(events, *, occurrence_ids=()):
    """Deterministically project current state from the event log.

    A snapshot is never stored as independent mutable state; it is recomputed
    from the log, so it cannot drift from the record of what an expert
    actually did. Replaying the same events always yields the same snapshot.

    Returns
        {"occurrences": {occurrence_id: {status, clusters, hypotheses}},
         "clusters":    {cluster_id: {members, status}}}
    """
    occurrences = {}
    clusters = {}

    def occurrence(occurrence_id):
        return occurrences.setdefault(occurrence_id, {
            "status": "UNREVIEWED", "clusters": [], "hypotheses": [],
        })

    def cluster(cluster_id):
        return clusters.setdefault(
            cluster_id, {"members": [], "status": "EXPERT_CURATED"})

    def join(occurrence_id, cluster_id):
        record = occurrence(occurrence_id)
        if cluster_id not in record["clusters"]:
            record["clusters"].append(cluster_id)
        members = cluster(cluster_id)["members"]
        if occurrence_id not in members:
            members.append(occurrence_id)
        if record["status"] == "UNREVIEWED":
            record["status"] = "GROUPED"

    def leave(occurrence_id, cluster_id):
        record = occurrence(occurrence_id)
        if cluster_id in record["clusters"]:
            record["clusters"].remove(cluster_id)
        members = cluster(cluster_id)["members"]
        if occurrence_id in members:
            members.remove(occurrence_id)
        if not record["clusters"] and record["status"] == "GROUPED":
            record["status"] = "UNREVIEWED"

    for occurrence_id in occurrence_ids:
        occurrence(occurrence_id)

    for event in events:
        validate_annotation_event(event)
        action, target = event["action"], event["target_id"]
        hypothesis = event["hypothesis"] or {}

        if action == "ADD_TO_CLUSTER":
            join(target, hypothesis["cluster_id"])
        elif action == "REMOVE_FROM_CLUSTER":
            leave(target, hypothesis["cluster_id"])
        elif action == "MERGE_CLUSTERS":
            # target_id is the surviving cluster; the named clusters are
            # emptied into it. Their records are retained (never deleted) so
            # the log's history stays inspectable.
            for source_id in hypothesis["merged_cluster_ids"]:
                for occurrence_id in list(cluster(source_id)["members"]):
                    leave(occurrence_id, source_id)
                    join(occurrence_id, target)
                cluster(source_id)["status"] = "REJECTED"
        elif action == "SPLIT_CLUSTER":
            # hypothesis.split_into maps new cluster id -> member occurrence
            # ids drawn out of the target cluster.
            for new_id, member_ids in hypothesis["split_into"].items():
                for occurrence_id in member_ids:
                    leave(occurrence_id, target)
                    join(occurrence_id, new_id)
        elif action in HYPOTHESIS_ACTIONS:
            record = occurrence(target)
            record["hypotheses"].append({
                "action": action,
                "hypothesis": event["hypothesis"],
                "event_id": event["event_id"],
                "reviewer_id": event["reviewer"]["reviewer_id"],
            })
            # A recorded hypothesis is HYPOTHESIS. Nothing in this projection
            # promotes it to EXPERT_SUPPORTED automatically -- that status
            # means a named reviewer endorsed it, and even then it is not
            # corpus truth or consensus.
            record["status"] = "HYPOTHESIS"
        elif action == "REJECT_HYPOTHESIS":
            occurrence(target)["status"] = "REJECTED"
        elif action == "WITHHOLD_JUDGMENT":
            occurrence(target)["status"] = "WITHHELD"

    return {
        "occurrences": dict(sorted(occurrences.items())),
        "clusters": dict(sorted(clusters.items())),
    }
