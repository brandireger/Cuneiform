# Hittite Fragment Matching

Research code and governed artifacts for a content-based join and duplicate
suggester for fragmentary Hittite cuneiform texts. The project uses the
openly licensed TLHdig Beta 0.2.0 corpus and targets a reproducible prototype,
a graduate-mentorship demonstration, and an Ancient Language Processing
workshop paper.

The project is currently in **Phase 2**: characterizing what evidence is
recoverable from the corpus before training or promoting further models.
Phase 1 produced useful baselines and several negative results; its full,
immutable snapshot is preserved under `Archive/`.

## Read first

- [`CLAUDE.md`](CLAUDE.md) — living design authority: corpus schema,
  cleanroom rules, task definitions, and engineering standards.
- [`PHASE2_CHARTER.md`](PHASE2_CHARTER.md) — current research questions
  and probe menu.
- [`SANDBOX_RULES.md`](SANDBOX_RULES.md) — Phase 2 experimental governance.
- [`specs/EVIDENCE_POLICY.md`](specs/EVIDENCE_POLICY.md) — mandatory
  evidence classes, assistance profiles, and run-manifest contract.
- [`P5_CLOSEOUT.md`](P5_CLOSEOUT.md) — Phase 1 closeout and rationale for
  the Phase 2 reframe.

If these documents disagree, `CLAUDE.md` controls unless a later,
human-ratified document explicitly supersedes it.

## Repository map

| Path | Purpose |
|---|---|
| `lib/` | Reusable active modules and fail-closed contracts carried into Phase 2. |
| `scripts/` | Active utilities retained for Phase 2. Historical numbered implementations live in `Archive/scripts/`. |
| `configs/` | Active tokenizer, training, and evidence-policy configuration. |
| `tests/` | Lightweight governance and evidence-policy regression tests. |
| `demo/` | Parallel Takšan demonstration track; it does not control research evaluation. |
| `p2_out/`, `p4_out/` | Small tracked artifacts plus local, gitignored derived data required by active work. |
| `reports/` | Current reports and selected Phase 1 closeout material used by Phase 2. |
| `specs/` | Current and carried-forward specifications. |
| `Archive/` | Frozen Phase 1 snapshot, including the complete numbered pipeline, historical results, reports, and references. Do not rewrite it in place. |

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
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The full install includes a large CUDA-enabled PyTorch wheel. For governance
tests only, PyYAML is sufficient:

```powershell
python -m pip install pyyaml==6.0.3
python -m unittest discover -s tests -v
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

## Attribution and licensing status

Corpus attribution: Müller, Prechel, Rieken & Schwemer (2025), TLHdig Beta
0.2.0, DOI 10.5281/zenodo.15459134, CC BY 4.0.

A separate license for this repository's original source code has not yet
been selected. The corpus license does not by itself license the project
code. Reuse of the code should wait until the project owner adds an explicit
code license.
