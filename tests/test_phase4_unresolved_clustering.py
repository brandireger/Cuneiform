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


def make_row(occurrence_id, tokens, left, right, doc_id="KUB 1.1",
             language="Hit"):
    return {
        "occurrence_id": occurrence_id, "language": language,
        "doc_id": doc_id, "main_split": "train", "categories": [],
        "tokens": tokens, "left": left, "right": right,
    }


class TestUngroupedBySequence(unittest.TestCase):
    def test_unique_sequence_is_ungrouped(self):
        rows = [make_row("occ-a", ["ku"], ["nu"], ["zi"])]
        self.assertEqual(
            [r["occurrence_id"] for r in clustering.ungrouped_by_sequence(rows)],
            ["occ-a"])

    def test_shared_sequence_is_not_ungrouped(self):
        rows = [
            make_row("occ-a", ["ku"], ["nu"], ["zi"]),
            make_row("occ-b", ["ku"], ["ta"], ["an"], doc_id="KUB 2.2"),
        ]
        self.assertEqual(clustering.ungrouped_by_sequence(rows), [])

    def test_cross_language_duplicate_is_still_ungrouped(self):
        """Grouping is per-language, matching build_clusters()'s own
        same-language default -- a Hittite 'ku' and an Akkadian 'ku' are not
        the same evidence."""
        rows = [
            make_row("occ-a", ["ku"], ["nu"], ["zi"], language="Hit"),
            make_row("occ-b", ["ku"], ["ta"], ["an"], language="Akk"),
        ]
        ungrouped_ids = {r["occurrence_id"]
                          for r in clustering.ungrouped_by_sequence(rows)}
        self.assertEqual(ungrouped_ids, {"occ-a", "occ-b"})


class TestBuildContextClusters(unittest.TestCase):
    def test_matching_flanking_context_joins_a_cluster(self):
        rows = [
            make_row("occ-a", ["ku"], ["nu"], ["zi"], doc_id="KUB 1.1"),
            make_row("occ-b", ["ta"], ["nu"], ["zi"], doc_id="KUB 2.2"),
        ]
        clusters = clustering.build_context_clusters(rows, window=1)
        self.assertEqual(len(clusters), 1)
        member_ids = {m["occurrence_id"] for m in clusters[0]["members"]}
        self.assertEqual(member_ids, {"occ-a", "occ-b"})

    def test_own_sequence_content_is_irrelevant_to_grouping(self):
        """The whole point: occ-a and occ-b have DIFFERENT own content but
        the same immediate environment, which is exactly what a
        same-sequence cluster (build_clusters()) cannot see."""
        rows = [
            make_row("occ-a", ["ku"], ["nu"], ["zi"]),
            make_row("occ-b", ["ta", "an"], ["nu"], ["zi"], doc_id="KUB 2.2"),
        ]
        clusters = clustering.build_context_clusters(rows, window=1)
        self.assertEqual(len(clusters), 1)

    def test_mismatched_context_does_not_join(self):
        rows = [
            make_row("occ-a", ["ku"], ["nu"], ["zi"]),
            make_row("occ-b", ["ta"], ["nu"], ["different"], doc_id="KUB 2.2"),
        ]
        self.assertEqual(clustering.build_context_clusters(rows, window=1), [])

    def test_context_shorter_than_window_is_excluded_not_padded(self):
        """A run at the very start or end of a line has no token on that
        side. It must be excluded from this channel, not silently matched
        on a shorter (weaker) window than every other member used."""
        rows = [
            make_row("occ-a", ["ku"], [], ["zi"]),
            make_row("occ-b", ["ta"], ["nu"], ["zi"], doc_id="KUB 2.2"),
        ]
        self.assertEqual(clustering.build_context_clusters(rows, window=1), [])

    def test_a_sequence_peer_is_excluded_from_the_context_channel(self):
        """An occurrence that already clusters by exact sequence must not
        ALSO appear in the context channel -- the two channels partition
        the population (well-grouped vs. not), they do not overlap."""
        rows = [
            make_row("occ-a", ["ku"], ["nu"], ["zi"], doc_id="KUB 1.1"),
            make_row("occ-b", ["ku"], ["nu"], ["zi"], doc_id="KUB 2.2"),
            make_row("occ-c", ["mu"], ["nu"], ["zi"], doc_id="KUB 3.3"),
            make_row("occ-d", ["pu"], ["nu"], ["zi"], doc_id="KUB 4.4"),
        ]
        clusters = clustering.build_context_clusters(rows, window=1)
        member_ids = {m["occurrence_id"]
                      for c in clusters for m in c["members"]}
        # occ-a/occ-b share a sequence ("ku"), so they are NOT ungrouped and
        # must not appear here even though their context ("nu"/"zi") matches
        # occ-c and occ-d's.
        self.assertNotIn("occ-a", member_ids)
        self.assertNotIn("occ-b", member_ids)
        self.assertIn("occ-c", member_ids)
        self.assertIn("occ-d", member_ids)

    def test_single_document_cluster_is_flagged_via_documents_field(self):
        rows = [
            make_row("occ-a", ["ku"], ["nu"], ["zi"], doc_id="KUB 1.1"),
            make_row("occ-b", ["ta"], ["nu"], ["zi"], doc_id="KUB 1.1"),
        ]
        clusters = clustering.build_context_clusters(rows, window=1)
        self.assertEqual(clusters[0]["documents"], ["KUB 1.1"])


if __name__ == "__main__":
    unittest.main()
