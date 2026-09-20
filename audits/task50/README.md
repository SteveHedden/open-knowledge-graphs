# Task 50 workflow audit and verification

Baseline: production `3b5802d3`; observed GitHub Actions runs on 2026-09-20.

| Phase | Successful publication 35466932969 | Target after separation |
| --- | ---: | --- |
| Wikidata acquisition | 206 s | 0 s / 0 requests in publication |
| Shared catalog classification | 177 s | 0 s / 0 model calls in publication |
| Detail pages | 27 s | One render pass; reuse identical bytes |
| Catalog validation | 11 s | Retain complete validation |
| Content comparison | 20 s | Preserve normalized-content deduplication |
| Baseline vector readiness | 246 s | Preserve readiness and generation isolation |
| Candidate vector readiness | 247 s | At most one candidate generation per release |
| Full publish job | 1,203 s | < 900 s jobs-only, excluding queue/runner allocation |

Successful run: https://github.com/SteveHedden/open-knowledge-graphs/actions/runs/35466932969

Run 35508346905 spent 5,390 s in the combined Wikidata acquisition step before
cancellation at the 90-minute job limit; deployment never started. Isolation must
allow saved jobs/software data to publish even under this failure.
https://github.com/SteveHedden/open-knowledge-graphs/actions/runs/35508346905

Jobs run 35430261963 succeeded in approximately 393 s wall time; run 35499074352
failed after approximately 1,444 s. Source-level last-good retention already exists;
the old successful-run-only publication gate prevented immediate publication of
otherwise valid mixed output. Both jobs and catalog previously held the same
repository-publication concurrency group for acquisition and deployment.

The old combined fetch built both catalogs and cross-catalog recommendations;
classification cache keys included vocabulary-wide/scoped concept hashes, allowing
additions or label changes to trigger unnecessary assessments. HTML deleted and
rewrote every detail page. Vector readiness/seeding is already generation-aware;
its cost is retained pending separately proven cross-generation reuse.

Local verification results and production timings are recorded here as checks finish.

Local checks (2026-09-20):

- Root regression suite: 228 passed; the additional exact-transition semantic-review
  regression also passes in the 14-test independent snapshot suite.
- Jobs: 350 existing tests passed; the two changed workflow-contract tests passed
  after updating their expected independent queue and completion triggers (352 total).
- API: 55 passed. MCP: 20 passed in an isolated dependency environment.
- Real stored corpus cache rehearsal: all 4,298 records reused, zero uncached
  assessments and zero classification API calls, including a missing response cache.
- Assembled catalog and shared RDF/JSON evidence validation passed: 4,298 records,
  8,686 accepted assignments; no identity loss and no schema/metadata warnings.
- Initial page rebuild reused 995 pages and regenerated 32; subsequent unchanged
  code/catalog inputs can skip rendering and homepage requests entirely.
- YAML parsing, Python compilation, JavaScript syntax and whitespace checks passed.

The release rehearsal also exercises the code-change invalidation path: modifying
release code between two runs changes `publication-inputs.json` and correctly
requires a release. Identical-input checks are run with code held fixed.
