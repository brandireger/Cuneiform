#!/usr/bin/env python3
"""
dm1_missing_text_export.py -- Takšan demo, small-prototype DM1: missing-text
expert UI data export.

Usage:
    python demo/dm1_missing_text_export.py

Scope decision (2026-07-24, Ixca + architect session): this is NOT
TAKSAN_DEMO_SPEC.md's join-workbench DM1/DM2. Phase 2's own closeout and
successor handoff instead call for a small UI prototype against
specs/EXPERT_DECISION_CONTRACT.md -- one missing-text location, ranked
sign options, the four expert actions. TAKSAN_DEMO_SPEC.md predates the
Phase 2 pivot and describes a different product (fragment-pair join
candidates); it is not used here.

Revision (2026-07-24): the first prototype pass used only the 4
hand-curated examples in Phase2/phase2_out/p2e7_contract_examples.jsonl.
This pass instead adapts EVERY real packet already produced by the P2-E4
and P2-E6 probes -- 16 single-sign + 12 multi-sign, 28 total -- using the
same adapt_p2e4_packet()/adapt_p2e6_packet() machinery
scripts/p2e7_contract_check.py used for its 4 curated examples. Those
adapters strip hidden evaluation gold (they never copy `outcome`,
top-level `evidence`/`support`/`contradictions`/`observable_*`, or
anything else outside the fields the contract schema names) and run
validate_suggestion_packet() before returning. This script does NOT
invent new packets, does NOT re-run any probe, and does NOT touch the
frozen test split.

Cleanroom safeguard beyond what scripts/p2e7_contract_check.py checks:
every packet's fragment_id (stripping a trailing "::N" witness-member
suffix, e.g. "IBoT 4.346+::1" -> "IBoT 4.346+") is cross-referenced
against Phase1_pipeline/p2_out/splits.parquet's frozen main_split column.
Export hard-aborts if any resolved split is not 'dev' -- fail closed on
an unknown fragment too, never silently permissive.

Revision (2026-07-24, same day): added fragment-context export per
Ixca's request to see the whole tablet a missing-text location was
drawn from, not just its two-token window. Scope, decided jointly with
Ixca (AskUserQuestion): "deterministic glosses only" -- NO machine
translation of the Hittite text (CLAUDE.md's standing out-of-scope
rule, restated for demo purposes). What IS exported:
  - the full line-by-line transliteration of every fragment referenced
    by the 28 packets (corpus.parquet), so the missing-sign location
    can be seen in its real document context;
  - CTH composition titles (CATALOG_METADATA, from the already-fetched
    Archive/p25_out/cth_titles.csv catalogue snapshot -- read-only,
    Archive/ is not modified);
  - a determinative category for words whose leading sign matches
    CLAUDE.md's own already-vetted starting inventory (D, m, URU, KUR,
    LU, GIS, NA4, E, DUG, TUG, ID, HUR.SAG, MUSEN, UZU, SIG, NINDA) --
    words carrying a determinative outside that list are labeled
    "uncategorized" rather than guessed. A real corpus census (696
    is_det words across these 18 fragments) found ~72% match the
    vetted list at its correct Unicode encoding (the corpus uses ÆḪ/
    subscript digits; CLAUDE.md's prose used plain ASCII for the same
    markers -- corrected here, not a new determinative).
  - Sumerogram words are labeled as such (a structural fact from
    is_sum) with NO english gloss attached -- logogram gloss curation
    needs a real reference (CHD/HZL) this session doesn't have, and
    inventing one would be exactly the fabrication risk this project
    exists to avoid.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import expert_decision_contract as edc  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402

import pandas as pd  # noqa: E402

P2E4_PATH = Path("Phase2/phase2_out/p2e4_candidate_set_packets.jsonl")
P2E4_MANIFEST = Path("Phase2/phase2_out/p2e4_candidate_set_audit_manifest.json")
P2E6_PATH = Path("Phase2/phase2_out/p2e6_multisign_packets.jsonl")
P2E6_MANIFEST = Path("Phase2/phase2_out/p2e6_multisign_horizon_manifest.json")
SPLITS_PATH = Path("Phase1_pipeline/p2_out/splits.parquet")
CORPUS_PATH = Path("Phase1_pipeline/p2_out/corpus.parquet")
DOC_TABLE_PATH = Path("Phase1_pipeline/p2_out/doc_table.parquet")
DECOMPOSED_PATH = Path("Phase1_pipeline/p4_out/decomposed_corpus.parquet")
CTH_TITLES_PATH = Path("Archive/p25_out/cth_titles.csv")

OUT_DIR = Path("Phase3/demo_out")
OUT_JS = OUT_DIR / "missing_text_demo_data.js"
OUT_REPORT = OUT_DIR / "missing_text_demo_data_report.md"
OUT_CONTEXT_JS = OUT_DIR / "fragment_context_data.js"
OUT_GAPS_JS = OUT_DIR / "gap_locations_data.js"

# CLAUDE.md's starting determinative inventory, verbatim (Corpus (pinned)
# section). Matched longest-prefix-first against the corpus's actual
# Unicode encoding (Ḫ, subscript digits), not the plain-ASCII prose
# rendering. Never extended beyond this list without a deliberate,
# separately-reviewed decision -- unmapped is_det words are flagged, not
# guessed.
DET_TABLE = {
    "ḪUR.SAG": "mountain",
    "NA₄": "stone",
    "MUŠEN": "bird",
    "NINDA": "bread/pastry",
    "GIŠ": "wooden object",
    "SÍG": "wool",
    "TÚG": "garment",
    "URU": "city",
    "KUR": "land",
    "LÚ": "profession/title",
    "UZU": "body part/meat",
    "DUG": "vessel",
    "ÍD": "river",
    "É": "building",
    "D": "deity name",
    "m": "personal name (Personenkeil)",
}
DET_PREFIXES_BY_LENGTH = sorted(DET_TABLE, key=len, reverse=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def provenance(probe, artifact, manifest):
    return {
        "source_probe": probe,
        "source_artifact": artifact.as_posix(),
        "source_artifact_sha256": sha256_file(artifact),
        "source_manifest": manifest.as_posix(),
        "source_manifest_sha256": sha256_file(manifest),
        "dev_example_only": True,
        "hidden_evaluation_payload_removed": True,
    }


def base_doc_id(fragment_id):
    """Strip a trailing '::N' witness-member suffix for a splits.parquet lookup."""
    return fragment_id.split("::")[0]


def classify_determinative(signs):
    """Return (marker, category) from CLAUDE.md's vetted inventory, or
    (None, None) if the word's leading sign doesn't match any known
    determinative prefix -- never guessed."""
    if not signs:
        return None, None
    first = signs[0]
    for prefix in DET_PREFIXES_BY_LENGTH:
        if first.startswith(prefix):
            return prefix, DET_TABLE[prefix]
    return None, None


def build_fragment_context(doc_ids, det_stats):
    corpus = pd.read_parquet(CORPUS_PATH)
    doc_table = pd.read_parquet(DOC_TABLE_PATH).set_index("doc_id")
    cth_titles = pd.read_csv(CTH_TITLES_PATH).set_index("cth")["title"]

    context = {}
    for doc_id in doc_ids:
        sub = corpus[corpus["doc_id"] == doc_id].sort_values(
            ["line_index_in_doc", "word_index_in_line"])
        if sub.empty:
            raise SystemExit(
                f"FRAGMENT CONTEXT ABORT: doc_id '{doc_id}' has no rows in "
                f"{CORPUS_PATH} -- refusing to export a fragment with no "
                f"underlying text."
            )

        doc_row = doc_table.loc[doc_id] if doc_id in doc_table.index else None
        cth = int(doc_row["cth"]) if doc_row is not None else None
        title = cth_titles.get(cth) if cth is not None else None

        lines_by_label = {}
        line_order = []
        for _, row in sub.iterrows():
            key = (row["line_index_in_doc"], row["line_label"])
            if key not in lines_by_label:
                lines_by_label[key] = {
                    "line_index_in_doc": int(row["line_index_in_doc"]),
                    "line_label": row["line_label"],
                    "words": [],
                }
                line_order.append(key)
            if bool(row["is_empty"]):
                continue
            # signs / sign_damage_states are stored as JSON-encoded strings
            # in corpus.parquet, not native list columns -- must json.loads(),
            # never list(), which would silently iterate characters instead.
            signs = json.loads(row["signs"]) if row["signs"] else []
            damage_states = (
                json.loads(row["sign_damage_states"])
                if row["sign_damage_states"] else [])
            marker, category = classify_determinative(signs) if row["is_det"] else (None, None)
            if row["is_det"]:
                det_stats["matched" if category else "unmapped"] += 1
                if not category:
                    det_stats["unmapped_examples"].add(signs[0][:12] if signs else "?")
            lines_by_label[key]["words"].append({
                "word_index_in_line": int(row["word_index_in_line"]),
                "surface_translit": row["surface_translit"],
                "trans": row["trans"] if pd.notna(row["trans"]) else None,
                "signs": signs,
                "sign_damage_states": damage_states,
                "is_det": bool(row["is_det"]),
                "is_sum": bool(row["is_sum"]),
                "is_akk": bool(row["is_akk"]),
                "det_category": category,
            })

        context[doc_id] = {
            "doc_id": doc_id,
            "cth": cth,
            "cth_title": title if pd.notna(title) else None,
            "site": doc_row["site"] if doc_row is not None else None,
            "n_members": int(doc_row["n_members"]) if doc_row is not None else None,
            "lines": [lines_by_label[key] for key in line_order],
        }
    return context


def load_decomposed_lines(doc_ids):
    """Returns dict (doc_id, line_index_in_doc) -> ordered list of
    (token, damage_state, word_index_in_line) triples, sorted by
    word_pos. Cross-checked line by line against
    lib.hittite_tokenizer.build_decomposed_line_index() -- the
    project's own canonical reader -- so a divergence aborts loudly
    instead of silently trusting a second, parallel read of the same
    file."""
    df = pd.read_parquet(DECOMPOSED_PATH)
    df = df[df["doc_id"].isin(doc_ids)].sort_values(
        ["doc_id", "line_index_in_doc", "word_pos"])
    lines = {}
    for row in df.itertuples(index=False):
        key = (row.doc_id, row.line_index_in_doc)
        widx = None if pd.isna(row.word_index_in_line) else int(row.word_index_in_line)
        lines.setdefault(key, []).append((row.token, row.damage_state, widx))

    canonical = ht.build_decomposed_line_index()
    for key, triples in lines.items():
        mine = [(t, s) for t, s, _ in triples]
        theirs = canonical.get(key, [])
        if mine != theirs:
            raise SystemExit(
                f"GAP LOCATION ABORT: local decomposed read for {key} "
                f"diverges from hittite_tokenizer.build_decomposed_line_index() "
                f"-- refusing to trust a second read of the same file."
            )
    return lines


def filtered_stream(triples):
    """(token, damage_state, word_index_in_line) triples -> list of
    (original_index, token, word_index_in_line) surviving
    lib.hittite_tokenizer.encode_fragment_window(include_restored=False)
    plus the same SPECIALS/'x' drop scripts/p2e_witness_recoverability.py
    applies. Verified against the real encode_fragment_window() output,
    not just assumed to match it."""
    canonical = ht.encode_fragment_window(
        [(0, [(t, s) for t, s, _ in triples])], include_restored=False)
    canonical = [t for t in canonical if t not in ht.SPECIALS and t != "x"]
    mine = []
    for i, (tok, state, widx) in enumerate(triples):
        if state == "restored" or tok in ht.SPECIALS or tok == "x":
            continue
        mine.append((i, tok, widx))
    if [t for _, t, _ in mine] != canonical:
        raise SystemExit(
            "GAP LOCATION ABORT: local restored/SPECIALS filter diverges "
            "from hittite_tokenizer.encode_fragment_window() -- refusing "
            "to trust a second reimplementation of that filter."
        )
    return mine


def compute_gap_location(packet, decomposed_lines):
    """Returns the exact word(s) and decomposed sign(s) a packet's gap
    covers, verified against the packet's own left_context/right_context
    (which were independently computed by the P2-E4/P2-E6 probes) --
    not merely trusted from the offset math. Returns None (and the
    fragment panel falls back to line-only highlighting) if anything
    doesn't reconcile exactly, rather than guess."""
    gap_extent = packet["query"]["gap_extent"]
    if gap_extent["kind"] != "EXACT" or gap_extent["minimum_signs"] != gap_extent["maximum_signs"]:
        return None
    mask_length = gap_extent["minimum_signs"]
    doc_id = base_doc_id(packet["query"]["fragment_id"])
    line_idx = packet["query"]["location"]["line_index_in_doc"]
    offset = packet["query"]["location"]["sign_offset_in_line"]

    triples = decomposed_lines.get((doc_id, line_idx))
    if triples is None:
        return None
    stream = filtered_stream(triples)
    if offset + mask_length > len(stream):
        return None

    gap_entries = stream[offset:offset + mask_length]
    anchor_length = len(packet["query"]["left_context"])
    left_entries = stream[max(0, offset - anchor_length):offset]
    right_entries = stream[offset + mask_length:offset + mask_length + anchor_length]
    left_tokens = [t for _, t, _ in left_entries]
    right_tokens = [t for _, t, _ in right_entries]
    if (left_tokens != packet["query"]["left_context"]
            or right_tokens != packet["query"]["right_context"]):
        # Genuine mismatch (or an edge-of-line context the anchor_length
        # assumption doesn't hold for) -- do not guess; fall back to
        # line-only highlighting for this packet.
        return None

    word_indices = sorted({widx for _, _, widx in gap_entries if widx is not None})
    if not word_indices:
        return None

    gap_original_indices = {i for i, t, widx in gap_entries}

    words_detail = []
    for widx in word_indices:
        word_triples = [(i, t, s) for i, (t, s, w) in enumerate(triples) if w == widx]
        words_detail.append({
            "word_index_in_line": widx,
            "tokens": [
                {"token": t, "damage_state": s, "is_gap": i in gap_original_indices}
                for i, t, s in word_triples
            ],
        })

    return {
        "line_index_in_doc": line_idx,
        "word_indices": word_indices,
        "words": words_detail,
    }


