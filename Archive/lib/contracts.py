"""lib/contracts.py -- hard contracts at ingress points, per
P5C_AMENDMENT_2.md H3.

Diagnosis on record (P5C_AMENDMENT_2.md): all three bugs caught this
cycle (H1 family exclusion, IDF reference drift, flatten_lines tuples)
share one shape -- a silent representation/bookkeeping mismatch at an
interface, absorbed without error by a defaulting lookup, a permissive
type, or a per-script reimplementation. These helpers are meant to run
at EVERY ingress (import and call them inline in scoring/training/
reporting scripts), not once in a test file -- an assert that never
runs protects nothing.

C1-C7 raise (AssertionError/ValueError/TypeError) on violation. C8/C9
are WARN-only: they print + return a finding but do not raise, because
the underlying data may be correct and the design intent wrong -- the
fit/run proceeds, but silence about the disagreement is not allowed.
C10 is a query helper for the reporting layer (find(), not assert()).
"""
import numpy as np


# ---------------------------------------------------------------- C1

def assert_encoding_sane(ids, tokenizer, max_unk=0.05, *, label=None):
    """ids: list[int], already-encoded model input. Raises if the
    UNK-rate exceeds max_unk (corpus OOV baseline is ~0.16%; E2 ran at
    82.6%), or if there is no non-special (lexical) token at all.
    Prints ONE decoded round-trip example per call for spot audit."""
    if not ids:
        raise ValueError(f"assert_encoding_sane({label}): empty ids sequence")
    n_unk = sum(1 for i in ids if i == tokenizer.unk_id)
    unk_rate = n_unk / len(ids)
    special_ids = {tokenizer.vocab[s] for s in tokenizer.specials if s in tokenizer.vocab}
    n_non_special = sum(1 for i in ids if i not in special_ids)
    decoded = tokenizer.decode(ids)
    print(f"[C1 assert_encoding_sane{f' ({label})' if label else ''}] "
          f"n={len(ids)} unk_rate={unk_rate:.4f} non_special={n_non_special} "
          f"round-trip sample: {decoded[:12]}")
    if unk_rate > max_unk:
        raise AssertionError(
            f"assert_encoding_sane({label}): UNK rate {unk_rate:.4f} exceeds "
            f"max_unk={max_unk} ({n_unk}/{len(ids)} tokens). This is exactly "
            f"E2's signature (82.6% UNK) -- check encode_fragment_window() is "
            f"in use, not a local reimplementation.")
    if n_non_special == 0:
        raise AssertionError(
            f"assert_encoding_sane({label}): zero non-special tokens -- "
            f"content-free window, structure-only input.")


# ---------------------------------------------------------------- C2

def assert_parallel(*seqs, label=None):
    """Raises unless all given parallel sequences (tokens /
    damage_states / glyphs, ...) have equal length. Call at
    CONSTRUCTION time, before they're zipped together downstream."""
    lens = [len(s) for s in seqs]
    if len(set(lens)) > 1:
        raise AssertionError(
            f"assert_parallel({label}): parallel sequences have mismatched "
            f"lengths {lens} -- construction-time desync.")


# ---------------------------------------------------------------- C3

def assert_truth_reachable(query, gold, candidate_ids, *, ceiling_exclusions=None):
    """gold: str or set[str], the true partner id(s) for `query`.
    Raises unless every gold id is in candidate_ids, OR is explicitly
    declared in ceiling_exclusions (a set containing either `query`
    itself or (query, gold) tuples -- i.e. counted into a REPORTED
    ceiling-exclusion line, not silently dropped). This is H1's bug
    shape made impossible to repeat silently: truth excluded, 0.0 read
    as 'hard task' instead of 'broken plumbing'."""
    gold_set = {gold} if isinstance(gold, str) else set(gold)
    cand_set = set(candidate_ids)
    missing = gold_set - cand_set
    if not missing:
        return
    excl = ceiling_exclusions or set()
    truly_missing = {g for g in missing if (query, g) not in excl and query not in excl}
    if truly_missing:
        raise AssertionError(
            f"assert_truth_reachable({query}): gold partner(s) {truly_missing} "
            f"not in candidate universe (n={len(cand_set)}) and not declared "
            f"in a reported ceiling-exclusion line.")


# ---------------------------------------------------------------- C4

def stamp_stats(stats, universe_name, n, content_hash=None):
    """Wraps a fitted corpus statistic (BM25 IDF/avgdl, calibration
    distribution, vocab, ...) with provenance at fit time."""
    return {"stats": stats, "universe_name": universe_name, "n": n,
            "content_hash": content_hash}


