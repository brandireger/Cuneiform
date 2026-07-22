#!/usr/bin/env python3
"""
04_edges.py -- Per-fragment break/edge profiles for the matrix model
(CLAUDE.md: rows=lines, columns=sign positions, edges=left/right/top/
bottom).

Usage:
    python scripts/04_edges.py /path/to/TLHdig_0.2.0-beta.zip

Reads p2_out/corpus.parquet, p2_out/doc_table.parquet and
p2_out/unjoin_reconstructed.jsonl (from 02_parse.py / 03_unjoin.py),
plus a fresh light pass over the zip to capture <gap> elements (not
captured in 02_parse.py -- gap/top-bottom-edge extraction is this
deliverable's job per P2_PARSER_SPEC.md).

Per line: left edge = damage_state of the first sign; right edge =
damage_state of the last sign; leading_space_c = blank/lost run width
if the line opens with a <space> pseudo-word.
Per fragment (standalone doc, or reconstructed composite member):
top/bottom edge event = nearest <gap> immediately before the first /
after the last line, classified by its t/c attributes, plus a prime
(′) flag on the first/last line label (conventional signal that the
original line number is unknown because the tablet is broken there).

cu ▒ positions are NOT used here as a break signal -- per the D1
damage-oracle finding, cu renders the editor's full proposed reading
and ▒ marks illegible_x/indeterminate-gap positions only, not general
restoration. The authoritative per-sign state is sign_damage_states
from the transliteration markup, already in corpus.parquet.
"""

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

OUT_DIR = Path("p2_out")
CTH_FOLDER_RE = re.compile(r"CTH\s*(\d+)", re.IGNORECASE)
PRIME_RE = re.compile(r"[′″]")


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def is_junk(name: str) -> bool:
    return "__MACOSX" in name or name.rsplit("/", 1)[-1].startswith("._")


def collect_gap_events(root):
    """Walk the document in order, returning a list of
    (line_index_at_time, t_attr, c_attr) for every <gap> element, using
    the SAME line-counting scheme as 02_parse.py (increment on each
    <lb> start, starting at -1) so indices line up with corpus.parquet.
    """
    events = []
    text_el = root.find(".//{*}text")
    if text_el is None:
        return events
    line_index = -1

    def walk(el):
        nonlocal line_index
        tag = local(el.tag)
        if tag == "lb":
            line_index += 1
        elif tag == "gap":
            events.append((line_index, el.get("t"), el.get("c")))
        for child in el:
            walk(child)

    for child in text_el:
        walk(child)
    return events


