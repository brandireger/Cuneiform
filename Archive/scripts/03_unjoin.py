#!/usr/bin/env python3
"""
03_unjoin.py -- Reconstruct join ground truth from composite documents.

Usage:
    python scripts/03_unjoin.py /path/to/TLHdig_0.2.0-beta.zip

Implements the semantics verified in p2_out/unjoin_semantics.md
(P2_PARSER_SPEC.md Deliverable 2 gate): sigla in AO:TxtPubl are
document-local, ordered, and separated by a join-type marker ('+' =
direct physical join, '(+)' = indirect/same-object-not-directly-
touching); per-line {€N} or {€N+M} tags in lb@lnr attribute a line to
one or more members, with slash-separated labels positionally matched
to the sigla order when labels differ, or a single shared label when
they coincide.

Self-contained: re-reads the zip directly rather than depending on
02_parse.py's output, so it can run independently and so the sigla/
line-label parsing (small, verified functions) doesn't need cross-
module import gymnastics with a digit-prefixed filename.
"""

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

OUT_DIR = Path("p2_out")

CTH_FOLDER_RE = re.compile(r"CTH\s*(\d+)", re.IGNORECASE)
SIGLA_PREFIX_RE = re.compile(r"^\s*\{€([\d+]+)\}\s*")
# Member declarations in AO:TxtPubl, each preceded by a join-type
# separator (except the first). Capture separator + manuscript name +
# siglum together so join_type is available per adjacent pair.
MEMBER_CHAIN_RE = re.compile(r"(\(\+\)|\+)?\s*([^{}+]+?)\s*\{€(\d+)\}")


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def is_junk(name: str) -> bool:
    return "__MACOSX" in name or name.rsplit("/", 1)[-1].startswith("._")


def parse_members_chain(txtpubl: str):
    """Returns list of dicts: siglum, manuscript, join_type_from_prev
    (None for the first member; 'direct' or 'indirect' otherwise)."""
    members = []
    for sep, manuscript, siglum in MEMBER_CHAIN_RE.findall(txtpubl or ""):
        jt = None
        if sep == "+":
            jt = "direct"
        elif sep == "(+)":
            jt = "indirect"
        members.append({
            "siglum": siglum,
            "manuscript": manuscript.strip(),
            "join_type_from_prev": jt,
        })
    return members


def parse_line_sigla(raw_lnr: str):
    """Returns (sigla_list, remainder_label). sigla_list is [] if no tag."""
    raw_lnr = raw_lnr or ""
    m = SIGLA_PREFIX_RE.match(raw_lnr)
    if not m:
        return [], raw_lnr.strip()
    remainder = raw_lnr[m.end():].strip()
    sigla = m.group(1).split("+")
    return sigla, remainder


