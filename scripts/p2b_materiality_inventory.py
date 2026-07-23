#!/usr/bin/env python3
"""Phase 2 P2-B probe: inventory material evidence encoded by TLHdig.

Raw XML is admitted by filename only after the frozen split map proves the
entry is non-test.  Test, ambiguous, and unmatched filenames are skipped
before decompression and parsing.  The probe records aggregate schema and
coverage counts, never raw text or attribute values.

Usage:
    python scripts/p2b_materiality_inventory.py
"""

import hashlib
import json
import math
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path, PurePosixPath

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import contracts
import evidence_policy as ep
from phase2_io import split_lookup_fail_closed


SEED = 20260723
TIME_BUDGET_HOURS = 2
CORPUS_ZIP = Path("TLHdig_0.2.0-beta.zip")
P2_OUT = Path("p2_out")
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2b_materiality_inventory.json"
MANIFEST_PATH = OUT_DIR / "p2b_materiality_inventory_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2b_materiality_inventory.md"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"

DIRECT_MEDIA_EXTENSIONS = {
    ".bmp", ".dae", ".e57", ".exr", ".fbx", ".gif", ".glb", ".gltf",
    ".jpeg", ".jpg", ".las", ".laz", ".obj", ".off", ".ply", ".png",
    ".ptx", ".stl", ".tif", ".tiff", ".webp",
}

ABSENT_SCHEMA_TERM_GROUPS = {
    "metric_geometry": (
        "height", "width", "thickness", "curvature", "contour",
        "coordinate", "surfaceprofile", "breakprofile",
    ),
    "clay_material": (
        "clay", "fabric", "texture", "colour", "color", "composition",
    ),
    "graphetic_hand": (
        "paleography", "palaeography", "ductus", "wedge", "scribe",
        "ancienthand",
    ),
    "linked_media": (
        "pointcloud", "mesh", "photograph", "photo", "image", "scan",
    ),
}