def assert_stats_provenance(stamped, expected_universe, expected_n):
    """stamped: a stamp_stats() dict. Raises if universe_name/n don't
    match what the consumer declares it expects -- Amendment 1's BM25
    reference-set convention, enforced in code rather than prose."""
    if not isinstance(stamped, dict) or "universe_name" not in stamped:
        raise AssertionError(
            "assert_stats_provenance: stats object is not stamped (missing "
            "universe_name/n/content_hash) -- use stamp_stats() at fit time.")
    if stamped["universe_name"] != expected_universe:
        raise AssertionError(
            f"assert_stats_provenance: stats fit over universe "
            f"'{stamped['universe_name']}' (n={stamped['n']}), but this "
            f"consumer declared it expects '{expected_universe}' "
            f"(n={expected_n}).")
    if stamped["n"] != expected_n:
        raise AssertionError(
            f"assert_stats_provenance: universe name matches "
            f"('{expected_universe}') but n={stamped['n']} != expected "
            f"{expected_n} -- universe drifted without a name change.")


# ---------------------------------------------------------------- C5

def assert_no_test(ids, splits_lookup, *, label=None):
    """splits_lookup: fragment_id -> main_split. Raises if any id's
    main_split == 'test'."""
    bad = [i for i in ids if splits_lookup.get(i) == "test"]
    if bad:
        raise AssertionError(
            f"assert_no_test({label}): {len(bad)} test-side id(s) reached a "
            f"training/scoring ingress: {bad[:5]}...")


def assert_dev_only_selection(split_name, *, label=None):
    """Raises unless split_name == 'dev' -- guards model-selection
    ingress points that must never read test."""
    if split_name != "dev":
        raise AssertionError(
            f"assert_dev_only_selection({label}): selection ingress called "
            f"with split='{split_name}', must be 'dev'.")


# ---------------------------------------------------------------- C6

def assert_unique_docids(frame, id_col="fragment_id"):
    """frame: a pandas DataFrame. Raises if id_col has duplicates --
    the canonical fragment-universe loader (with its 28-ambiguous
    exclusion) is the ONLY loader; downstream artifacts get
    re-checked here at load."""
    dupes = frame[frame[id_col].duplicated(keep=False)][id_col].unique().tolist()
    if dupes:
        raise AssertionError(
            f"assert_unique_docids: {len(dupes)} duplicate {id_col} value(s) "
            f"after loading: {dupes[:5]}... -- did this bypass the canonical "
            f"loader (eval_harness.load_fragment_universe)?")


# ---------------------------------------------------------------- C7

def assert_seam_window_bilateral(window_meta, tokenizer):
    """window_meta: dict with 'context_ids' and 'cont_ids' keys -- the
    two sides of a constructed seam window, as already-encoded ids.
    Raises unless EACH side has >= 1 non-special (lexical) token.
    E2 would also have tripped this (its windows had lexical content
    on neither side once encoded)."""
    special_ids = {tokenizer.vocab[s] for s in tokenizer.specials if s in tokenizer.vocab}
    for side_name in ("context_ids", "cont_ids"):
        if side_name not in window_meta:
            raise AssertionError(f"assert_seam_window_bilateral: missing '{side_name}' key")
        ids = window_meta[side_name]
        n_lex = sum(1 for i in ids if i not in special_ids)
        if n_lex == 0:
            raise AssertionError(
                f"assert_seam_window_bilateral: side '{side_name}' has zero "
                f"lexical tokens -- a content-blind or one-sided window "
                f"(E2's exact failure mode).")


# ---------------------------------------------------------------- C8 (WARN)

def warn_degenerate_feature(name, values, *, var_floor=1e-6):
    """values: array-like. WARNS (prints, does not raise) if variance
    is near zero or any value is NaN/inf. Returns the finding dict (or
    None if clean) so callers can embed it in a report -- the negatives'
    seam_score 0.876 +/- 0.024 was visible in the feature table all
    along; this makes it impossible to not-see."""
    arr = np.asarray(values, dtype=float)
    finding = {}
    if arr.size and not np.all(np.isfinite(arr)):
        finding["nan_inf_count"] = int((~np.isfinite(arr)).sum())
    var = float(np.var(arr)) if arr.size else 0.0
    finding.update({
        "variance": var,
        "mean": float(np.mean(arr)) if arr.size else None,
        "std": float(np.std(arr)) if arr.size else None,
        "min": float(np.min(arr)) if arr.size else None,
        "max": float(np.max(arr)) if arr.size else None,
    })
    if var < var_floor or finding.get("nan_inf_count"):
        print(f"[C8 WARN warn_degenerate_feature] feature '{name}' is degenerate: {finding}")
        return finding
    return None


