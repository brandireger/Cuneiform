#!/usr/bin/env python3
"""
01_inventory.py — Schema-agnostic census of the TLHdig XML corpus.

Usage:
    python scripts/01_inventory.py /path/to/TLHdig_0.2.0-beta.zip

Stdlib only (Python 3.9+). Reads the zip in place; writes reports to
./p1_out/ (renamed from inventory_out/ 2026-07-21 for consistency with
p2_out/p25_out/p3_out/p4_out). Designed to DISCOVER the schema, not
assume it.
"""

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- config
OUT_DIR = Path("p1_out")
SAMPLE_DOCS = 3            # raw XML samples to save
SAMPLE_TRUNC = 4000        # chars per sample
MAX_ATTR_VALUES = 12       # example values kept per attribute

# Publication prefixes -> site (approximate, refined later with expert
# input; enough for a first provenance histogram).
SITE_PREFIXES = {
    "KBo": "Hattusa", "KUB": "Hattusa", "Bo": "Hattusa", "VBoT": "Hattusa",
    "IBoT": "Hattusa", "ABoT": "Hattusa", "HT": "Hattusa(coll.)",
    "HKM": "Masat/Tapikka", "Mst": "Masat/Tapikka", "Mşt": "Masat/Tapikka",
    "Or": "Ortakoy/Sapinuwa", "Or.": "Ortakoy/Sapinuwa",
    "KuT": "Kusakli/Sarissa", "KuSa": "Kusakli/Sarissa",
    "KpT": "Kayalipinar/Samuha",
    "MH": "unknown", "AT": "Alalakh", "RS": "Ugarit", "Msk": "Emar",
}

CTH_RE = re.compile(r"CTH[\s._-]*(\d+)", re.IGNORECASE)
CTH_FOLDER_RE = re.compile(r"CTH\s*(\d+)", re.IGNORECASE)
JOIN_PLUS_RE = re.compile(r"\S\s*\+\s*\S")          # "X + Y" join notation
# Fields where a "+" is an actual manuscript-join marker rather than
# incidental punctuation. mrp* morphological-parse attributes also
# contain "+=" (clitic-attachment notation, e.g. "POSP += ma@CNJctr@@")
# which is NOT a join and must not be scanned for join detection.
JOIN_BEARING_TAGS = {"docID", "TxtPubl"}
JOIN_BEARING_ATTRS = {("lb", "txtid")}
BRACKET_TOKENS = ["[", "]", "⸢", "⸣", "〈", "〉", "<", ">", "(", ")"]


def local(tag: str) -> str:
    """Strip XML namespace: '{ns}line' -> 'line'."""
    return tag.rsplit("}", 1)[-1]


