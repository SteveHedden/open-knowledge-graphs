# Open Knowledge Graphs (with MCP)

Open Knowledge Graphs is a static, daily-refreshed catalog of ontology and semantic software records sourced from Wikidata. It publishes both machine-readable artifacts (Turtle + JSON) and a searchable browser UI.

## Live Links

- Site: https://openknowledgegraphs.com/
- Semantic Search API: https://api.openknowledgegraphs.com/
- Ontology schema (Turtle): https://openknowledgegraphs.com/ontology.ttl
- Ontologies dataset (Turtle): https://openknowledgegraphs.com/data/ontologies.ttl
- Ontologies dataset (JSON): https://openknowledgegraphs.com/data/ontologies.json
- Software dataset (Turtle): https://openknowledgegraphs.com/data/software.ttl
- Software dataset (JSON): https://openknowledgegraphs.com/data/software.json

## API

Semantic search over the full catalog.

```
GET https://api.openknowledgegraphs.com/search?q=movie+ontology&limit=5
GET https://api.openknowledgegraphs.com/ontologies?q=healthcare+vocabulary
GET https://api.openknowledgegraphs.com/software?q=rdf+triplestore
```

**Parameters:** `q` (required), `category`, `type` (ontology|software), `limit` (default 20, max 100)

**Categories:** Life Sciences & Healthcare, Geospatial, Government & Public Sector, International Development, Finance & Business, Library & Cultural Heritage, Technology & Web, Environment & Agriculture, General / Cross-domain

## MCP Server

The `mcp-server/` directory contains an MCP (Model Context Protocol) server that exposes the OKG catalog to AI assistants like Claude Desktop and Claude Code.

### Tools

| Tool | Description |
| --- | --- |
| `okg_get_catalog_info` | Get catalog metadata: counts, categories, and available endpoints |
| `okg_search` | Semantic search across all resources (ontologies + software) |
| `okg_search_ontologies` | Search ontologies, vocabularies, and taxonomies only |
| `okg_search_software` | Search semantic software tools only |

### Quick Start

```bash
cd mcp-server
uv sync
uv run okg-mcp
```

### Configuration

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "open-knowledge-graphs": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-server", "run", "okg-mcp"]
    }
  }
}
```

## Architecture Overview

1. `scripts/fetch_data.py` queries Wikidata (WDQS), normalizes records, and writes:
   - `data/ontologies.ttl`
   - `data/ontologies.json`
   - `data/software.ttl`
   - `data/software.json`
2. Category enrichment is maintained in `data/categories.json`:
   - one-time backfill: `scripts/classify_categories.py`
   - incremental on daily refresh: `scripts/fetch_data.py`
3. `site/index.html` + `site/app.js` + `site/style.css` render the client-side catalog UI.
4. GitHub Actions refresh data daily and deploy the static site + datasets to GitHub Pages.

## Repository Layout

- `data/`: published datasets and category mappings
- `mcp-server/`: MCP server for AI assistant integration
- `scripts/`: data refresh and LLM classification scripts
- `site/`: static frontend (HTML/CSS/JS + assets)
- `.github/workflows/`: CI/CD for data refresh and Pages deploy
- `ontology.ttl`: ontology and SHACL shape definitions

## Local Setup

### Prerequisites

- Python 3.11+ (3.12 recommended)
- `pip`

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Refresh Data Locally

```bash
python scripts/fetch_data.py
```

Optional category backfill (Anthropic):

```bash
export ANTHROPIC_API_KEY=your_key_here
python scripts/classify_categories.py
```

### Run the Site Locally

```bash
python -m http.server 8000
```

Then open: `http://localhost:8000/site/`

## Data API Documentation

There is no server-side API; the JSON files are the API surface.

### `ontologies.json`

Top-level object:

```json
{
  "generatedAt": "2026-03-08T03:21:55Z",
  "items": []
}
```

`items[]` fields:

- Required:
  - `title` (string)
  - `wikidataId` (IRI string to Wikidata page)
  - `types` (string array, may contain multiple values)
- Optional (omitted when absent):
  - `description` (string)
  - `homepage` (IRI string)
  - `partOf` (string)
  - `licenses` (string array)
  - `category` (string, one of predefined domain categories)

### `software.json`

Top-level object:

```json
{
  "generatedAt": "2026-03-08T03:21:55Z",
  "items": []
}
```