def reconstruct_doc(name: str, raw: bytes, cth):
    root = ET.fromstring(raw)
    doc_id_el = root.find(".//{*}docID")
    doc_id = (doc_id_el.text or "").strip() if doc_id_el is not None else Path(name).stem
    txtpubl_el = root.find(".//{*}TxtPubl")
    txtpubl = (txtpubl_el.text or "").strip() if txtpubl_el is not None else ""
    members = parse_members_chain(txtpubl)

    if len(members) < 2:
        return None  # not a multi-member composite; nothing to unjoin

    member_by_siglum = {m["siglum"]: m for m in members}
    declared_order = [m["siglum"] for m in members]

    lbs = root.findall(".//{*}lb")
    lines = []  # (line_idx, sigla_list, label)
    unassigned_lines = 0
    for i, lb in enumerate(lbs):
        sigla, label = parse_line_sigla(lb.get("lnr", ""))
        sigla = [s for s in sigla if s in member_by_siglum]  # drop unresolvable sigla defensively
        if not sigla:
            unassigned_lines += 1
        lines.append((i, sigla, label, lb.get("lg"), lb.get("cu", "")))

    if not any(sigla for _, sigla, *_ in lines):
        return {
            "doc_id": doc_id, "cth": cth, "status": "quarantined",
            "reason": "no per-line {€N} sigla found despite "
                      f"{len(members)}-member TxtPubl (likely incomplete "
                      "line-level tagging in source data)",
            "n_members_declared": len(members), "members": members,
        }

    # per-member pseudo-fragment line sets (shared lines duplicated)
    member_lines = {s: [] for s in member_by_siglum}
    cooccur = {}  # frozenset({a,b}) -> count of shared lines
    for line_idx, sigla, label, lg, cu in lines:
        sub_labels = label.split("/") if "/" in label and len(sigla) > 1 else None
        for pos, s in enumerate(sigla):
            this_label = (sub_labels[pos] if sub_labels and pos < len(sub_labels)
                          else label)
            member_lines[s].append({
                "line_idx": line_idx, "label": this_label,
                "lg": lg, "cu": cu,
                "shared_with": [x for x in sigla if x != s],
            })
        if len(sigla) > 1:
            for a in range(len(sigla)):
                for b in range(a + 1, len(sigla)):
                    key = frozenset((sigla[a], sigla[b]))
                    cooccur[key] = cooccur.get(key, 0) + 1

    # declared adjacent pairs (explicit join_type from TxtPubl chain)
    pairs = {}
    for i in range(1, len(members)):
        a, b = declared_order[i - 1], declared_order[i]
        key = frozenset((a, b))
        pairs[key] = {
            "member_a": a, "member_b": b,
            "join_type": members[i]["join_type_from_prev"],
            "declared_adjacent": True,
        }
    for key, n in cooccur.items():
        if key not in pairs:
            a, b = tuple(key)
            pairs[key] = {
                "member_a": a, "member_b": b,
                "join_type": "inferred_from_shared_lines",
                "declared_adjacent": False,
            }

    pair_records = []
    for key, info in pairs.items():
        n_shared = cooccur.get(key, 0)
        a_lines = sorted(x["line_idx"] for x in member_lines[info["member_a"]])
        b_lines = sorted(x["line_idx"] for x in member_lines[info["member_b"]])
        shared_line_idxs = sorted(
            x["line_idx"] for x in member_lines[info["member_a"]]
            if info["member_b"] in x["shared_with"]
        )
        # junction geometry heuristic (documented as heuristic, not ground truth):
        # a long contiguous run of shared lines looks like duplicate-type
        # overlap; 1-2 shared lines at a numbering boundary look like a
        # single-seam physical join transition; otherwise unclear.
        if n_shared == 0:
            geometry = "no_overlap_seam"  # classic non-overlapping physical join signature
        elif n_shared <= 2:
            geometry = "seam_single_line_transition"
        elif shared_line_idxs and (shared_line_idxs[-1] - shared_line_idxs[0] + 1) <= n_shared + 2:
            geometry = "extended_overlap_duplicate_like"
        else:
            geometry = "unclear"
        pair_records.append({
            "parent_doc": doc_id, "cth": cth,
            "member_a": {"siglum": info["member_a"],
                         "manuscript": member_by_siglum[info["member_a"]]["manuscript"]},
            "member_b": {"siglum": info["member_b"],
                         "manuscript": member_by_siglum[info["member_b"]]["manuscript"]},
            "join_type": info["join_type"],
            "declared_adjacent": info["declared_adjacent"],
            "n_shared_lines": n_shared,
            "n_lines_a": len(a_lines), "n_lines_b": len(b_lines),
            "junction_geometry": geometry,
        })

    return {
        "doc_id": doc_id, "cth": cth, "status": "unjoined",
        "n_members_declared": len(members), "members": members,
        "n_lines_total": len(lines), "n_unassigned_lines": unassigned_lines,
        "pairs": pair_records,
        "member_lines": {
            s: sorted(entries, key=lambda e: e["line_idx"])
            for s, entries in member_lines.items()
        },
    }


