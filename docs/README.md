# Cuneiform Lab Binder

A single-file, self-contained reader for navigating this project's reports,
handoffs, plans, and specs — organized as a lab binder with a tab per phase.

- **`index.html`** — the binder. Open it locally, or view the hosted version
  (see below). All document data is embedded; there are no external files to
  load and nothing to build.
- **`READING_LIST.md`** — the same content as a plain-markdown chronological
  reader, for note-taking outside the browser.
- **`.nojekyll`** — tells GitHub Pages to serve the files as-is (no Jekyll
  processing).

## What the binder does

- Eight tabs: **Now** (orientation + current state), **Phase 1–5**,
  **Expansion** (TLHdig 0.3 side-thread), and **Reference** (specs, rulings,
  migrations).
- Each document shows its declared date (or a flag that it is undated and
  ordered by dependency), any status it declares (Authoritative, Ratified,
  Superseded, Probe, Audit, Frozen), a one-line annotation, and links to every
  other repo document it references.
- Filter/search, a one-hour reading path, per-document read marks, a reading
  list, and inline note/quotation boxes. Read marks and notes are saved in your
  own browser (`localStorage`) — they are personal and never committed.

The date shown for each document is the first ISO date found in its body: treat
it as a reliable "existed by" bound rather than a guaranteed authored-on date.
The handoff spine the chronology rests on is self-dated in headers.

## Hosting with GitHub Pages

Two options — either works.

### Option A — automated (workflow, recommended)

This repo includes `.github/workflows/pages.yml`, which deploys the `docs/`
folder whenever it changes. To turn it on once:

1. Push this branch to GitHub.
2. Go to **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **GitHub Actions**.

The next push under `docs/` (or a manual **Run workflow** on the "Deploy binder
to Pages" action) publishes the site. The live URL will be:

```
https://brandireger.github.io/Cuneiform/
```

### Option B — no workflow (serve from a branch)

If you'd rather not use Actions:

1. **Settings → Pages → Source → Deploy from a branch.**
2. Branch: **`master`**, folder: **`/docs`**. Save.

GitHub serves `docs/index.html` at the same URL above within a minute or two.

## Updating the binder

Regenerate `index.html` (and `READING_LIST.md`) and replace the files here. With
Option A, the push redeploys automatically; with Option B, Pages re-serves the
new file on push. No other change is needed.
