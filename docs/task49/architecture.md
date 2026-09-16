# Shared descriptive classification

Task 49 implements one RDF identity and concept model for catalog resources, software and jobs. Vocabulary approval was given in the implementation conversation on 2026-09-15. The local proposal remains available in the original checkout; `REVIEW.md` preserves the approved review scope.

## Maintained inputs

- `vocabularies/categories.ttl`: existing domain identities and four approved children.
- `vocabularies/activities.ttl`: twenty activity/use-case concepts; four reuse the existing jobs activity identities.
- `vocabularies/supplementary-entities.ttl`: fifteen approved non-catalog entities.
- Catalog RDF: identity, labels, aliases, entity types and existing links. `vocabularies/tools-resources.ttl` is its generated entity registry, including supplementary entities and one tagging identity for each QID.
- `curation/tag-decisions.ttl`: durable human acceptance/rejection, independent of content-version cache keys. Preserve explicit reviewed corrections from PR 73.

`scripts/shared_tags.py` performs linear-time alias discovery, contextual LLM classification, strict source-quote and target validation, and RDF evidence construction. It never changes source text, admission policy, job evidence scoring, active membership or identity. The initial backfill includes retained normalized job snapshots; historical-only records and raw suggestions stay in local `build/` artifacts.

## Authoritative assignments and projections

`okg:usesResource`, `okg:hasActivity` and multi-valued `okg:category` link accepted assignments. Every subject has an assessment linked to evidence nodes. These retain exact source-field text, source link, method, vocabulary version, content hash and review state. Required/preferred/contextual/unspecified and alternative-requirement wording live only in RDF evidence; the public JSON whitelist excludes these fields.

`sharedTags` JSON and `categories` arrays are projected from accepted RDF. The old scalar `category` and `data/categories.json` remain deprecated **primary-category compatibility projections**, never a limit on assignments. The legacy curation category value is synchronized to an accepted domain so it cannot contradict the shared classification. Its old exactly-one-domain LLM step is bypassed when shared vocabularies are present. Software types remain separate.

Invalid quotes/targets and ambiguous proposals do not become published assignments. `build/tagging-suggestions.json` retains private diagnostics. Empty dimensions mean no accepted evidence, not an assertion that the subject lacks a capability or domain. Organizations, people, licenses and source/policy nodes are not backfilled in these dimensions.

## Refreshes and caching

Both existing transactional publication workflows run shared classification before their validation/commit steps. Cache identity includes normalized meaningful content, approved concept semantics, the entities actually matched in that record, alias policy, method and model. Adding an unrelated catalog entity therefore does not reclassify the whole corpus; a newly matched candidate does. Refresh timestamps do not trigger reclassification. Meaningful vocabulary/content/method changes do. Private response caches persist through GitHub Actions cache; accepted RDF can seed a cache if the private response cache is absent. Human corrections are applied separately on every projection and cannot be overwritten by an automated refresh.

Catalog assignments are kept with catalog RDF and `curation/tag-assignments.ttl`. Job assignments are kept inside the independently manifested `data/jobs/jobs.ttl`. Hourly/daily job refreshes must not modify the catalog manifest's assignment artifacts. Workflow classification failure prevents publication; no result is fabricated to complete a run.

## Website, API and comparison

The catalog and job cards use shared chips and evidence inspection. Existing job catalog mentions and language chips use this same display when classification is available. Detail pages render the same accepted evidence. Shared filters and `/tags/` use `site/shared-tags.js`; the API imports that same logic.

Filters: OR within tools/activities/domains, AND across dimensions, and parent selection includes descendants. New API endpoints are `/tags` and `/tag-comparison`. Search accepts repeatable `tools`, `activities` and `domains` URIs. Filtered searches use the full verified catalog and explicitly report text-filter mode, preventing a small vector-result window from silently losing matching records. Unfiltered semantic results hydrate full shared tags from the matching catalog generation. MCP parameters mirror the API; if a filtered API request fails, MCP fails clearly instead of silently returning unfiltered results.

The comparison shows resource records, software records, their union of catalog identities, distinct active eligible job postings, and employer counts. Jobs preserve the catalog's qualified/review inclusion policy. Known posting fingerprints are deduplicated; unresolved syndicated copies can remain. Catalog entities present in both catalogs count once in the union. A tool's own catalog record counts as supply for that tool, without generating a self-use triple. Counts overlap across tags and must not be summed. These measure catalog coverage and observed hiring demand, not quality, delivery capacity, vacancies across the entire market, or a meaningful numerical supply/demand ratio.

## Validation and publication

Run the root, jobs, API/browser and MCP suites, `scripts/validate_shared_tags.py`, catalog semantic validation, and both catalog/jobs manifest checks. The first backfill also validates all protected fields and membership against its baseline. Retain aggregate before/after audit and representative evidence. Publish through the repository's reviewed PR and transactional publication workflows, then verify the live generation, tags, filters, comparison endpoint and representative detail pages.

### Provider migration

The classifier supports Anthropic and OpenAI using `TAG_CLASSIFICATION_PROVIDER`
and `TAG_CLASSIFICATION_MODEL`. OpenAI uses full GPT-5.4 with medium reasoning;
credentials remain in environment variables. `TAG_REUSE_MODELS` is an explicit
comma-separated allowlist of prior model outputs acceptable for a migration.
The source, vocabulary, alias policy and method must still match; each reused
assessment retains the original model in its cache key and RDF attribution.
The Task 49 backfill preserves completed `claude-sonnet-4-6` results. Invalid
quotes and ambiguous assignments remain private regardless of provider.

Alternative requirements remain visible as individual tool tags: “Neo4j, Stardog,
or equivalent” produces both supported tags, with the alternative group retained
only in RDF. Discarding unsupported group text never removes an otherwise
evidence-backed tool assignment.
