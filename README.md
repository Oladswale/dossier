# Curator

A personal, free, self-hosted news-curation engine. It crawls RSS feeds
across categories you define (finance, wealth building, education, real
estate, entertainment, or whatever you want), pulls a summary for each
article (the publisher's own summary if there is one, otherwise a free
local extractive summary — no paid APIs involved anywhere), and serves the
result as an installable PWA on GitHub Pages.

**How it works, end to end:**

1. `sources.yaml` lists the feeds you care about, grouped by category.
2. A GitHub Actions workflow (`.github/workflows/crawl.yml`) runs the
   crawler (`crawler/main.py`) on a schedule (every 6 hours by default).
   It fetches each feed, summarizes new entries, de-duplicates against
   what's already stored, and writes the result to `docs/data/*.json`.
3. The workflow commits that JSON straight back into the repo.
4. GitHub Pages serves the `docs/` folder as a static site — the PWA in
   `docs/index.html` just fetches those JSON files and renders them. No
   server, no database, no hosting cost.

Because everything lives in git, you also get a full history of what was
crawled and when, for free.

## One-time setup

1. Create a new GitHub repo and push this folder to it.
2. In the repo settings → **Pages**, set source to "Deploy from a branch",
   branch `main`, folder `/docs`. Save. GitHub will give you a URL like
   `https://yourname.github.io/curator/`.
3. In repo settings → **Actions → General → Workflow permissions**, select
   "Read and write permissions" (the crawler needs to commit data back).
4. Edit `sources.yaml` to your liking (a starter list across five
   categories is already in there — see "About the starter sources" below).
5. Commit and push. This triggers the first crawl automatically (the
   workflow runs on any push that touches `sources.yaml`). You can also
   trigger a run manually any time from the **Actions** tab →
   "Crawl sources" → **Run workflow**.
6. After the first successful run, visit your Pages URL. On your phone,
   open it in the browser and use "Add to Home Screen" (iOS Safari) or
   the install prompt (Android Chrome) to install it as an app.

## Before you push: check your sources

Feed URLs go dead over time. Run this locally before pushing changes to
`sources.yaml`:

```bash
pip install -r requirements.txt
python crawler/check_sources.py
```

It reports which feeds are alive and which aren't, so you can prune
without waiting for a scheduled run to fail silently.

You can also run the crawler itself locally to see output before pushing:

```bash
python crawler/main.py
```

## About the starter sources

`sources.yaml` ships with a first pass at feeds across your five
categories, including a couple of Nigeria-specific ones for finance
(Nairametrics, TechCabal) since that's relevant to your context. I picked
well-known feeds, but RSS URLs do change or disappear — run
`check_sources.py` after your first clone to confirm what's actually live,
and swap in whatever sources you personally trust. Adding a new source is
just adding a `name`/`url` pair under the right category in the YAML.

## Adding a new category

1. Add a new key to `sources.yaml` with its list of sources.
2. Add a matching entry to `docs/data/categories.json` (id, label, color).
   The `id` must match the YAML key exactly.
3. Push. The next crawl will create `docs/data/{your-category}.json`
   automatically.

## On privacy

This is **not** password-protected. `robots.txt` and a `noindex` meta tag
keep it out of search engines, but the URL itself isn't secret — anyone
with the exact link could open it if a private repo isn't used. Given
there's nothing sensitive in it, that's an acceptable tradeoff for now. If
you later want real access control, the straightforward upgrade is a
private repo + GitHub Pro (Pages can then restrict access to repo
collaborators only).

## Where this could go later

Nothing here locks you in if you decide to grow this beyond personal use —
a few natural next steps, if you ever want them:

- **Better summarization**: swap the free extractive summarizer for an
  LLM call once/if budget allows — `crawler/summarize.py` is the only file
  that would need to change.
- **Smarter categorization**: right now categorization is manual (a
  source's feed always lands in the category you assigned it to in
  `sources.yaml`). A keyword-tagging layer could auto-sort mixed-topic
  sources later.
- **Read-later / notes**: the read-state is already tracked client-side
  (localStorage) — a "save for later" list or personal notes per article
  would slot into the same pattern.
- **Multi-user**: if this ever became something you'd share, the JSON-per-
  category structure could become a lightweight public API on its own.

None of that needs deciding now — the current design doesn't foreclose any
of it.
