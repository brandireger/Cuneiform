"""Determinism-hash tests for the P4-E clustering channel.

The clustering manifest originally recorded only a hash of the candidates
FILE. Every record in that file embeds `provenance.created_utc` and
`git_commit`, so that hash changed on every rerun regardless of content --
which made the workbench's standing determinism check ("compare the logical
hash; if it changes, stop and diagnose") inapplicable to this channel.
`logical_hash` closes that gap, and these tests pin the property that makes it
worth having: insensitive to when a grouping was proposed, sensitive to what
it groups.
"""
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lib"))

import phase4_unresolved_clustering as clustering  # noqa: E402
import unresolved_evidence as ue  # noqa: E402


def make_proposal(cluster_id="seq-s-00001", members=("occ-a", "occ-b"),
                  created_utc="2026-07-27T00:00:00+00:00",
                  git_commit="a" * 40):
    return ue.build_cluster_proposal(
        cluster_id=cluster_id,
        member_occurrence_ids=list(members),
        method_name="exact_normalized_sign_sequence",
        evidence_class="EDITORIAL_TRANSCRIPTION",
        model_derived=False,
        language_scope="SAME_LANGUAGE_AS_QUERY",
        supporting_evidence=[{
            "type": "EXACT_NORMALIZED_SIGN_SEQUENCE",
            "sequence": "ku",
            "member_count": len(members),
            "distinct_document_count": 2,
            "languages": ["Hit"],
            "value_is_a_count_not_a_score": True,
        }],
        contradictory_evidence=[],
        provenance=ue.build_provenance(
            split_manifest_hash="0" * 64,
            language_layer_hash="1" * 64,
            config_hash="2" * 64,
            git_commit=git_commit,
            seed=20260726,
            evidence_policy="transcription_assisted",
            created_utc=created_utc,
        ),
    )


class TestClusteringLogicalHash(unittest.TestCase):
    def test_provenance_does_not_affect_the_logical_hash(self):
        """A later rerun of an unchanged grouping must hash identically."""
        first = make_proposal()
        later = make_proposal(
            created_utc="2027-01-01T12:00:00+00:00", git_commit="b" * 40)
        self.assertNotEqual(first["provenance"], later["provenance"])
        self.assertEqual(
            clustering.logical_hash([first]), clustering.logical_hash([later]))

    def test_membership_change_does_affect_the_logical_hash(self):
        baseline = make_proposal()
        changed = make_proposal(members=("occ-a", "occ-c"))
        self.assertNotEqual(
            clustering.logical_hash([baseline]),
            clustering.logical_hash([changed]))

    def test_supporting_evidence_change_does_affect_the_logical_hash(self):
        baseline = make_proposal()
        changed = copy.deepcopy(baseline)
        changed["supporting_evidence"][0]["sequence"] = "ta"
        self.assertNotEqual(
            clustering.logical_hash([baseline]),
            clustering.logical_hash([changed]))

    def test_emission_order_does_not_affect_the_logical_hash(self):
        """Proposals are hashed in cluster-id order, not arrival order."""
        one = make_proposal(cluster_id="seq-s-00001")
        two = make_proposal(cluster_id="seq-s-00002", members=("occ-c", "occ-d"))
        self.assertEqual(
            clustering.logical_hash([one, two]),
            clustering.logical_hash([two, one]))

    def test_language_scope_change_does_affect_the_logical_hash(self):
        """The two channels must never hash alike on the same membership."""
        same = make_proposal()
        cross = copy.deepcopy(same)
        cross["language_scope"] = "CROSS_LANGUAGE_PARALLEL"
        self.assertNotEqual(
            clustering.logical_hash([same]), clustering.logical_hash([cross]))


if __name__ == "__main__":
    unittest.main()