# ---------------------------------------------------------------- C9 (WARN)

def check_coefficient_intent(feature_names, coefs, intents):
    """feature_names: list[str]; coefs: list[float] (fitted combiner
    coefficients); intents: dict name -> +1/-1 (declared DESIGNED
    sign, e.g. +1 = 'more join-like'). WARNS (prints + returns
    findings, does not raise) for any coefficient whose sign
    contradicts its declared intent -- the fit proceeds regardless;
    P5's negative seam_score weight sat unflagged in a coefficient
    list for a full report cycle; never silently again."""
    findings = []
    for name, coef in zip(feature_names, coefs):
        intent = intents.get(name)
        if intent is None or coef == 0:
            continue
        if (coef > 0) != (intent > 0):
            findings.append({"feature": name, "coefficient": float(coef), "designed_intent": intent})
    if findings:
        print(f"[C9 WARN check_coefficient_intent] {len(findings)} coefficient(s) "
              f"contradict their declared intent: {findings}")
    return findings


# ---------------------------------------------------------------- C10

def check_impossible_values(cells, *, min_n=20):
    """cells: list of dicts each with at least {'name', 'value', 'n'}
    (e.g. one recall@k or AUC cell). Returns the subset with value
    exactly 0.0 or 1.0 and n >= min_n -- these REQUIRE a mandatory
    one-line explanation in the emitting report (this only finds
    them; the report supplies the explanation). Legitimate zeros
    exist (tier-A full-distractor was one) but each must be claimed,
    not passed over -- v1's silent 0.0 tables (H1's bug) are the
    motivating case."""
    return [c for c in cells if c.get("n", 0) >= min_n and c.get("value") in (0.0, 1.0)]


# ==================================================================
# Self-test: each contract exercised on a constructed violation (must
# raise / must return a nonempty finding) AND on clean input (must
# pass / return no finding). Run via `python lib/contracts.py`.
# ==================================================================

