#!/usr/bin/env python3
"""
decompose_corpus.py -- P4 D12 amendment (2026-07-22, approved by
architect): sign-level logogram decomposition.

Reusable module (unnumbered, same reason as eval_harness.py). Not a
P3/P2 rebuild -- P2/P2.5's corpus.parquet stays frozen and untouched;
this is a NEW, P4-only derived artifact (p4_out/decomposed_corpus.parquet)
built by re-walking the raw XML, because word-level sub-element
boundaries (<d>/<sGr>/<aGr> vs plain syllabic text) are NOT preserved
in corpus.parquet's flattened "signs" column -- 02_parse.py concatenates
a whole word's text before hyphen-splitting, which silently fuses e.g.
a determinative "D" with a following logogram "UTU" into one "DUTU"
token whenever there's no literal "-"/"." between them in the source
text (there usually isn't; that boundary only exists as an XML tag
edge). This module re-derives token boundaries from the true
<d>/<sGr>/<aGr> tag structure instead.

Rule (architect-specified): sGr/aGr/d content splits on '-' and '.'
(GIŠ.DINANNA -> GIŠ + DINANNA; DINGIR-LIM -> DINGIR + LIM; DUTU-uš ->
D + UTU + uš), EXCEPT a run containing '×' (ligature compounds like
KA×U) stays atomic -- one wedge-cluster, one token. Plain syllabic
text keeps the existing hyphen-split-into-signs behaviour, lowercased.
Case is preserved for logogram-class tokens (script class is free
signal: DUTU-derived tokens are uppercase, syllabic tokens lowercase).
"""

import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

OUT_DIR = Path("p4_out")
RESTORED = "restored"


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def is_junk(name: str) -> bool:
    return "__MACOSX" in name or name.rsplit("/", 1)[-1].startswith("._")


def iter_doc_order(el):
    yield ("start", el)
    if el.text:
        yield ("text", el.text)
    for child in el:
        yield from iter_doc_order(child)
        if child.tail:
            yield ("text", child.tail)
    yield ("end", el)


def split_logogram_run(text):
    """Split on '-'/'.' except inside a '×'-containing span, which
    stays atomic. Returns list of sub-strings (offsets recovered by
    caller via cumulative length, since this is a pure string op)."""
    if "×" not in text:
        # simple case: split on - and . uniformly
        parts = []
        cur = ""
        for ch in text:
            if ch in "-.":
                if cur:
                    parts.append(cur)
                cur = ""
            else:
                cur += ch
        if cur:
            parts.append(cur)
        return parts if parts else [text]
    # protect '×' runs: find the contiguous substring containing '×'
    # bounded by the nearest '-'/'.' on each side, keep it atomic,
    # split normally outside it
    parts = []
    cur = ""
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "×":
            # extend cur to the ligature boundary (next -/. or end)
            j = i
            while j < n and text[j] not in "-.":
                j += 1
            cur += text[i:j]
            i = j
            continue
        if ch in "-.":
            if cur:
                parts.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    if cur:
        parts.append(cur)
    return parts if parts else [text]


