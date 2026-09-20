# Contributing

Thanks for contributing to Open Knowledge Graph Resources.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Common Tasks

Refresh data:

```bash
python scripts/fetch_data.py
```

Review pending classifications without a paid LLM API:

```bash
python scripts/classification_review.py backlog
python scripts/classification_issue.py --repository SteveHedden/open-knowledge-graphs
```

Follow [the Codex review workflow](docs/classification-review.md) to inspect evidence,
prepare RDF results, validate/import them, and publish through the coordinated release.
Unreviewed eligible records can publish; tagging is independent of job admission.

Local site preview:

```bash
python -m http.server 8000
```

Open: `http://localhost:8000/site/`

## Quality Checks Before PR

```bash
python3 -m py_compile scripts/fetch_data.py scripts/category_classifier.py scripts/classification_review.py
node --check site/app.js
python3 - <<'PY'
from rdflib import Graph
Graph().parse('ontology.ttl', format='turtle')
print('ontology.ttl parse ok')
PY
```

If your change affects generated datasets, include updated files in `data/`.

## Adding a Resource

All catalog resources are sourced from Wikidata — there is no direct way to add one to OKG
itself. See [`docs/adding-resources-through-wikidata.md`](docs/adding-resources-through-wikidata.md)
for the full workflow (identity resolution, notability, ingestible classes, and verification),
and use the "Resource batch" issue template to propose and track a batch of candidates.

Release metadata follows Wikidata P348 statements with P577 qualifiers on the same
statement. Repository release pages are not polled. See [release metadata and
activity history](docs/releases-and-events.md) for supported fields, precision,
missing-data behavior and the shared event contract.

## Pull Request Guidelines

- Keep PRs focused and scoped to one task/theme.
- Include a short summary of behavior changes.
- Link related issues/tasks where relevant.
- Add or update docs when behavior, workflows, or schema changes.
- Preserve optional-field behavior in JSON output (omit missing keys).
- Treat Wikidata edits as public external mutations: commit and review an evidence-backed dry-run audit first, and never execute live edits without separate explicit approval.

## Data and Schema Guidelines

- Do not introduce required fields unless explicitly approved.
- Preserve current SHACL constraints unless the task requires updates.
- Keep `wikidataId` as an IRI-valued field.
- Prefer deterministic output ordering where possible.
- Declare source eligibility markers, exclusions, and reviewed exceptions in `sources.ttl`; do not duplicate their QIDs in Python or turn labels, descriptions, or URL shapes into automatic exclusions.

## Workflow and Deployment Notes

- Resource, software and jobs refresh independently and store immutable dataset snapshots without committing to main.
- `update-data.yml` pins validated snapshots and code, assembles shared artifacts and serializes exact-generation publication.
- See [refresh/publication operations](docs/independent-refreshes.md) for schedules, compatibility, retries and recovery.
- `deploy.yml` is a manual rollback path accepting a generation ID or Git ref; successful rollback moves catalog pointers without reverting repository history.
- Do not move `catalog-generation/*` tags. They are immutable successful-publication records.
- Use `openknowledgegraphs.com` URLs in docs and public references.

## Reporting Problems

- Open an issue with:
  - repro steps
  - expected vs actual behavior
  - relevant logs/screenshots
  - affected files/workflow runs
