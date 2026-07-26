"""Shared reader for the ratified `line_lang_canonical` field.

Per specs/LINE_LANG_MIGRATION.md: this project's corpus is multilingual
at LINE granularity (Hittite, Akkadian, Sumerian, Hattic, Luwian,
Palaic, Hurrian), but nothing downstream checked language at all until
this module existed -- every anchor index, vocab build, and witness
match treated every line as if it were Hittite. This is the single
choke point for consuming the ratified field; do not re-derive
`line_lang_canonical` from `Phase1_pipeline/p2_out/corpus.parquet`'s
own (data-quality-flagged, unratified) `line_lang` column elsewhere.

Fails toward EXCLUSION, not inclusion: a line whose canonical language
could not be confirmed (missing, malformed, or unrecognized -- see
migrations/line_lang_v1/audit_report.md) is treated as NOT Hittite by
`is_hittite_line()`, since an unconfirmed line could be non-Hittite and
this module's purpose is keeping non-Hittite content out of Hittite-only
vocabulary/anchor construction, not guessing it in.
"""

from pathlib import Path

import pandas as pd

CANONICAL_PATH = Path("migrations/line_lang_v1/line_lang_canonical.parquet")
HITTITE_CODE = "Hit"


def load_line_lang_lookup(path=CANONICAL_PATH):
    """(doc_id, line_index_in_doc) -> line_lang_canonical (str or None).

    Raises if the ratified migration artifact hasn't been built --
    fail closed rather than silently treating every line as unknown."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/line_lang_rebuild.py first "
            "(specs/LINE_LANG_MIGRATION.md Step C) before any code that "
            "needs to distinguish Hittite from non-Hittite lines.")
    df = pd.read_parquet(
        path, columns=["doc_id", "line_index_in_doc", "line_lang_canonical"])
    return {
        (row.doc_id, int(row.line_index_in_doc)): row.line_lang_canonical
        for row in df.itertuples(index=False)
    }


def is_hittite_line(lookup, doc_id, line_index_in_doc):
    """True only for a CONFIRMED-Hittite line. Lines absent from the
    lookup (e.g. no <lb> at that index) or with a non-Hit canonical
    value (including null/unresolved) are NOT Hittite by this check."""
    return lookup.get((doc_id, line_index_in_doc)) == HITTITE_CODE
