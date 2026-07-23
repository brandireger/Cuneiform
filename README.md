# Hittite Fragment Matching

Research code and governed artifacts for evidence-bounded reconstruction of
missing information in fragmentary Hittite cuneiform texts. The project asks
what textual or structural context can be predicted from the evidence TLHdig
actually encodes, when the system must abstain, and how much each conclusion
depends on editorial or model assistance. Composition affinity,
duplicate/parallel discovery, and physical-join suggestion are downstream
applications rather than the organizing objective.

The intended interface is decision support for a trained Hittite specialist:
for a missing sign or span, show a ranked set of evidence-supported
possibilities, their out-of-sample calibration statistics and confidence
intervals, the evidence for and against each option, and an explicit
`other / unsupported` path. It is not an automatic restoration tool for lay
users, and top-1 exact match is not its sole success criterion.

**Phase 2 is now complete as an exploratory characterization phase.** It
mapped what evidence is recoverable from the corpus before training or
promoting further models. Phase 1 produced useful baselines and several
negative results; its full, immutable snapshot is preserved under `Archive/`.
The next workstream is a small expert missing-text UI prototype against the
versioned decision contract, not another undirected model-training pass.

The first Phase 2 recoverability map is now available in
[`reports/phase2_p2e_witness_recoverability.md`](reports/phase2_p2e_witness_recoverability.md).
It measures when independent witnesses constrain intentionally hidden
attested spans, preserving variants, ambiguity, and abstention instead of
treating every gap as safely reconstructable. Its abstention-calibration
follow-up is
[`reports/phase2_p2e2_abstention_calibration.md`](reports/phase2_p2e2_abstention_calibration.md):
high-agreement witness reconstruction exists for a small one-sign region,
but its reliability threshold does not yet transfer stably across
compositions. The five-fold stability audit is in
[`reports/phase2_p2e3_cross_calibration.md`](reports/phase2_p2e3_cross_calibration.md);
it shows that pooled agreement is concentrated in recurrent, witness-rich
contexts and must not be treated as a universal reliability guarantee.
The expert candidate-set audit is in
[`reports/phase2_p2e4_candidate_set_audit.md`](reports/phase2_p2e4_candidate_set_audit.md);
in the fold-selected dev contexts, showing a mean of 1.34 options retained
the intentionally hidden attested sign 92.95% of the time versus 89.97% at
top-1. Most residual disagreements did not contain that reading anywhere in
the exact-anchor witness set, motivating an inspectable local-alignment
probe rather than a larger opaque model.
That residual probe is reported in
[`reports/phase2_p2e5_alignment_probe.md`](reports/phase2_p2e5_alignment_probe.md).
Alignment recovered only 6/387 post-hoc absences at depth five; even an
unimplementable residual-only oracle would add just 0.11 percentage points.
The alignment code and evidence packets are retained as a negative result,
but the scorer is not being promoted into the UI.

The multi-sign horizon is reported in
[`reports/phase2_p2e6_multisign_horizon.md`](reports/phase2_p2e6_multisign_horizon.md).
Tie-complete witness sets effectively recovered 27.36% of eligible two-sign
contexts, declining to 7.95% for five signs; composition-macro rates were
lower. Equal-evidence ties also expanded a nominal five-option set to as many
as 237 alternatives, and composition-held-out set calibration transferred
poorly. The layer is therefore retained only as abstention-first expert
evidence—never automatic completion or per-option truth probability. The next
target was an expert decision-interface contract and Phase 2 closeout; both
are now complete.

Contract v1.0.0 is specified in
[`specs/EXPERT_DECISION_CONTRACT.md`](specs/EXPERT_DECISION_CONTRACT.md) and
implemented by
[`lib/expert_decision_contract.py`](lib/expert_decision_contract.py). It
supports select, reject-all, other/unsupported, and withhold-judgment actions;
forbids automatic completion and per-option truth-probability claims; and
keeps every expert decision quarantined pending adjudication. See
[`PHASE2_CLOSEOUT.md`](PHASE2_CLOSEOUT.md) for the complete handoff.

## Read first

- [`AGENTS.md`](AGENTS.md) — design authority for Codex sessions:
  corpus schema, cleanroom rules, task definitions, and engineering standards.
- [`CLAUDE.md`](CLAUDE.md) — corresponding design authority for
  Claude Code sessions.