def main(zip_path: str) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    corpus = pd.read_parquet(OUT_DIR / "corpus.parquet")
    doc_table = pd.read_parquet(OUT_DIR / "doc_table.parquet")

    reconstructed = {}
    with open(OUT_DIR / "unjoin_reconstructed.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            reconstructed[d["doc_id"]] = d
    composite_doc_ids = set(reconstructed.keys())

    zp = zipfile.ZipFile(zip_path)
    all_names = zp.namelist()
    xml_names = [n for n in all_names
                 if n.lower().endswith(".xml") and not n.endswith("/")
                 and not is_junk(n)]

    gap_events_by_doc = {}
    for name in xml_names:
        # only need gap events for docs we'll actually build fragments from;
        # cheap enough to just do all of them for completeness/consistency.
        raw = zp.read(name)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue
        doc_id_el = root.find(".//{*}docID")
        doc_id = (doc_id_el.text or "").strip() if doc_id_el is not None else Path(name).stem
        events = collect_gap_events(root)
        if events:
            gap_events_by_doc[doc_id] = events

    # ---- per-line edge features from corpus.parquet (vectorized: a
    # Python-level nested groupby+iterrows over 1.5M rows would be far
    # too slow, so this is done with sort + groupby().first()/last()).
    corpus_sorted = corpus.sort_values(
        ["doc_id", "line_index_in_doc", "word_index_in_line"], kind="stable")

    key = ["doc_id", "line_index_in_doc"]
    meta_cols = ["side", "column", "line_label"]
    has_edge_col = "on_physical_edge" in corpus_sorted.columns
    if has_edge_col:
        meta_cols.append("on_physical_edge")
    line_meta = corpus_sorted.groupby(key, sort=False).first()[meta_cols]

    first_word = corpus_sorted.groupby(key, sort=False).first()
    leading_space_c = first_word["space_c"].where(first_word["is_space"])

    has_signs = corpus_sorted["signs"] != "[]"
    signed = corpus_sorted[has_signs]
    left_states_json = signed.groupby(key, sort=False)["sign_damage_states"].first()
    right_states_json = signed.groupby(key, sort=False)["sign_damage_states"].last()
    left_edge_state = left_states_json.apply(lambda s: json.loads(s)[0])
    right_edge_state = right_states_json.apply(lambda s: json.loads(s)[-1])

    line_df = line_meta.copy()
    line_df["leading_space_c"] = leading_space_c
    line_df["left_edge_state"] = left_edge_state
    line_df["right_edge_state"] = right_edge_state
    line_df = line_df.reset_index()
    line_df["has_prime"] = line_df["line_label"].apply(
        lambda lbl: bool(lbl and PRIME_RE.search(str(lbl))))

    # ---- build fragments: standalone docs (whole doc) + reconstructed members
    fragments = []
    doc_line_count = dict(zip(doc_table["doc_id"], doc_table["line_count"]))

    for doc_id, n_lines in doc_line_count.items():
        if doc_id in composite_doc_ids:
            continue  # handled via member fragments below
        fragments.append({"fragment_id": doc_id, "parent_doc": doc_id,
                           "siglum": None, "line_idxs": list(range(int(n_lines)))})

    for doc_id, rec in reconstructed.items():
        for siglum, entries in rec["member_lines"].items():
            idxs = [e["line_idx"] for e in entries]
            fragments.append({
                "fragment_id": f"{doc_id}::{siglum}", "parent_doc": doc_id,
                "siglum": siglum, "line_idxs": idxs,
            })

    line_lookup = {(r.doc_id, r.line_index_in_doc): r for r in line_df.itertuples()}

    edge_rows = []
    for frag in fragments:
        doc_id = frag["parent_doc"]
        idxs = sorted(frag["line_idxs"])
        if not idxs:
            continue
        events = gap_events_by_doc.get(doc_id, [])
        min_idx, max_idx = idxs[0], idxs[-1]
        top_events = [e for e in events if e[0] < min_idx]
        bottom_events = [e for e in events if e[0] >= max_idx]
        first_line = line_lookup.get((doc_id, min_idx))
        last_line = line_lookup.get((doc_id, max_idx))

        per_line = []
        edge_dirs_seen = set()
        for idx in idxs:
            r = line_lookup.get((doc_id, idx))
            if r is None:
                continue
            on_edge = getattr(r, "on_physical_edge", None)
            if on_edge:
                edge_dirs_seen.add(on_edge)
            per_line.append({
                "line_index_in_doc": idx, "side": r.side, "column": r.column,
                "line_label": r.line_label, "has_prime": r.has_prime,
                "left_edge_state": r.left_edge_state,
                "right_edge_state": r.right_edge_state,
                "leading_space_c": r.leading_space_c,
                "on_physical_edge": on_edge,
            })

        first_on_edge = getattr(first_line, "on_physical_edge", None) if first_line else None
        last_on_edge = getattr(last_line, "on_physical_edge", None) if last_line else None

        # A5.2: a line explicitly marked as sitting ON the physical
        # tablet edge (u./o. Rd.) is direct evidence the fragment is
        # NOT broken there -- overrides the weaker prime-mark heuristic.
        if first_on_edge == "upper":
            top_edge_lost = False
        else:
            top_edge_lost = bool(top_events) or bool(first_line and first_line.has_prime)
        if last_on_edge == "lower":
            bottom_edge_lost = False
        else:
            bottom_edge_lost = bool(bottom_events) or bool(last_line and last_line.has_prime)

        edge_rows.append({
            "fragment_id": frag["fragment_id"], "parent_doc": doc_id,
            "siglum": frag["siglum"], "cth": None,
            "n_lines": len(idxs),
            "top_edge_lost": top_edge_lost,
            "top_edge_gap_desc": top_events[-1][2] if top_events else None,
            "top_edge_confirmed_preserved": first_on_edge == "upper",
            "bottom_edge_lost": bottom_edge_lost,
            "bottom_edge_gap_desc": bottom_events[0][2] if bottom_events else None,
            "bottom_edge_confirmed_preserved": last_on_edge == "lower",
            "preserves_left_edge": "left" in edge_dirs_seen,
            "preserves_right_edge": "right" in edge_dirs_seen,
            "left_edge_states": json.dumps(
                [pl["left_edge_state"] for pl in per_line], ensure_ascii=False),
            "right_edge_states": json.dumps(
                [pl["right_edge_state"] for pl in per_line], ensure_ascii=False),
            "lines": json.dumps(per_line, ensure_ascii=False),
        })

    edges_df = pd.DataFrame(edge_rows)
    cth_lookup = dict(zip(doc_table["doc_id"], doc_table["cth"]))
    edges_df["cth"] = edges_df["parent_doc"].map(cth_lookup)
    edges_df.to_parquet(OUT_DIR / "edges.parquet", index=False)

    # ---- report
    n_standalone = sum(1 for f in fragments if f["siglum"] is None)
    n_member = sum(1 for f in fragments if f["siglum"] is not None)
    top_lost_pct = 100 * edges_df["top_edge_lost"].mean() if len(edges_df) else 0
    bottom_lost_pct = 100 * edges_df["bottom_edge_lost"].mean() if len(edges_df) else 0

    lines_out = [
        "# P2 Deliverable 3 -- Edges Report", "",
        f"- Fragments total: {len(edges_df)} "
        f"({n_standalone} standalone docs + {n_member} reconstructed "
        f"composite members from {len(composite_doc_ids)} composite docs)",
        f"- Fragments with a detected top-edge loss (gap before first "
        f"line, or first line has a prime mark): {top_lost_pct:.1f}%",
        f"- Fragments with a detected bottom-edge loss (gap at/after "
        f"last line, or last line has a prime mark): {bottom_lost_pct:.1f}%",
        f"- Documents with at least one `<gap>` element: {len(gap_events_by_doc)}",
        "",
        "## P2.5 A5.2 addendum -- physical-edge-line coverage",
        "",
        f"- Fragments with a top edge CONFIRMED preserved (first line "
        f"sits on the upper `Rand`, overriding the prime-mark "
        f"heuristic): {100*edges_df['top_edge_confirmed_preserved'].mean():.1f}%"
        if "top_edge_confirmed_preserved" in edges_df.columns else
        "- (on_physical_edge not present in corpus.parquet -- run "
        "07_metadata_patch.py first for this section to populate)",
        (f"- Fragments with a bottom edge CONFIRMED preserved (last "
         f"line sits on the lower `Rand`): "
         f"{100*edges_df['bottom_edge_confirmed_preserved'].mean():.1f}%"
         if "bottom_edge_confirmed_preserved" in edges_df.columns else ""),
        (f"- Fragments preserving a left/right physical edge somewhere "
         f"in their line range: "
         f"{100*edges_df['preserves_left_edge'].mean():.1f}% / "
         f"{100*edges_df['preserves_right_edge'].mean():.1f}%"
         if "preserves_left_edge" in edges_df.columns else ""),
        "",
        "## Scope notes",
        "- `cu` (▒ positions) is deliberately NOT used as a break "
        "signal here -- D1's damage-oracle investigation found cu "
        "renders the editor's full proposed reading (restored signs "
        "get real glyphs); the authoritative per-sign silhouette is "
        "`sign_damage_states` from transliteration markup, already "
        "used for left/right edge states.",
        "- Top/bottom edge detection is a first-pass heuristic (gap "
        "adjacency + prime-mark presence), not definitive -- e.g. a "
        "prime mark persists across an entire broken side by "
        "convention, so `has_prime` on the first/last line is a weak "
        "corroborating signal, not proof by itself; `top_edge_gap_desc`"
        " / `bottom_edge_gap_desc` (the editor's own free-text gap "
        "description, e.g. 'Vs. bricht ab') is the stronger signal "
        "when present.",
        "- Composite-member fragments' gap events are attributed by "
        "line-index adjacency in the shared document stream, not by "
        "member -- a gap physically belonging to a different member "
        "interleaved nearby could be mis-attributed in rare cases; "
        "not deeply validated at this stage, flagged for P5/P6 review.",
    ]
    with open(OUT_DIR / "edges_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print(f"Done. {len(edges_df)} fragments, edges.parquet written.")
    print(f"Reports in: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/04_edges.py /path/to/TLHdig_0.2.0-beta.zip")
    main(sys.argv[1])
