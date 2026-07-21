#!/usr/bin/env python3
"""
14_tyndall.py -- P3 Deliverable 3: fenced Tyndall (2012) replication.

Usage:
    python 14_tyndall.py

Uses TYNDALL'S OWN split semantics (fragment-level 10-fold CV WITHIN
compositions -- a closed-set classifier that has seen other witnesses
of each test composition during training), which is a fundamentally
different protocol from our frozen zero-shot main_split/site_split.
Every output is labeled protocol=tyndall2012 and MUST NOT be mixed
into eval_harness.py's tables.

Corpus caveat (same fix as eval_harness.py): 28 doc_ids are ambiguous
(cross-filed under two CTH numbers, or two different files sharing an
identical <docID> string) -- excluded from the population here too,
for the same cleanroom-safety reason.

Tokenizations (Tyndall's own two): all-token (bag of sign tokens,
reusing eval_harness's bm25_sign tokenizer minus bigrams) and
ideogram-only (Sumero-/Akkadograms only). Renderings: FULL
(restorations kept as plain text -- this is the closest match to
Tyndall's "brackets removed" condition, his best-reported 0.67) and
ATTESTED (restorations fully excluded -- a condition Tyndall never
tested; the FULL-vs-ATTESTED delta retro-quantifies how much of his
2012 result was restoration leakage). His "plain" condition (bracket
markup characters left visibly in the token stream) is NOT
reconstructed here -- out of scope, noted in the report rather than
silently approximated.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

sys.path.insert(0, str(Path(__file__).parent))
import eval_harness as eh

OUT_DIR = Path("results") / "tyndall_replication"
SEED = 20260722
N_FOLDS = 10
APPROX_TARGET_COMPOSITIONS = 36
APPROX_TARGET_FRAGMENTS = 389

TYNDALL_PUBLISHED = {
    "plain": {"NB_alltoken": 0.55, "MaxEnt_alltoken": 0.61,
              "NB_ideogram": 0.44, "MaxEnt_ideogram": 0.51},
    "brackets_removed": {"NB_alltoken": 0.64, "MaxEnt_alltoken": 0.67,
                          "NB_ideogram": 0.49, "MaxEnt_ideogram": 0.54},
}


def build_population():
    splits = pd.read_parquet(eh.P2_OUT / "splits.parquet")
    doc_table = pd.read_parquet(eh.P2_OUT / "doc_table.parquet")
    bins_df = pd.read_csv(eh.P25_OUT / "cth_bins.csv")
    is_bin_by_cth = dict(zip(bins_df["cth"], bins_df["is_bin"]))

    dup_doc_ids = set(splits.loc[splits.duplicated("doc_id", keep=False), "doc_id"])
    doc_table = doc_table[~doc_table["doc_id"].isin(dup_doc_ids)].copy()
    doc_table = doc_table[doc_table["cth"].notna()].copy()
    doc_table["cth"] = doc_table["cth"].astype(int)
    doc_table["is_bin"] = doc_table["cth"].map(is_bin_by_cth).fillna(False)
    real = doc_table[~doc_table["is_bin"]]

    counts = real.groupby("cth")["doc_id"].count()
    eligible_cth = counts[counts >= 2].index.tolist()
    pop = real[real["cth"].isin(eligible_cth)][["doc_id", "cth"]].copy()
    return pop, len(dup_doc_ids)


def sample_approx_scale(pop, seed=SEED):
    """Seeded sample targeting ~36 compositions / ~389 fragments, both
    simultaneously (not just composition count) -- shuffles
    compositions, then greedily takes them in that random order,
    stopping once BOTH targets are reached or exceeded, whichever
    happens first, to avoid drastically overshooting the fragment
    count the way a composition-count-only stop condition would."""
    rng = np.random.default_rng(seed)
    counts = pop.groupby("cth")["doc_id"].count()
    cths = counts.index.to_numpy().copy()
    rng.shuffle(cths)
    chosen, total = [], 0
    for c in cths:
        chosen.append(c)
        total += int(counts.loc[c])
        if len(chosen) >= APPROX_TARGET_COMPOSITIONS or total >= APPROX_TARGET_FRAGMENTS:
            break
    return pop[pop["cth"].isin(chosen)].copy()


def assign_folds(pop, seed=SEED, n_folds=N_FOLDS):
    rng = np.random.default_rng(seed)
    fold = np.zeros(len(pop), dtype=int)
    pop = pop.reset_index(drop=True)
    for cth, grp in pop.groupby("cth"):
        idx = grp.index.to_numpy().copy()
        rng.shuffle(idx)
        for i, row_idx in enumerate(idx):
            fold[row_idx] = i % n_folds
    pop = pop.copy()
    pop["fold"] = fold
    return pop


def render_population(pop, line_index, tokenization, rendering):
    doc_table = pd.read_parquet(eh.P2_OUT / "doc_table.parquet").set_index("doc_id")
    out = []
    for doc_id in pop["doc_id"]:
        n_lines = int(doc_table.loc[doc_id, "line_count"]) if doc_id in doc_table.index else 0
        line_idxs = range(n_lines)
        if tokenization == "ideogram":
            r = eh.render_fragment_ideogram_only(doc_id, line_idxs, line_index)
            toks = r[rendering]
        else:
            r = eh.render_fragment(doc_id, line_idxs, line_index)
            toks = r[f"sign_{rendering}"]
        out.append(toks)
    return out


def run_cv(pop_with_folds, tokens, classifier_name):
    y = pop_with_folds["cth"].to_numpy()
    fold = pop_with_folds["fold"].to_numpy()
    fold_accuracies = []
    fold_coverage = []
    for f in range(N_FOLDS):
        train_idx = np.where(fold != f)[0]
        test_idx = np.where(fold == f)[0]
        if len(test_idx) == 0:
            continue
        train_classes = set(y[train_idx])
        test_classes = set(y[test_idx])
        usable_test = [i for i in test_idx if y[i] in train_classes]
        fold_coverage.append({
            "fold": f, "n_test": len(test_idx), "n_usable_test": len(usable_test),
            "n_test_classes": len(test_classes),
            "n_test_classes_unseen_in_train": len(test_classes - train_classes),
        })
        if not usable_test:
            continue
        vec = CountVectorizer(tokenizer=lambda x: x, preprocessor=lambda x: x,
                               lowercase=False, token_pattern=None)
        Xtr = vec.fit_transform([tokens[i] for i in train_idx])
        Xte = vec.transform([tokens[i] for i in usable_test])
        ytr = y[train_idx]
        yte = y[usable_test]
        if classifier_name == "NB":
            clf = MultinomialNB()
        else:
            # lbfgs with max_iter=2000 took >60 CPU-minutes and never
            # finished on the 426-class full-scale population --
            # laptop compute budget exceeded (CLAUDE.md: redesign
            # rather than grind). saga + looser tolerance converges
            # much faster on large sparse multinomial problems; the
            # accuracy cost of the looser tolerance is a documented
            # tradeoff for a baseline replication, not a final model.
            clf = LogisticRegression(max_iter=200, solver="saga", tol=1e-2)
        clf.fit(Xtr, ytr)
        pred = clf.predict(Xte)
        acc = float(np.mean(pred == yte))
        fold_accuracies.append(acc)
        print(f"    fold {f} ({classifier_name}): acc={acc:.3f}", flush=True)
    overall = float(np.mean(fold_accuracies)) if fold_accuracies else None
    return overall, fold_accuracies, fold_coverage


def run_scale(scale_name, pop, line_index, checkpoint_path=None, all_results=None):
    pop_folded = assign_folds(pop)
    results = {}
    for tokenization in ("alltoken", "ideogram"):
        for rendering in ("full", "attested"):
            print(f"  [{scale_name}] rendering {tokenization}/{rendering}...", flush=True)
            toks = render_population(pop_folded, line_index, tokenization, rendering)
            for clf_name in ("NB", "MaxEnt"):
                print(f"  [{scale_name}] {clf_name} {tokenization}/{rendering}: "
                      f"running {N_FOLDS}-fold CV...", flush=True)
                overall, fold_acc, coverage = run_cv(
                    pop_folded, toks, "NB" if clf_name == "NB" else "LogReg")
                key = f"{clf_name}_{tokenization}_{rendering}"
                results[key] = {
                    "accuracy": overall, "fold_accuracies": fold_acc,
                    "fold_coverage": coverage, "n_folds_used": len(fold_acc),
                }
                print(f"  [{scale_name}] {key}: accuracy={overall}", flush=True)
                if checkpoint_path is not None:
                    all_results[scale_name] = {
                        "n_compositions": int(pop["cth"].nunique()), "n_docs": len(pop),
                        "results": results,
                    }
                    with open(checkpoint_path, "w", encoding="utf-8") as f:
                        json.dump({"protocol": "tyndall2012", "seed": SEED,
                                   "published_reference": TYNDALL_PUBLISHED,
                                   "scales": all_results, "status": "IN_PROGRESS"},
                                  f, ensure_ascii=False, indent=2, default=str)
    return results, pop_folded


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pop, n_dup_excluded = build_population()
    print(f"Eligible (>=2-witness real) population: {pop['cth'].nunique()} "
          f"compositions, {len(pop)} docs ({n_dup_excluded} ambiguous doc_ids excluded)")

    approx_pop = sample_approx_scale(pop)
    print(f"Approx-scale sample: {approx_pop['cth'].nunique()} compositions, "
          f"{len(approx_pop)} docs (target {APPROX_TARGET_COMPOSITIONS}/{APPROX_TARGET_FRAGMENTS})")

    corpus = pd.read_parquet(eh.P2_OUT / "corpus.parquet")
    line_index = eh.build_line_index(corpus)
    del corpus

    checkpoint_path = OUT_DIR / "metrics_checkpoint.json"
    all_results = {}
    for scale_name, scale_pop in (("approx_scale", approx_pop), ("full_scale", pop)):
        print(f"\n=== {scale_name} ===", flush=True)
        results, pop_folded = run_scale(scale_name, scale_pop, line_index,
                                         checkpoint_path=checkpoint_path, all_results=all_results)
        all_results[scale_name] = {
            "n_compositions": int(scale_pop["cth"].nunique()), "n_docs": len(scale_pop),
            "results": results,
        }
        for k, v in results.items():
            print(f"  {k}: accuracy={v['accuracy']}", flush=True)

    with open(OUT_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump({"protocol": "tyndall2012", "seed": SEED,
                   "published_reference": TYNDALL_PUBLISHED,
                   "scales": all_results}, f, ensure_ascii=False, indent=2, default=str)
    checkpoint_path.unlink(missing_ok=True)

    lines = [
        "# Tyndall (2012) Fenced Replication -- protocol=tyndall2012", "",
        "**FENCED: this uses Tyndall's own fragment-level 10-fold-CV-"
        "within-compositions protocol, a closed-set classification task "
        "fundamentally different from eval_harness.py's zero-shot "
        "retrieval tables. Never mix these numbers into the main P3 "
        "results.**", "",
        f"- Ambiguous doc_ids excluded (cross-filed under 2 CTH numbers "
        f"or colliding docID text -- see eval_harness.py docstring): {n_dup_excluded}",
        f"- Eligible population (real, >=2-witness compositions): "
        f"{pop['cth'].nunique()} compositions, {len(pop)} docs",
        f"- Approx-scale sample (seed={SEED}): {approx_pop['cth'].nunique()} "
        f"compositions, {len(approx_pop)} docs "
        f"(Tyndall 2012: 36 compositions, 389 fragments)",
        "",
        "## Scope note: 'plain' vs 'brackets-removed'",
        "Tyndall's 'brackets removed' condition (restorations kept as "
        "plain text, bracket punctuation stripped) corresponds to our "
        "FULL rendering. His 'plain' condition (bracket markup "
        "characters left in the token stream) is NOT reconstructed "
        "here -- out of scope. ATTESTED (restorations fully excluded) "
        "is a condition Tyndall never tested; it retro-quantifies "
        "restoration leakage in his reported numbers.",
        "",
        "## Published reference (Tyndall 2012)", "",
        "| condition | NB all-token | MaxEnt all-token | NB ideogram | MaxEnt ideogram |",
        "|---|---|---|---|---|",
    ]
    for cond, vals in TYNDALL_PUBLISHED.items():
        lines.append(f"| {cond} | {vals['NB_alltoken']} | {vals['MaxEnt_alltoken']} | "
                      f"{vals['NB_ideogram']} | {vals['MaxEnt_ideogram']} |")

    for scale_name in ("approx_scale", "full_scale"):
        r = all_results[scale_name]["results"]
        lines += [f"", f"## {scale_name} replication "
                  f"({all_results[scale_name]['n_compositions']} comps, "
                  f"{all_results[scale_name]['n_docs']} docs)", "",
                  "| classifier | tokenization | rendering | accuracy | n folds used |",
                  "|---|---|---|---|---|"]
        for k, v in r.items():
            clf, tok, rend = k.split("_", 2)
            lines.append(f"| {clf} | {tok} | {rend} | {v['accuracy']} | {v['n_folds_used']} |")

        full_maxent_all = r.get("MaxEnt_alltoken_full", {}).get("accuracy")
        att_maxent_all = r.get("MaxEnt_alltoken_attested", {}).get("accuracy")
        if full_maxent_all is not None and att_maxent_all is not None:
            lines.append(f"\n**FULL vs ATTESTED delta (MaxEnt, all-token) -- "
                         f"restoration-leakage estimate: "
                         f"{full_maxent_all - att_maxent_all:+.3f}** "
                         f"(FULL={full_maxent_all:.3f} vs published brackets-removed "
                         f"MaxEnt_alltoken={TYNDALL_PUBLISHED['brackets_removed']['MaxEnt_alltoken']})")

        lines.append("\n### Fold class coverage (honest reporting, per spec)")
        sample_key = "MaxEnt_alltoken_full"
        if sample_key in r:
            for fc in r[sample_key]["fold_coverage"]:
                lines.append(f"- fold {fc['fold']}: {fc['n_test']} test docs, "
                             f"{fc['n_usable_test']} usable (class seen in train), "
                             f"{fc['n_test_classes_unseen_in_train']} test-only "
                             f"(unseen-in-train) classes excluded")

    with open(OUT_DIR / "report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nDone. Report: {(OUT_DIR / 'report.md').resolve()}")


if __name__ == "__main__":
    main()