def main(zip_path: str) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    zp = zipfile.ZipFile(zip_path)

    def is_junk(n: str) -> bool:
        # macOS zip artifacts: __MACOSX/ shadow tree and AppleDouble
        # resource-fork files ("._Foo.xml"), never real corpus content.
        return "__MACOSX" in n or n.rsplit("/", 1)[-1].startswith("._")

    all_names = zp.namelist()
    xml_names = [n for n in all_names
                 if n.lower().endswith(".xml") and not n.endswith("/")
                 and not is_junk(n)]
    other_names = [n for n in all_names
                   if not n.lower().endswith(".xml") and not n.endswith("/")
                   and not is_junk(n)]
    junk_count = sum(1 for n in all_names if is_junk(n) and not n.endswith("/"))

    sizes = []
    tag_counts = Counter()
    parent_child = Counter()            # (parent, child) edges
    attr_counts = Counter()             # (tag, attr)
    attr_examples = defaultdict(set)    # (tag, attr) -> sample values
    root_tags = Counter()
    parse_errors = []

    cth_hits = Counter()                # CTH number -> num docs mentioning (text/attr)
    docs_with_cth = 0
    cth_folder_hits = Counter()         # CTH number -> num docs, from folder path
    docs_with_cth_folder = 0
    docs_with_join_plus = 0             # authoritative: docID/TxtPubl/txtid only
    join_plus_examples = []
    docs_with_join_plus_noisy = 0       # old all-attribute/text scan, kept for comparison
    join_plus_noisy_examples = []
    prefix_hist = Counter()
    bracket_freq = Counter()
    text_char_total = 0
    docs_scanned = 0

    samples_saved = 0
    sample_fh = open(OUT_DIR / "sample_documents.txt", "w", encoding="utf-8")

    for name in xml_names:
        raw = zp.read(name)
        sizes.append(len(raw))
        docs_scanned += 1

        if samples_saved < SAMPLE_DOCS:
            sample_fh.write(f"\n{'='*70}\nFILE: {name}\n{'='*70}\n")
            sample_fh.write(raw[:SAMPLE_TRUNC].decode("utf-8", "replace"))
            sample_fh.write("\n[TRUNCATED]\n")
            samples_saved += 1

        # ---- filename/path-level signals (independent of parse success)
        stem = Path(name).stem
        # CTH membership is structural: one "CTH ###_XML" folder per
        # composition, not reliably present in the document body/text.
        folder_cth = None
        for part in Path(name).parts:
            fm = CTH_FOLDER_RE.match(part)
            if fm:
                folder_cth = fm.group(1)
                break
        if folder_cth:
            docs_with_cth_folder += 1
            cth_folder_hits[folder_cth] += 1
        for pfx, site in SITE_PREFIXES.items():
            if stem.startswith(pfx):
                prefix_hist[f"{pfx} ({site})"] += 1
                break
        else:
            prefix_hist["(no known prefix)"] += 1

        # ---- parse
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            parse_errors.append((name, str(e)))
            continue

        root_tags[local(root.tag)] += 1

        doc_text_parts = []
        doc_cth = set()
        doc_has_plus = False        # authoritative: docID/TxtPubl/txtid
        doc_has_plus_noisy = False  # any "+"-ish text/attr, incl. mrp* clitic notation

        stack = [(root, None)]
        while stack:
            el, parent = stack.pop()
            t = local(el.tag)
            tag_counts[t] += 1
            if parent is not None:
                parent_child[(parent, t)] += 1
            for a, v in el.attrib.items():
                key = (t, local(a))
                attr_counts[key] += 1
                if len(attr_examples[key]) < MAX_ATTR_VALUES:
                    attr_examples[key].add(v[:60])
                for m2 in CTH_RE.finditer(v):
                    doc_cth.add(m2.group(1))
                if JOIN_PLUS_RE.search(v):
                    doc_has_plus_noisy = True
                    if len(join_plus_noisy_examples) < 25:
                        join_plus_noisy_examples.append(f"{name} :: {t}@{local(a)} = {v[:100]}")
                    if (t, local(a)) in JOIN_BEARING_ATTRS:
                        doc_has_plus = True
                        if len(join_plus_examples) < 25:
                            join_plus_examples.append(f"{name} :: {t}@{local(a)} = {v[:100]}")
            for chunk in (el.text, el.tail):
                if chunk and chunk.strip():
                    s = chunk.strip()
                    doc_text_parts.append(s)
                    for m2 in CTH_RE.finditer(s):
                        doc_cth.add(m2.group(1))
                    if JOIN_PLUS_RE.search(s):
                        doc_has_plus_noisy = True
                        if len(join_plus_noisy_examples) < 25:
                            join_plus_noisy_examples.append(f"{name} :: text = {s[:100]}")
                        if t in JOIN_BEARING_TAGS:
                            doc_has_plus = True
                            if len(join_plus_examples) < 25:
                                join_plus_examples.append(f"{name} :: {t} text = {s[:100]}")
            for child in el:
                stack.append((child, t))

        text = " ".join(doc_text_parts)
        text_char_total += len(text)
        for b in BRACKET_TOKENS:
            bracket_freq[b] += text.count(b)
        if doc_cth:
            docs_with_cth += 1
            for c in doc_cth:
                cth_hits[c] += 1
        if doc_has_plus:
            docs_with_join_plus += 1
        if doc_has_plus_noisy:
            docs_with_join_plus_noisy += 1

    sample_fh.close()

    # ---------------------------------------------------------- report
    def fmt_mb(b): return f"{b/1_048_576:.1f} MB"

    report = {
        "zip": str(zip_path),
        "xml_file_count": len(xml_names),
        "junk_files_excluded": junk_count,
        "non_xml_files": other_names[:50],
        "total_xml_bytes": sum(sizes),
        "doc_size_bytes": {
            "min": min(sizes) if sizes else 0,
            "median": sorted(sizes)[len(sizes)//2] if sizes else 0,
            "max": max(sizes) if sizes else 0,
        },
        "parse_errors": len(parse_errors),
        "parse_error_examples": parse_errors[:10],
        "root_tags": dict(root_tags),
        "top_tags": tag_counts.most_common(40),
        "top_parent_child_edges": [
            [f"{p} > {c}", n] for (p, c), n in parent_child.most_common(40)],
        "top_attributes": [
            [f"{t}@{a}", n, sorted(attr_examples[(t, a)])[:8]]
            for (t, a), n in attr_counts.most_common(40)],
        "cth": {
            "docs_with_cth_folder": docs_with_cth_folder,
            "distinct_cth_folders": len(cth_folder_hits),
            "docs_with_cth_text_reference": docs_with_cth,
            "distinct_cth_numbers_in_text": len(cth_hits),
            "top_cth_folders": cth_folder_hits.most_common(20),
        },
        "joins": {
            "docs_with_join_notation_authoritative":
                docs_with_join_plus,
            "docs_with_plus_notation_noisy_all_fields":
                docs_with_join_plus_noisy,
            "note": "authoritative = '+' found only in docID / "
                    "AO:TxtPubl / lb@txtid; noisy = any '+' anywhere "
                    "including w@mrp* clitic-attachment notation "
                    "('POSP += ma'), which is not a join marker.",
            "examples": join_plus_examples,
        },
        "provenance_prefix_histogram": prefix_hist.most_common(),
        "bracket_marker_frequencies": dict(bracket_freq),
        "total_text_chars": text_char_total,
    }

    with open(OUT_DIR / "inventory_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = [
        "# TLHdig Inventory Report", "",
        f"- XML documents (junk excluded): **{len(xml_names)}** "
        f"({fmt_mb(sum(sizes))} uncompressed XML)",
        f"- macOS junk files excluded (__MACOSX/, AppleDouble '._*'): "
        f"{junk_count}",
        f"- Non-XML, non-junk files in zip: {len(other_names)}",
        f"- Parse errors: {len(parse_errors)}",
        f"- Root tag(s): {dict(root_tags)}",
        f"- Total text characters: {text_char_total:,}", "",
        "## CTH coverage",
        f"- **Authoritative** (folder path, one `CTH ###_XML` dir per "
        f"composition): {docs_with_cth_folder} / {docs_scanned} docs, "
        f"{len(cth_folder_hits)} distinct compositions",
        f"- Docs also textually referencing a CTH number in-body: "
        f"{docs_with_cth} / {docs_scanned} (do not rely on this for "
        f"labels — CTH membership is structural, not textual)",
        "",
        "## Join ('+') notation",
        f"- **Authoritative** (docID / AO:TxtPubl / lb@txtid only): "
        f"{docs_with_join_plus} docs",
        f"- Noisy all-field scan (inflated by `w@mrp*` clitic-attachment "
        f"notation, e.g. \"POSP += ma@CNJctr@@\", which is NOT a join): "
        f"{docs_with_join_plus_noisy} docs — do not use this number",
        "", "## Provenance prefixes (filename-based, first match)", ""]
    for k, v in prefix_hist.most_common():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Bracket/restoration markers (char counts)", ""]
    for k, v in sorted(bracket_freq.items(), key=lambda kv: -kv[1]):
        lines.append(f"- `{k}` : {v:,}")
    lines += ["", "## Top 25 element tags", ""]
    for t, n in tag_counts.most_common(25):
        lines.append(f"- `<{t}>` : {n:,}")
    lines += ["", "## Top 25 attributes (with example values)", ""]
    for (t, a), n in attr_counts.most_common(25):
        ex = "; ".join(sorted(attr_examples[(t, a)])[:5])
        lines.append(f"- `{t}@{a}` ({n:,}) — e.g. {ex}")
    lines += ["", "*Full detail in inventory_report.json. "
              "Upload this .md and sample_documents.txt to the chat.*"]

    with open(OUT_DIR / "inventory_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Done. {len(xml_names)} XML docs scanned, "
          f"{len(parse_errors)} parse errors.")
    print(f"Reports in: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/01_inventory.py /path/to/TLHdig_0.2.0-beta.zip")
    main(sys.argv[1])