def _self_test():
    import sys
    sys.path.insert(0, ".")  # allow running from repo root
    import Archive.lib.hittite_tokenizer as ht

    results = []

    def check(name, fn):
        try:
            fn()
            results.append((name, "OK"))
        except Exception as e:  # noqa: BLE001
            results.append((name, f"FAILED: {e}"))

    tok = ht.Tokenizer.load()
    line_id = tok.vocab["<LINE>"]
    unk_id = tok.unk_id
    # find one real vocab token id for clean-input tests
    real_tok = next(t for t in tok.vocab if t not in tok.specials)
    real_id = tok.vocab[real_tok]

    # ---- C1 ----
    def c1_fires():
        bad_ids = [unk_id] * 20 + [line_id]  # 95% UNK
        try:
            assert_encoding_sane(bad_ids, tok, max_unk=0.05, label="c1-violation")
        except AssertionError:
            return
        raise RuntimeError("C1 did not fire on a UNK-flooded window")
    check("C1 fires on UNK-flooded window", c1_fires)

    def c1_clean():
        good_ids = [real_id] * 20 + [line_id]
        assert_encoding_sane(good_ids, tok, max_unk=0.05, label="c1-clean")
    check("C1 passes on clean window", c1_clean)

    # ---- C2 ----
    def c2_fires():
        try:
            assert_parallel([1, 2, 3], ["a", "b"], label="c2-violation")
        except AssertionError:
            return
        raise RuntimeError("C2 did not fire on mismatched lengths")
    check("C2 fires on mismatched lengths", c2_fires)

    def c2_clean():
        assert_parallel([1, 2, 3], ["a", "b", "c"], label="c2-clean")
    check("C2 passes on equal lengths", c2_clean)

    # ---- C3 ----
    def c3_fires():
        try:
            assert_truth_reachable("q1", "gold1", ["cand1", "cand2"])
        except AssertionError:
            return
        raise RuntimeError("C3 did not fire when gold excluded from candidates")
    check("C3 fires when gold silently excluded", c3_fires)

    def c3_clean():
        assert_truth_reachable("q1", "gold1", ["cand1", "gold1", "cand2"])
        # declared exclusion also passes even though gold is absent
        assert_truth_reachable("q1", "gold1", ["cand1"], ceiling_exclusions={"q1"})
    check("C3 passes when gold present or exclusion declared", c3_clean)

    # ---- C4 ----
    def c4_fires():
        stamped = stamp_stats({"idf": [1, 2]}, universe_name="query_union", n=15153)
        try:
            assert_stats_provenance(stamped, expected_universe="full_non_test", expected_n=21920)
        except AssertionError:
            return
        raise RuntimeError("C4 did not fire on universe mismatch (the A1 bug shape)")
    check("C4 fires on universe-name mismatch (A1 bug shape)", c4_fires)

    def c4_clean():
        stamped = stamp_stats({"idf": [1, 2]}, universe_name="full_non_test", n=21920)
        assert_stats_provenance(stamped, expected_universe="full_non_test", expected_n=21920)
    check("C4 passes on matching provenance", c4_clean)

    # ---- C5 ----
    def c5_fires():
        splits = {"a": "train", "b": "test"}
        try:
            assert_no_test(["a", "b"], splits, label="c5-violation")
        except AssertionError:
            return
        raise RuntimeError("C5 did not fire on a test-side id")
    check("C5 fires on test-side id reaching ingress", c5_fires)

    def c5_clean():
        splits = {"a": "train", "b": "dev"}
        assert_no_test(["a", "b"], splits, label="c5-clean")
    check("C5 passes when no test ids present", c5_clean)

    # ---- C6 ----
    def c6_fires():
        import pandas as pd
        df = pd.DataFrame({"fragment_id": ["x", "y", "x"]})
        try:
            assert_unique_docids(df)
        except AssertionError:
            return
        raise RuntimeError("C6 did not fire on duplicate fragment_id")
    check("C6 fires on duplicate fragment_id", c6_fires)

    def c6_clean():
        import pandas as pd
        df = pd.DataFrame({"fragment_id": ["x", "y", "z"]})
        assert_unique_docids(df)
    check("C6 passes on unique fragment_ids", c6_clean)

    # ---- C7 ----
    def c7_fires():
        window_meta = {"context_ids": [line_id, line_id], "cont_ids": [real_id]}
        try:
            assert_seam_window_bilateral(window_meta, tok)
        except AssertionError:
            return
        raise RuntimeError("C7 did not fire on a one-sided (content-blind) window")
    check("C7 fires on content-blind side (E2's shape)", c7_fires)

    def c7_clean():
        window_meta = {"context_ids": [real_id, line_id], "cont_ids": [real_id]}
        assert_seam_window_bilateral(window_meta, tok)
    check("C7 passes when both sides have lexical content", c7_clean)

    # ---- C8 ----
    def c8_fires():
        finding = warn_degenerate_feature("seam_score_neg", [0.876, 0.877, 0.875, 0.876])
        if finding is None:
            raise RuntimeError("C8 did not fire on a near-zero-variance feature")
    check("C8 fires on near-zero-variance feature", c8_fires)

    def c8_clean():
        finding = warn_degenerate_feature("bm25_whole", [0.1, 5.2, 12.8, 3.4, 0.9])
        if finding is not None:
            raise RuntimeError("C8 false-fired on a healthy-variance feature")
    check("C8 silent on healthy-variance feature", c8_clean)

    # ---- C9 ----
    def c9_fires():
        findings = check_coefficient_intent(
            ["seam_score", "bm25_whole"], [-4.436, 0.004],
            {"seam_score": +1, "bm25_whole": +1})
        if not findings or findings[0]["feature"] != "seam_score":
            raise RuntimeError("C9 did not fire on P5's actual negative seam_score coefficient")
    check("C9 fires on sign-contradicting coefficient (P5's actual case)", c9_fires)

    def c9_clean():
        findings = check_coefficient_intent(
            ["bm25_whole", "bm25_edge"], [0.5, 0.3], {"bm25_whole": +1, "bm25_edge": +1})
        if findings:
            raise RuntimeError("C9 false-fired on sign-consistent coefficients")
    check("C9 silent on sign-consistent coefficients", c9_clean)

    # ---- C10 ----
    def c10_fires():
        cells = [{"name": "joins_tier_A_recall@1", "value": 0.0, "n": 27}]
        flagged = check_impossible_values(cells)
        if not flagged:
            raise RuntimeError("C10 did not flag an exact-0.0 cell with n>=20")
    check("C10 flags exact-0.0 cell (n>=20)", c10_fires)

    def c10_clean():
        cells = [{"name": "joins_tier_C_recall@1", "value": 0.2787, "n": 61}]
        flagged = check_impossible_values(cells)
        if flagged:
            raise RuntimeError("C10 false-flagged a non-extreme value")
    check("C10 silent on non-extreme values", c10_clean)

    print("\n=== contracts.py self-test results ===")
    n_fail = 0
    for name, status in results:
        print(f"  [{'PASS' if status == 'OK' else 'FAIL'}] {name}: {status}")
        if status != "OK":
            n_fail += 1
    print(f"\n{len(results) - n_fail}/{len(results)} passed.")
    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_test()