def decompose_document(raw_xml_bytes):
    """Single document-order walk (like 02_parse.py) producing, per
    word: list of (token_text, damage_state, is_num, is_logogram_class).
    Returns list of per-line dicts: {line_index, tokens: [...]}."""
    root = ET.fromstring(raw_xml_bytes)
    text_el = root.find(".//{*}text")
    if text_el is None:
        return []

    in_del = in_laes = False
    cur_source = None  # None=syllabic, else ('logogram'|'num', element_id) -- element_id
                        # makes adjacent-but-separate tags (e.g. <d>D</d><sGr>UTU</sGr>)
                        # distinct segments even though both are "logogram" type
    element_counter = [0]
    line_index = -1
    lines = []
    cur_line_tokens = None

    cur_word_runs = []  # (text, damage_state, source) per contiguous run
    in_word = False

    def state():
        return RESTORED if in_del else ("laes" if in_laes else "attested")

    def flush_word():
        nonlocal cur_word_runs
        if not cur_word_runs:
            cur_word_runs = []
            return
        # group into maximal consecutive same-source segments
        segments = []
        for text, st, src in cur_word_runs:
            if segments and segments[-1][0] == src:
                segments[-1][1].append((text, st))
            else:
                segments.append([src, [(text, st)]])
        for src, runs in segments:
            concat = "".join(t for t, _ in runs)
            if not concat:
                continue
            src_type = src[0] if src is not None else None
            if src_type == "num":
                cur_line_tokens.append(("<NUM>", "attested"))
                continue
            offsets = []
            pos = 0
            for t, st in runs:
                offsets.append((pos, pos + len(t), st))
                pos += len(t)

            def state_at(idx):
                for a, b, s in offsets:
                    if a <= idx < b:
                        return s
                return "attested"

            if src_type == "logogram":
                subtoks = split_logogram_run(concat)
            else:
                subtoks = concat.split("-")
            cursor = 0
            for tok in subtoks:
                idx_in_concat = concat.find(tok, cursor)
                if idx_in_concat < 0:
                    idx_in_concat = cursor
                cursor = idx_in_concat + len(tok)
                if not tok:
                    continue
                st = "illegible_x" if tok.strip("()") == "x" else state_at(idx_in_concat)
                out_tok = tok if src_type == "logogram" else tok.lower()
                cur_line_tokens.append((out_tok, st))
        cur_word_runs = []

    for text_child in text_el:
        for ev, payload in iter_doc_order(text_child):
            if ev == "start":
                tag = local(payload.tag)
                if tag == "lb":
                    flush_word()
                    if cur_line_tokens is not None:
                        lines.append({"line_index_in_doc": line_index, "tokens": cur_line_tokens})
                    line_index += 1
                    cur_line_tokens = []
                elif tag == "w":
                    flush_word()
                    in_word = True
                elif tag == "del_in":
                    in_del = True
                elif tag == "del_fin":
                    in_del = False
                elif tag == "laes_in":
                    in_laes = True
                elif tag == "laes_fin":
                    in_laes = False
                elif tag in ("sGr", "aGr", "d"):
                    element_counter[0] += 1
                    cur_source = ("logogram", element_counter[0])
                elif tag == "num":
                    element_counter[0] += 1
                    cur_source = ("num", element_counter[0])
                elif tag == "parsep":
                    flush_word()
                    if cur_line_tokens is not None:
                        cur_line_tokens.append(("<PAR>", "attested"))
            elif ev == "end":
                tag = local(payload.tag)
                if tag in ("sGr", "aGr", "d", "num"):
                    cur_source = None
            elif ev == "text":
                if in_word and payload.strip() and cur_line_tokens is not None:
                    cur_word_runs.append((payload.strip(), state(), cur_source))
    flush_word()
    if cur_line_tokens is not None:
        lines.append({"line_index_in_doc": line_index, "tokens": cur_line_tokens})
    return lines


def build_decomposed_cache(zip_path, doc_ids_needed=None):
    """Re-walks the corpus zip once, writing
    p4_out/decomposed_corpus.parquet: doc_id, line_index_in_doc,
    token, damage_state (word-token order preserved via row order).
    doc_ids_needed: optional set to restrict (still walks the whole
    zip since docID isn't known until parsed, but skips writing rows
    for docs not needed, to keep the cache small)."""
    OUT_DIR.mkdir(exist_ok=True)
    cache_path = OUT_DIR / "decomposed_corpus.parquet"
    if cache_path.exists():
        return cache_path

    zp = zipfile.ZipFile(zip_path)
    names = [n for n in zp.namelist() if n.lower().endswith(".xml")
             and not n.endswith("/") and not is_junk(n)]

    rows = []
    n_docs = 0
    n_errors = 0
    for name in names:
        raw = zp.read(name)
        try:
            root_check = ET.fromstring(raw)
        except ET.ParseError:
            n_errors += 1
            continue
        doc_id_el = root_check.find(".//{*}docID")
        doc_id = (doc_id_el.text or "").strip() if doc_id_el is not None else Path(name).stem
        if doc_ids_needed is not None and doc_id not in doc_ids_needed:
            continue
        try:
            lines = decompose_document(raw)
        except Exception:  # noqa: BLE001
            n_errors += 1
            continue
        n_docs += 1
        for line in lines:
            for i, (tok, st) in enumerate(line["tokens"]):
                rows.append({"doc_id": doc_id, "line_index_in_doc": line["line_index_in_doc"],
                            "word_pos": i, "token": tok, "damage_state": st})

    df = pd.DataFrame(rows)
    df.to_parquet(cache_path, index=False)
    print(f"decompose_corpus: {n_docs} docs, {n_errors} errors, {len(df):,} tokens -> {cache_path}")
    return cache_path