def main(zip_path: str) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    zp = zipfile.ZipFile(zip_path)
    all_names = zp.namelist()
    xml_names = [n for n in all_names
                 if n.lower().endswith(".xml") and not n.endswith("/")
                 and not is_junk(n)]

    results = []
    quarantined = []
    errors = []
    n_candidates = 0

    for name in xml_names:
        folder_cth = None
        for part in Path(name).parts:
            fm = CTH_FOLDER_RE.match(part)
            if fm:
                folder_cth = int(fm.group(1))
                break
        raw = zp.read(name)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue
        txtpubl_el = root.find(".//{*}TxtPubl")
        txtpubl = (txtpubl_el.text or "").strip() if txtpubl_el is not None else ""
        if len(parse_members_chain(txtpubl)) < 2:
            continue
        n_candidates += 1
        try:
            result = reconstruct_doc(name, raw, folder_cth)
        except Exception as e:  # noqa: BLE001 - never silently drop
            errors.append({"file": name, "error": f"{type(e).__name__}: {e}"})
            continue
        if result is None:
            continue
        if result["status"] == "quarantined":
            quarantined.append(result)
        else:
            results.append(result)

    # ---- outputs
    join_pairs_path = OUT_DIR / "join_pairs.jsonl"
    with open(join_pairs_path, "w", encoding="utf-8") as f:
        for doc in results:
            for pair in doc["pairs"]:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    with open(OUT_DIR / "unjoin_quarantine.jsonl", "w", encoding="utf-8") as f:
        for doc in quarantined:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        for err in errors:
            f.write(json.dumps({"status": "error", **err}, ensure_ascii=False) + "\n")

    with open(OUT_DIR / "unjoin_reconstructed.jsonl", "w", encoding="utf-8") as f:
        for doc in results:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # ---- stats
    total = len(results) + len(quarantined) + len(errors)
    success_rate = 100 * (len(results) + len(quarantined)) / total if total else 0.0
    members_per_doc = [d["n_members_declared"] for d in results + quarantined]
    from collections import Counter
    members_hist = Counter(members_per_doc)
    all_pairs = [p for d in results for p in d["pairs"]]
    geometry_hist = Counter(p["junction_geometry"] for p in all_pairs)
    jointype_hist = Counter(p["join_type"] for p in all_pairs)
    shared_line_counts = [p["n_shared_lines"] for p in all_pairs]

    lines_out = [
        "# P2 Deliverable 2 -- Unjoin Report", "",
        f"- Composite-doc candidates (TxtPubl parses to >=2 members): {n_candidates}",
        f"- Successfully reconstructed: {len(results)}",
        f"- Quarantined (documented reason, not counted as positives): {len(quarantined)}",
        f"- Errors (exceptions during reconstruction): {len(errors)}",
        f"- **Acceptance check #3 (>=90% unjoined or explicitly quarantined): "
        f"{success_rate:.1f}%** ({'PASS' if success_rate >= 90 else 'FAIL'})",
        "",
        "Note: P1 inventory's *authoritative* join-notation scan (docID/"
        "TxtPubl/lb@txtid text containing a well-formed embedded '+') "
        "found 866 docs. This deliverable's population "
        f"({n_candidates} docs) is defined more precisely as 'TxtPubl "
        "parses to >=2 {€N}-tagged members' and differs from 866 "
        "because (a) some P1 866-matches have a *dangling* trailing "
        "'+' with the second member's name never given in TxtPubl at "
        "all (an incomplete-metadata case, e.g. `KUB 7.19 {€1} +`), "
        "which this stricter parse cannot resolve to >=2 named members "
        "and therefore excludes; (b) some single-member docs carry a "
        "non-1 {€N} tag (e.g. `KBo 45.18 {€2}`) referencing a join "
        "family not fully represented in that file. Both are corpus "
        "data-quality artifacts, not parser bugs -- consistent with "
        "CLAUDE.md's 'quality filtering must be explicit, never "
        "silent' standard.",
        "",
        "## Members-per-doc histogram", ""]
    for k in sorted(members_hist):
        lines_out.append(f"- {k} members: {members_hist[k]} docs")
    lines_out += ["", "## Pair-level stats", "",
                  f"- Total member-pairs emitted: {len(all_pairs)}", ""]
    lines_out.append("### join_type")
    for k, v in jointype_hist.most_common():
        lines_out.append(f"- {k}: {v}")
    lines_out.append("")
    lines_out.append("### junction_geometry (heuristic -- see script docstring; "
                      "treat as noisy first-pass metadata, not ground truth)")
    for k, v in geometry_hist.most_common():
        lines_out.append(f"- {k}: {v}")
    lines_out.append("")
    if shared_line_counts:
        lines_out.append(f"- n_shared_lines: min={min(shared_line_counts)}, "
                          f"median={sorted(shared_line_counts)[len(shared_line_counts)//2]}, "
                          f"max={max(shared_line_counts)}")
    lines_out += ["", "## Quarantine reasons (top 10)", ""]
    reason_hist = Counter(d["reason"] for d in quarantined)
    for reason, cnt in reason_hist.most_common(10):
        lines_out.append(f"- ({cnt}) {reason}")
    lines_out += ["", "*Full detail in join_pairs.jsonl / unjoin_quarantine.jsonl / "
                  "unjoin_reconstructed.jsonl.*"]

    with open(OUT_DIR / "join_stats.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))

    print(f"Done. {len(results)} reconstructed, {len(quarantined)} quarantined, "
          f"{len(errors)} errors, {len(all_pairs)} join pairs emitted.")
    print(f"Reports in: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/03_unjoin.py /path/to/TLHdig_0.2.0-beta.zip")
    main(sys.argv[1])
