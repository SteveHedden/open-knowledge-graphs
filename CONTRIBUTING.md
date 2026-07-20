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

Classify categories (optional, requires Anthropic key):

```bash
export ANTHROPIC_API_KEY=your_key_here
python scripts/classify_categories.py
```

Local site preview:

```bash
python -m http.server 8000
```

Open: `http://localhost:8000/site/`

## Quality Checks Before PR

```bash
python3 -m py_compile scripts/fetch_data.py scripts/category_classifier.py scripts/classify_categories.py
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

## Pull Request Guidelines

- Keep PRs focused and scoped to one task/theme.
- Include a short summary of behavior changes.
- Link related issues/tasks where relevant.
- Add or update docs when behavior, workflows, or schema changes.
- Preserve optional-field behavior in JSON output (omit missing keys).

## Data and Schema Guidelines

- Do not introduce required fields unless explicitly approved.
- Preserve current SHACL constraints unless the task requires updates.
- Keep `wikidataId` as an IRI-valued field.
- Prefer deterministic output ordering where possible.

## Workflow and Deployment Notes

- Data refresh workflow (`update-data.yml`) runs daily at 06:00 UTC.
- Deployment workflow (`deploy.yml`) publishes `site/`, `data/`, and `ontology.ttl`.
- Use `openknowledgegraphs.com` URLs in docs and public references.

## Reporting Problems

- Open an issue with:
  - repro steps
  - expected vs actual behavior
  - relevant logs/screenshots
  - affected files/workflow runs