def assert_dev_split(fragment_id, main_split_lookup):
    doc_id = base_doc_id(fragment_id)
    split = main_split_lookup.get(doc_id)
    if split != "dev":
        raise SystemExit(
            f"CLEANROOM ABORT: fragment_id '{fragment_id}' (doc_id "
            f"'{doc_id}') resolved to main_split='{split}', not 'dev'. "
            f"Refusing to export -- see Cleanroom rule 1."
        )


def main():
    splits = pd.read_parquet(SPLITS_PATH).set_index("doc_id")["main_split"]

    p2e4_raw = load_jsonl(P2E4_PATH)
    p2e6_raw = load_jsonl(P2E6_PATH)
    if not p2e4_raw or not p2e6_raw:
        raise SystemExit("P2-E4 or P2-E6 source packets are empty.")

    p2e4_provenance = provenance("P2-E4", P2E4_PATH, P2E4_MANIFEST)
    p2e6_provenance = provenance("P2-E6", P2E6_PATH, P2E6_MANIFEST)

    packets = []
    rows = []

    for i, source in enumerate(p2e4_raw, 1):
        fragment_id = source["query"]["fragment_id"]
        assert_dev_split(fragment_id, splits)
        packet = edc.adapt_p2e4_packet(source, f"p2e4-{i:03d}", p2e4_provenance)
        packets.append(packet)

    for i, source in enumerate(p2e6_raw, 1):
        fragment_id = source["query"]["fragment_id"]
        assert_dev_split(fragment_id, splits)
        packet = edc.adapt_p2e6_packet(source, f"p2e6-{i:03d}", p2e6_provenance)
        packets.append(packet)

    for packet in packets:
        rows.append({
            "packet_id": packet["packet_id"],
            "fragment_id": packet["query"]["fragment_id"],
            "mode": packet["mode"],
            "status": packet["status"],
            "shown": packet["candidate_set"]["shown_option_count"],
            "total": packet["candidate_set"]["total_option_count"],
            "tail": packet["candidate_set"]["collapsed_tail_count"],
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    js_payload = json.dumps(packets, ensure_ascii=False, indent=2)
    js_content = (
        "// Generated by demo/dm1_missing_text_export.py -- do not hand-edit.\n"
        "// Every packet below is adapted via lib/expert_decision_contract.py's\n"
        "// adapt_p2e4_packet()/adapt_p2e6_packet() (hidden evaluation gold\n"
        "// stripped, validate_suggestion_packet() run) and cross-checked\n"
        "// against the frozen dev/test split before export.\n"
        f"const TAKSAN_DEMO_PACKETS = {js_payload};\n"
    )
    OUT_JS.write_text(js_content, encoding="utf-8")

    doc_ids = sorted({base_doc_id(r["fragment_id"]) for r in rows})
    det_stats = {"matched": 0, "unmapped": 0, "unmapped_examples": set()}
    fragment_context = build_fragment_context(doc_ids, det_stats)
    context_payload = json.dumps(fragment_context, ensure_ascii=False, indent=2)
    context_js_content = (
        "// Generated by demo/dm1_missing_text_export.py -- do not hand-edit.\n"
        "// Full line-by-line transliteration for every fragment referenced by\n"
        "// missing_text_demo_data.js. Deterministic glosses ONLY: determinative\n"
        "// categories from CLAUDE.md's vetted inventory (unmapped ones flagged,\n"
        "// never guessed) and CATALOG_METADATA CTH titles. NO machine\n"
        "// translation of Hittite text -- see the scope note at the top of\n"
        "// this script.\n"
        f"const TAKSAN_FRAGMENT_CONTEXT = {context_payload};\n"
    )
    OUT_CONTEXT_JS.write_text(context_js_content, encoding="utf-8")

    decomposed_lines = load_decomposed_lines(doc_ids)
    gap_locations = {}
    n_exact = 0
    for packet in packets:
        loc = compute_gap_location(packet, decomposed_lines)
        if loc is not None:
            gap_locations[packet["packet_id"]] = loc
            n_exact += 1
    gaps_payload = json.dumps(gap_locations, ensure_ascii=False, indent=2)
    gaps_js_content = (
        "// Generated by demo/dm1_missing_text_export.py -- do not hand-edit.\n"
        "// Exact word/sign location of each packet's gap, computed from\n"
        "// Phase1_pipeline/p4_out/decomposed_corpus.parquet (now carrying a\n"
        "// word_index_in_line column added specifically for this alignment --\n"
        "// see lib/decompose_corpus.py). Every entry here was verified by\n"
        "// reproducing the packet's own left_context/right_context tokens\n"
        "// exactly; packets that didn't reconcile are simply absent (the\n"
        "// fragment panel falls back to line-only highlighting for those).\n"
        f"const TAKSAN_GAP_LOCATIONS = {gaps_payload};\n"
    )
    OUT_GAPS_JS.write_text(gaps_js_content, encoding="utf-8")

    n_single = sum(1 for r in rows if r["mode"] == "SINGLE_SIGN")
    n_multi = sum(1 for r in rows if r["mode"] == "MULTI_SIGN")
    n_present = sum(1 for r in rows if r["status"] == "PRESENT_CANDIDATES")
    n_abstain = sum(1 for r in rows if r["status"] == "ABSTAIN_INSUFFICIENT_EVIDENCE")
    n_tail = sum(1 for r in rows if r["tail"] > 0)

    report_lines = [
        "# Missing-text demo data export report",
        "",
        f"Sources: `{P2E4_PATH.as_posix()}` (16 packets) + "
        f"`{P2E6_PATH.as_posix()}` (12 packets).",
        f"Output: `{OUT_JS.as_posix()}` "
        f"({OUT_JS.stat().st_size / 1024:.1f} KB).",
        "",
        f"**{len(packets)} real packets exported** "
        f"({n_single} single-sign, {n_multi} multi-sign; "
        f"{n_present} present-candidates, {n_abstain} abstain; "
        f"{n_tail} with a collapsed tail). Every packet is adapted via "
        "`lib/expert_decision_contract.py`'s `adapt_p2e4_packet()`/"
        "`adapt_p2e6_packet()`, which strips hidden evaluation gold "
        "(the raw source's `outcome`, top-level `evidence`/`support`/"
        "`contradictions`/`observable_*` fields are never read) and runs "
        "`validate_suggestion_packet()` before returning.",
        "",
        "**Cleanroom check**: every packet's fragment_id (base doc_id after "
        "stripping a trailing `::N` witness-member suffix) was looked up in "
        "`Phase1_pipeline/p2_out/splits.parquet`'s frozen `main_split` "
        f"column. All {len(packets)} resolved to `dev`. The export "
        "hard-aborts on any packet resolving to `test`, `train`, "
        "`discovery`, or an unrecognized doc_id.",
        "",
        "| packet_id | fragment_id | mode | status | shown/total (tail) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        report_lines.append(
            f"| `{r['packet_id']}` | {r['fragment_id']} | {r['mode']} | "
            f"{r['status']} | {r['shown']}/{r['total']} ({r['tail']} collapsed) |"
        )
    report_lines.append("")

    total_lines = sum(len(fc["lines"]) for fc in fragment_context.values())
    total_words = sum(len(line["words"]) for fc in fragment_context.values() for line in fc["lines"])
    n_det = det_stats["matched"] + det_stats["unmapped"]
    det_pct = (det_stats["matched"] / n_det * 100) if n_det else 0.0
    missing_titles = sorted({
        fc["cth"] for fc in fragment_context.values()
        if fc["cth"] is not None and fc["cth_title"] is None
    })

    report_lines += [
        "## Fragment context export",
        "",
        f"`{OUT_CONTEXT_JS.as_posix()}` "
        f"({OUT_CONTEXT_JS.stat().st_size / 1024:.1f} KB): full line-by-line "
        f"transliteration for the {len(doc_ids)} distinct fragments referenced "
        f"above ({total_lines} lines, {total_words} words total), sourced "
        f"directly from `{CORPUS_PATH.as_posix()}`.",
        "",
        f"**Determinative categories**: {det_stats['matched']}/{n_det} "
        f"({det_pct:.1f}%) of determinative-marked words matched CLAUDE.md's "
        "already-vetted starting inventory (matched at the corpus's real "
        "Unicode encoding — Ḫ, subscript digits — not the plain-ASCII prose "
        "spelling). The remaining "
        f"{det_stats['unmapped']} are labeled \"uncategorized\" in the UI, "
        "never guessed. Sample unmapped leading signs: "
        f"{', '.join(sorted(det_stats['unmapped_examples'])[:15])}. These are "
        "real, legitimate determinative/marker categories outside the small "
        "list CLAUDE.md happened to name (e.g. MUNUS \"woman\", M/F personal-"
        "name markers, KAM ordinal markers, ḪI.A/MEŠ plural markers) — "
        "extending the vetted list is a deliberate follow-up decision, not "
        "something this export makes unilaterally.",
        "",
        f"**CTH titles**: sourced from `{CTH_TITLES_PATH.as_posix()}` "
        "(CATALOG_METADATA; the already-fetched hethport.uni-wuerzburg.de/CTH/ "
        "catalogue snapshot, not re-fetched here). "
        + (f"All {len(fragment_context)} fragments' CTH titles were found."
           if not missing_titles
           else f"Missing for CTH {missing_titles}."),
        "",
        "**No machine translation.** Sumerogram words are labeled as such "
        "(`is_sum`, a structural fact) with no English gloss attached — a "
        "real logogram-gloss curation pass needs a citable reference (CHD/"
        "HZL) this export does not have. No Hittite sentence or word is "
        "translated anywhere in this output.",
        "",
        "## Exact gap location export",
        "",
        f"`{OUT_GAPS_JS.as_posix()}`: exact word(s)/decomposed-sign(s) for "
        f"**{n_exact}/{len(packets)}** packets. Computed from "
        f"`{DECOMPOSED_PATH.as_posix()}` (now carrying `word_index_in_line`, "
        "added in `lib/decompose_corpus.py` specifically for this — it "
        "increments on every `<w>` start and resets on every `<lb>`, "
        "verified to match `Archive/scripts/02_parse.py`'s own "
        "`word_index_in_line` exactly, the same counter corpus.parquet's "
        "word grouping already uses). Every entry was verified end-to-end: "
        "the restored/SPECIALS-filtered stream this reads is checked token-"
        "for-token against `lib/hittite_tokenizer.encode_fragment_window()`, "
        "and the resulting left/right context is checked token-for-token "
        "against the packet's own (independently probe-computed) "
        "`left_context`/`right_context`. A packet is only included if both "
        "checks pass exactly; the "
        f"{len(packets) - n_exact} that don't are omitted here rather than "
        "guessed, and the fragment panel falls back to line-only "
        "highlighting for those.",
        "",
    ]

    OUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Exported {len(packets)} validated packets to {OUT_JS}")
    print(f"Exported fragment context for {len(doc_ids)} fragments to {OUT_CONTEXT_JS}")
    print(f"Exported exact gap locations for {n_exact}/{len(packets)} packets to {OUT_GAPS_JS}")
    print(f"Report written to {OUT_REPORT}")


if __name__ == "__main__":
    main()