SOURCES = [
    {
        "title": "Würzburg 3D-Joins und Schriftmetrologie",
        "url": (
            "https://www.phil.uni-wuerzburg.de/altorientalistik/"
            "forschung/abgeschlossene-forschungsvorhaben/"
            "3d-joins-und-schriftmetrologie/"
        ),
        "use": (
            "3D optical measurements, script-feature analysis, fragment "
            "reconstruction, and handwriting study"
        ),
    },
    {
        "title": "Hethitologie-Portal Mainz 3D-Joins",
        "url": "https://www.hethport.uni-wuerzburg.de/HPM/hpm.php?p=3djoins",
        "use": (
            "high-resolution point clouds, fragment contours, 3D writing/"
            "carrier analysis, and the limits of content for repetitive text"
        ),
    },
    {
        "title": "Observed methods of cuneiform tablet reconstruction",
        "url": (
            "https://www.sciencedirect.com/science/article/pii/"
            "S0305440314003690"
        ),
        "use": (
            "physical dimensions and observed reconstruction cues including "
            "surface markings and colour"
        ),
    },
    {
        "title": "Nineveh Medical Project: About the sources",
        "url": (
            "https://oracc.museum.upenn.edu/asbp/ninmed/"
            "Aboutthesources/index.html"
        ),
        "use": (
            "distinction between direct profile matches and indirect "
            "same-tablet joins separated by missing clay"
        ),
    },
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_name(name):
    return name.rsplit("}", 1)[-1]


def is_junk_archive_name(name):
    leaf = PurePosixPath(name).name
    return "__MACOSX" in name or leaf.startswith("._")


def archive_access_status(name, split_lookup, ambiguous_ids):
    """Classify an XML entry without reading its bytes."""
    stem = PurePosixPath(name).stem
    if stem in ambiguous_ids:
        return "ambiguous_stem_skipped"
    split = split_lookup.get(stem)
    if split is None:
        return "unmatched_stem_skipped"
    if split == "test":
        return "test_skipped_before_read"
    return "allowed"


def scan_non_test_schema(zip_path, split_lookup, ambiguous_ids):
    status = Counter()
    tag_instances = Counter()
    attribute_instances = Counter()
    tag_documents = Counter()
    attribute_documents = Counter()
    extension_counts = Counter()

    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if name.endswith("/") or is_junk_archive_name(name):
                continue
            suffix = PurePosixPath(name).suffix.lower() or "<none>"
            extension_counts[suffix] += 1
            if suffix != ".xml":
                continue

            status["xml_files"] += 1
            access = archive_access_status(
                name, split_lookup, ambiguous_ids)
            if access != "allowed":
                status[access] += 1
                continue

            status["allowed_read"] += 1
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError:
                status["allowed_parse_error"] += 1
                continue

            status["allowed_parsed"] += 1
            document_tags = set()
            document_attributes = set()
            for element in root.iter():
                tag = local_name(element.tag)
                tag_instances[tag] += 1
                document_tags.add(tag)
                for attribute in element.attrib:
                    key = f"{tag}@{local_name(attribute)}"
                    attribute_instances[key] += 1
                    document_attributes.add(key)
            tag_documents.update(document_tags)
            attribute_documents.update(document_attributes)

    media_counts = {
        extension: extension_counts[extension]
        for extension in sorted(DIRECT_MEDIA_EXTENSIONS)
        if extension_counts[extension]
    }
    return {
        "status": dict(status),
        "tag_instances": dict(tag_instances),
        "attribute_instances": dict(attribute_instances),
        "tag_documents": dict(tag_documents),
        "attribute_documents": dict(attribute_documents),
        "archive_extension_counts": dict(sorted(extension_counts.items())),
        "direct_media_extension_counts": media_counts,
    }


def present(value):
    return (
        value is not None
        and value != ""
        and not (isinstance(value, float) and math.isnan(value))
    )


def schema_term_matches(schema):
    """Return future-schema fields that invalidate current absence claims."""
    names = (
        set(schema["tag_instances"])
        | set(schema["attribute_instances"])
    )
    normalized = {
        name: "".join(character for character in name.lower()
                      if character.isalnum())
        for name in names
    }
    matches = {}
    for group, terms in ABSENT_SCHEMA_TERM_GROUPS.items():
        group_matches = sorted(
            name for name, clean_name in normalized.items()
            if any(term in clean_name for term in terms)
        )
        matches[group] = group_matches
    return matches


def summarize_edges(split_lookup):
    allowed_parents = {
        doc_id for doc_id, split in split_lookup.items() if split != "test"
    }
    edges = pd.read_parquet(P2_OUT / "edges.parquet")
    edges = edges[edges["parent_doc"].isin(allowed_parents)].copy()
    contracts.assert_unique_docids(edges)
    fragment_splits = {
        fragment_id: split_lookup[parent_doc]
        for fragment_id, parent_doc
        in zip(edges["fragment_id"], edges["parent_doc"])
    }
    contracts.assert_no_test(
        edges["fragment_id"], fragment_splits,
        label="P2-B non-test edge universe")

    def true_count(column):
        return int(edges[column].fillna(False).astype(bool).sum())

    line_counts = Counter()
    line_total = 0
    for encoded_lines in edges["lines"]:
        for line in json.loads(encoded_lines):
            line_total += 1
            for field in (
                    "side", "column", "line_label", "leading_space_c",
                    "on_physical_edge", "left_edge_state",
                    "right_edge_state"):
                if present(line.get(field)):
                    line_counts[field] += 1

    return {
        "fragments": len(edges),
        "parent_documents": edges["parent_doc"].nunique(),
        "top_edge_lost": true_count("top_edge_lost"),
        "bottom_edge_lost": true_count("bottom_edge_lost"),
        "top_edge_confirmed_preserved":
            true_count("top_edge_confirmed_preserved"),
        "bottom_edge_confirmed_preserved":
            true_count("bottom_edge_confirmed_preserved"),
        "preserves_left_edge": true_count("preserves_left_edge"),
        "preserves_right_edge": true_count("preserves_right_edge"),
        "top_edge_gap_description": int(
            edges["top_edge_gap_desc"].fillna("").astype(str).str.strip()
            .ne("").sum()
        ),
        "bottom_edge_gap_description": int(
            edges["bottom_edge_gap_desc"].fillna("").astype(str).str.strip()
            .ne("").sum()
        ),
        "embedded_fragment_lines": line_total,
        "line_field_nonempty": dict(line_counts),
    }


def summarize_sites(splits):
    grouped = splits.groupby("doc_id", sort=False).agg(
        splits=("main_split", lambda values: frozenset(values)),
        sites=("site", lambda values: frozenset(values)),
    )
    allowed = grouped[
        (grouped["splits"].map(len) == 1)
        & grouped["splits"].map(lambda values: next(iter(values)) != "test")
    ]
    if any(allowed["sites"].map(len) != 1):
        raise AssertionError("P2-B site summary found ambiguous site labels")
    sites = allowed["sites"].map(lambda values: next(iter(values)))
    counts = sites.value_counts().to_dict()
    return {
        "documents": len(sites),
        "recognized_site_documents": int((sites != "unknown").sum()),
        "unknown_site_documents": int((sites == "unknown").sum()),
        "counts": counts,
    }


def coverage(count, denominator):
    return {
        "count": int(count),
        "denominator": int(denominator),
        "percent": 100.0 * count / denominator if denominator else None,
    }


def build_matrix(schema, edges, sites):
    parsed_docs = schema["status"]["allowed_parsed"]
    tag_docs = Counter(schema["tag_documents"])
    line_total = edges["embedded_fragment_lines"]
    line_fields = Counter(edges["line_field_nonempty"])
    media_files = sum(schema["direct_media_extension_counts"].values())

    return [
        {
            "signal": "line sequence and line labels",
            "status": "USABLE_SYMBOLIC",
            "coverage": coverage(line_fields["line_label"], line_total),
            "encoded_as": "lb order; lb@lnr; edges.lines.line_label",
            "limit": "symbolic order/labels, not metric coordinates",
        },
        {
            "signal": "tablet side and column",
            "status": "PARTIAL_PROXY",
            "coverage": {
                "side": coverage(line_fields["side"], line_total),
                "column": coverage(line_fields["column"], line_total),
            },
            "encoded_as": "line labels and clb-derived side/column fields",
            "limit": "missing on many lines; no physical coordinate frame",
        },
        {
            "signal": "rulings and paragraph boundaries",
            "status": "USABLE_SYMBOLIC",
            "coverage": {
                "parsep_documents": coverage(
                    tag_docs["parsep"], parsed_docs),
                "double_parsep_documents": coverage(
                    tag_docs["parsep_dbl"], parsed_docs),
            },
            "encoded_as": "parsep / parsep_dbl",
            "limit": "presence and order only; no ruling depth or geometry",
        },
        {
            "signal": "blank runs, gaps, and damage states",
            "status": "PARTIAL_PROXY",
            "coverage": {
                "space_documents": coverage(tag_docs["space"], parsed_docs),
                "gap_documents": coverage(tag_docs["gap"], parsed_docs),
                "line_edge_states": coverage(
                    line_fields["left_edge_state"], line_total),
            },
            "encoded_as": (
                "space@c, gap@c/t, damage markup, edge-state summaries"
            ),
            "limit": (
                "editorial structural encoding; not measured fracture shape"
            ),
        },
        {
            "signal": "preserved physical edge identity",
            "status": "SPARSE_DIRECT",
            "coverage": {
                "physical_edge_lines": coverage(
                    line_fields["on_physical_edge"], line_total),
                "left_edge_fragments": coverage(
                    edges["preserves_left_edge"], edges["fragments"]),
                "right_edge_fragments": coverage(
                    edges["preserves_right_edge"], edges["fragments"]),
            },
            "encoded_as": "on_physical_edge and derived fragment flags",
            "limit": (
                "very sparse; top/bottom loss is mostly heuristic, not a "
                "measured break profile"
            ),
        },
        {
            "signal": "publication, inventory, and site metadata",
            "status": "PARTIAL_PROXY",
            "coverage": {
                "publication_documents": coverage(
                    tag_docs["TxtPubl"], parsed_docs),
                "inventory_number_documents": coverage(
                    tag_docs["InvNr"], parsed_docs),
                "excavation_number_documents": coverage(
                    tag_docs["ExcNr"], parsed_docs),
                "recognized_prefix_site_documents": coverage(
                    sites["recognized_site_documents"], sites["documents"]),
            },
            "encoded_as": "TxtPubl, sparse InvNr/ExcNr, filename-prefix site",
            "limit": (
                "site is derived and coarse; no room, locus, findspot, or "
                "stratigraphic context"
            ),
        },
        {
            "signal": "join relation notation",
            "status": "EDITORIAL_RELATION_ONLY",
            "coverage": {
                "direct_join_tag_documents": coverage(
                    tag_docs["DirectJoin"], parsed_docs),
                "indirect_join_tag_documents": coverage(
                    tag_docs["InDirectJoin"], parsed_docs),
            },
            "encoded_as": (
                "TxtPubl separators, DirectJoin/InDirectJoin, line sigla"
            ),
            "limit": (
                "label/provenance evidence, not independent physical "
                "measurement or certainty"
            ),
        },
        {
            "signal": "2D photographs, drawings, or scans",
            "status": "ABSENT",
            "coverage": coverage(media_files, sum(
                schema["archive_extension_counts"].values())),
            "encoded_as": None,
            "limit": "no image/media extensions in the distributed archive",
        },
        {
            "signal": "3D mesh, point cloud, and fracture contour",
            "status": "ABSENT",
            "coverage": coverage(media_files, sum(
                schema["archive_extension_counts"].values())),
            "encoded_as": None,
            "limit": "no 3D/media payload or metric contour coordinates",
        },
        {
            "signal": "dimensions, thickness, curvature, and surface profile",
            "status": "ABSENT",
            "coverage": coverage(0, parsed_docs),
            "encoded_as": None,
            "limit": "no corresponding element/attribute in the safe schema",
        },
        {
            "signal": "clay colour, fabric, texture, and composition",
            "status": "ABSENT",
            "coverage": coverage(0, parsed_docs),
            "encoded_as": None,
            "limit": "no corresponding element/attribute in the safe schema",
        },
        {
            "signal": "wedge shape, ductus, paleography, and scribal hand",
            "status": "ABSENT",
            "coverage": coverage(0, parsed_docs),
            "encoded_as": None,
            "limit": (
                "transliteration identifies signs but carries no graphetic "
                "shape, wedge coordinates, or ancient-hand label"
            ),
        },
    ]


def write_report(summary, elapsed_seconds):
    matrix = {row["signal"]: row for row in summary["materiality_matrix"]}
    schema = summary["safe_schema_scan"]
    edges = summary["edge_summary"]

    def percent(signal, key=None):
        item = matrix[signal]["coverage"]
        if key is not None:
            item = item[key]
        return item["percent"]

    lines = [
        "# Phase 2 P2-B materiality inventory",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Question",
        "",
        "Which physical and structural signals used to assess cuneiform "
        "joins are encoded in TLHdig, and which are absent?",
        "",
        "## What I did",
        "",
        f"Scanned aggregate tag/attribute names for "
        f"{schema['status']['allowed_parsed']:,} filename-gated non-test XML "
        "files and measured the governed non-test edge universe "
        f"({edges['fragments']:,} fragments; {edges['embedded_fragment_lines']:,} "
        "embedded lines). Test entries were skipped before decompression. "
        "The checklist is cross-referenced to Würzburg/HPM 3D-join work, "
        "the observed-reconstruction study, and ORACC's direct/indirect "
        "join distinction.",
        "",
        "## What I found",
        "",
        "| signal | corpus status | measured coverage / limitation |",
        "|---|---|---|",
        f"| line order and labels | usable symbolic | "
        f"{percent('line sequence and line labels'):.1f}% of fragment lines; "
        "no metric coordinates |",
        f"| side / column | partial proxy | "
        f"{percent('tablet side and column', 'side'):.1f}% / "
        f"{percent('tablet side and column', 'column'):.1f}% of lines |",
        f"| rulings / paragraphs | usable symbolic | "
        f"`parsep` in {percent('rulings and paragraph boundaries', 'parsep_documents'):.1f}% "
        "of safe XML documents; no ruling geometry |",
        f"| gaps, blank widths, edge damage | partial proxy | gaps in "
        f"{percent('blank runs, gaps, and damage states', 'gap_documents'):.1f}% "
        "of documents; editorial encoding, not a measured fracture |",
        f"| explicitly preserved physical edge | sparse direct | "
        f"{percent('preserved physical edge identity', 'physical_edge_lines'):.1f}% "
        "of fragment lines carry an edge direction |",
        f"| publication / inventory / site | partial proxy | inventory number "
        f"in {percent('publication, inventory, and site metadata', 'inventory_number_documents'):.1f}%; "
        f"prefix-site recognized for "
        f"{percent('publication, inventory, and site metadata', 'recognized_prefix_site_documents'):.1f}%; "
        "no locus/room/stratigraphy |",
        "| editorial direct/indirect relation | label only | encoded, but "
        "not independent physical evidence or certainty |",
        "| photos, drawings, 3D mesh, point cloud | absent | zero media/3D "
        "files in the distributed archive |",
        "| dimensions, thickness, curvature, break contour | absent | no "
        "safe-schema field or metric coordinate payload |",
        "| clay colour/fabric/composition | absent | no safe-schema field |",
        "| wedge shape, ductus, paleography, ancient hand | absent | sign "
        "identity survives only through editorial transliteration |",
        "",
        "## What it rules in / rules out",
        "",
        "TLHdig can support symbolic layout compatibility, damage-aware "
        "abstention, coarse provenance controls, and textual-affinity work. "
        "It cannot support a genuinely material physical-join model: the "
        "highest-value channels identified by 3D-join research—contour, "
        "surface geometry, dimensions, clay appearance/composition, and "
        "graphetic hand—are absent. Tier-A no-overlap work should therefore "
        "default to `insufficient encoded evidence` unless a textual bridge "
        "or an external material-data module is available.",
        "",
        "No content scoring occurred, so the tracer block is not applicable.",
        "",
        "## Cost",
        "",
        f"{elapsed_seconds:.1f} seconds elapsed against a "
        f"{TIME_BUDGET_HOURS}-hour budget.",
        "",
        "## Falsifier",
        "",
        "This conclusion would be wrong if material measurements are linked "
        "to TLHdig through an external identifier/resource not represented "
        "in the distributed archive or governed derived artifacts.",
        "",
        "## Sources",
        "",
    ]
    lines.extend(
        f"- [{source['title']}]({source['url']})"
        for source in summary["sources"]
    )
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("artifact_strict", POLICIES_PATH)
    splits = pd.read_parquet(
        P2_OUT / "splits.parquet",
        columns=["doc_id", "main_split", "site"],
    )
    split_lookup, ambiguous_ids = split_lookup_fail_closed(splits)

    schema = scan_non_test_schema(
        CORPUS_ZIP, split_lookup, ambiguous_ids)
    absence_checks = schema_term_matches(schema)
    edges = summarize_edges(split_lookup)
    sites = summarize_sites(splits)
    matrix = build_matrix(schema, edges, sites)

    if schema["status"].get("test_skipped_before_read", 0) == 0:
        raise AssertionError("P2-B cleanroom canary: no test entries skipped")
    if schema["direct_media_extension_counts"]:
        raise AssertionError(
            "P2-B media conclusion invalid: direct media files were found")
    unexpected_schema_fields = {
        group: fields for group, fields in absence_checks.items() if fields
    }
    if unexpected_schema_fields:
        raise AssertionError(
            "P2-B absence conclusion invalid: material schema fields found: "
            f"{unexpected_schema_fields}")

    summary = {
        "label": "PROBE — not for citation",
        "target_universe": "train + dev + discovery; test excluded",
        "time_budget_hours": TIME_BUDGET_HOURS,
        "safe_schema_scan": schema,
        "absence_schema_term_checks": absence_checks,
        "edge_summary": edges,
        "site_summary": sites,
        "materiality_matrix": matrix,
        "sources": SOURCES,
        "input_hashes": {
            "corpus_zip": sha256(CORPUS_ZIP),
            "edges_parquet": sha256(P2_OUT / "edges.parquet"),
            "splits_parquet": sha256(P2_OUT / "splits.parquet"),
        },
    }

    manifest = ep.build_manifest(
        task="physical_join_p2b_materiality_inventory",
        evidence_policy=policy.name,
        features_requested=[],
        registry=registry,
        policy=policy,
        dataset_manifest_path=P2_OUT / "edges.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=POLICIES_PATH,
        seed=SEED,
        declared_statistics_universe=(
            "filename-gated non-test XML schema plus canonical non-test "
            "edge fragments; train + dev + discovery"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "control_fields_observed": [
            "doc_id", "fragment_id", "parent_doc", "main_split"],
        "schema_names_observed": True,
        "raw_text_or_attribute_values_persisted": False,
        "test_side_accessed": False,
        "test_entries_skipped_before_read":
            schema["status"]["test_skipped_before_read"],
        "content_scoring_performed": False,
        "input_hashes": summary["input_hashes"],
    })

    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    ep.write_manifest(manifest, MANIFEST_PATH)
    elapsed = time.perf_counter() - started
    write_report(summary, elapsed)

    print(json.dumps({
        "safe_schema_status": schema["status"],
        "archive_extension_counts": schema["archive_extension_counts"],
        "edge_fragments": edges["fragments"],
        "edge_lines": edges["embedded_fragment_lines"],
        "matrix_status_counts": dict(Counter(
            row["status"] for row in matrix)),
    }, indent=2))
    print(f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}")


if __name__ == "__main__":
    main()