`items[]` fields:

- Required:
  - `title` (string)
  - `wikidataId` (IRI string to Wikidata page)
  - `types` (string array)
- Optional:
  - `description` (string)
  - `homepage` (IRI string)
  - `licenses` (string array)
  - `latestVersion` (string)
  - `releaseDate` (ISO date string)

## Ontology Documentation

Schema source: https://openknowledgegraphs.com/ontology.ttl

### Classes

| Class | Description |
| --- | --- |
| `okg:Resource` | Base class for all catalog resources |
| `okg:Ontology` | Ontology resources |
| `okg:ControlledVocabulary` | Controlled vocabulary resources |
| `okg:Taxonomy` | Taxonomy resources |
| `okg:Software` | Software/tooling resources |
| `okg:License` | License nodes attached to resources |

### Core Properties

| Property | Range | Notes |
| --- | --- | --- |
| `okg:title` | `xsd:string` | required; max 1 |
| `okg:wikidataId` | IRI | required; max 1 |
| `okg:description` | `xsd:string` | optional; max 1 |
| `okg:category` | `okg:Category` | optional; max 1 |
| `okg:homepage` | IRI | optional; max 1 |
| `okg:hasLicense` | `okg:License` | optional; multi-valued |
| `okg:partOf` | `xsd:string` | optional; max 1 |
| `okg:latestVersion` | `xsd:string` | software only; optional; max 1 |
| `okg:releaseDate` | `xsd:date` | software only; optional; max 1 |
| `okg:licenseName` | `xsd:string` | license node label |

SHACL constraints are defined in `okg:ResourceShape`, `okg:SoftwareShape`, and related shapes in `ontology.ttl`.

## CI/CD Pipeline

### Data Refresh Workflow

File: `.github/workflows/update-data.yml`

- Trigger: daily at `0 6 * * *` (06:00 UTC) + manual dispatch
- Installs Python dependencies
- Runs `python scripts/fetch_data.py`
- Commits changed data files as `github-actions[bot]` with:
  - `chore(data): refresh catalog from Wikidata`

### Deployment Workflow

File: `.github/workflows/deploy.yml`

- Trigger: pushes to `main` affecting `site/**`, `data/**`, `ontology.ttl`, or workflow file
- Builds Pages artifact from:
  - `site/` (frontend)
  - `data/` (datasets)
  - `ontology.ttl` (schema)
- Deploys via GitHub Pages actions

## Fork and Deploy

1. Fork the repository.
2. In your fork, enable GitHub Pages with source set to GitHub Actions.
3. (Optional) Configure a custom domain:
   - add `site/CNAME`
   - set DNS records
   - enable HTTPS in Pages settings
4. If using category classification, add `ANTHROPIC_API_KEY` as a repository secret or environment variable for the workflow runtime.
5. Run `Update Catalog Data` manually once to generate/refresh data.
6. Push any change to `site/`, `data/`, or `ontology.ttl` to trigger deploy.

## Migration from Streamlit

The Streamlit app has been removed from `main` (`app.py` no longer exists). See the full migration and feature mapping guide:

- [docs/MIGRATION.md](docs/MIGRATION.md)

Legacy reference data model remains available in `dist/catalog.ttl` (ignored in git).

## Troubleshooting

- `fetch_data.py` fails with HTTP/timeout errors:
  - rerun; the script has retry/backoff for WDQS throttling
- No category assignments added:
  - confirm `ANTHROPIC_API_KEY` is set
  - run `python scripts/classify_categories.py` manually
- Site loads but data is empty locally:
  - serve from repo root and open `http://localhost:8000/site/`
  - verify `data/*.json` exists and is valid JSON
- Workflow runs but no commit is created:
  - no data diff detected in tracked outputs

## FAQ

### Is this only open-source software?

No. The catalog includes both open and proprietary resources if they are represented in Wikidata.

### Are records manually curated?

Primary metadata is sourced from Wikidata queries. Category labels can be added via LLM classification and then frozen in `data/categories.json`.

### Why do some fields appear missing?

Wikidata coverage is uneven. Optional fields (homepage, license, version, release date, category) are omitted when unavailable.

### How often is data refreshed?

Daily at 06:00 UTC via GitHub Actions, plus manual runs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution workflow and quality checks.

## Data and License

- Data source: Wikidata (CC0)
- Code license: MIT (see `LICENSE`)