- [`PHASE2_CHARTER.md`](PHASE2_CHARTER.md) — current research questions
  and probe menu.
- [`SANDBOX_RULES.md`](SANDBOX_RULES.md) — Phase 2 experimental governance.
- [`specs/EVIDENCE_POLICY.md`](specs/EVIDENCE_POLICY.md) — mandatory
  evidence classes, assistance profiles, and run-manifest contract.
- [`P5_CLOSEOUT.md`](P5_CLOSEOUT.md) — Phase 1 closeout and rationale for
  the Phase 2 reframe.

Use the authority file for the active agent. If `AGENTS.md` and `CLAUDE.md`
disagree substantively, stop and ask the human collaborator which decision
controls rather than silently choosing one. A later, human-ratified document
may explicitly supersede either file.

## Repository map

| Path | Purpose |
|---|---|
| `lib/` | Reusable active modules and fail-closed contracts carried into Phase 2. |
| `scripts/` | Active utilities retained for Phase 2. Historical numbered implementations live in `Archive/scripts/`. |
| `configs/` | Active tokenizer, training, and evidence-policy configuration. |
| `tests/` | Lightweight governance and evidence-policy regression tests. |
| `demo/` | Parallel Takšan demonstration track; it does not control research evaluation. |
| `p2_out/`, `p4_out/` | Small tracked artifacts plus local, gitignored derived data required by active work. |
| `phase2_out/` | Small manifests and machine-readable outputs from active Phase 2 probes. |
| `reports/` | Current reports and selected Phase 1 closeout material used by Phase 2. |
| `specs/` | Current and carried-forward specifications. |
| `Archive/` | Frozen Phase 1 snapshot, including the complete numbered pipeline, historical results, reports, and references. Do not rewrite it in place. |
| `CITATION.cff` | Citation metadata for this research software. |
| `LICENSE` | MIT license for the repository's original source code. |

Some Phase 1 utilities are copied into the active tree because Phase 2 still
uses them. Their historical results remain frozen. A copied legacy utility is
not automatically compliant with the newer evidence-policy layer; every new
Phase 2 scoring or training run must integrate that layer explicitly.

## Corpus setup

Pinned corpus:

- **TLHdig Beta 0.2.0**
- DOI: [10.5281/zenodo.15459134](https://doi.org/10.5281/zenodo.15459134)
- File: `TLHdig_0.2.0-beta.zip`
- Expected MD5: `93e71e2560f5e109c87713d5590cb059`
- License: CC BY 4.0

Download the zip from Zenodo, keep it unextracted at the repository root, and
verify it on Windows:

```powershell
Get-FileHash TLHdig_0.2.0-beta.zip -Algorithm MD5
```

The raw corpus, derived parquet files, and model checkpoints are intentionally
gitignored.

## Environment

The pinned environment targets a CUDA 12.4 machine:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Python 3.11 or 3.12 must be installed and available as `python` before
creating the environment. The local `.venv/` is gitignored.

The full install includes a large CUDA-enabled PyTorch wheel. For the lighter
repository quality checks, install the CI dependency set instead:

```powershell
python -m pip install -r requirements-ci.txt
python -m unittest discover -s tests -v
python lib/contracts.py
ruff check lib scripts tests demo
```

Always run scripts from the repository root because data paths are
working-directory relative:

```powershell
python scripts/evidence_policy_smoke.py
```

Do not treat the smoke script as a research probe or citable result.

## Current safeguards

- Test-side fragments and restorations are protected by cleanroom rules.
- Composition splits are frozen and composition-disjoint.
- New semantic inputs must be registered in
  `configs/evidence_registry.yaml`.
- Evidence policies fail closed on unknown fields, prohibited classes,
  explicitly denied dependencies, technical identifiers used as semantic
  features, and mismatched manifest policy labels.
- Model-generated suggestions remain quarantined for expert verification.

## Citation, attribution, and licensing

Corpus attribution: Müller, Prechel, Rieken & Schwemer (2025), TLHdig Beta
0.2.0, DOI 10.5281/zenodo.15459134, CC BY 4.0.

Citation metadata for this research software is available in
[`CITATION.cff`](CITATION.cff).

The repository's original source code is Copyright (c) 2026 Brandi Reger and
licensed under the [`MIT License`](LICENSE). The TLHdig corpus and other
third-party materials retain their own licenses; the MIT license does not
replace or broaden those terms.
