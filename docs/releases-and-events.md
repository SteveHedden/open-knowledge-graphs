# Resource releases and the shared activity feed (Task 52)

Task 52 adds release metadata to resources and preserves software's preferred-rank
selection. Task 54 owns the homepage and **Add or update your project** guide.
No repository release APIs, tags, commits or release pages are polled or scraped.
A release that exists on GitHub but has not been recorded in Wikidata is outside
this integration's coverage.

## Source and selection

For every admitted ontology, vocabulary, taxonomy, knowledge graph, ontology
language or standard, read explicit Wikidata **P348** version statements. Read
**P577 as a qualifier on the same statement**, including its value-node precision
and calendar. This also applies to software. Do not use an item's standalone
publication date, inception date, Wikidata edit time, fetch time or deployment
time as a release date. Resource type alone does not establish that an item has
versioned releases.

Ignore deprecated statements. If preferred statements exist, they take precedence
over normal statements, even when a preferred statement has no date. Within the
eligible rank, choose the latest supported date and break ties deterministically
by version text and statement IRI. Without dates, retain the existing software
lexical version fallback; it is not semantic-version ordering or proof of release
chronology. Tied different versions or overlapping dates at different precisions are marked ambiguous and withheld from eligible
release events. Multiple conflicting dates on one statement remain unknown.

Preserve Gregorian year, month and day precision as `YYYY`, `YYYY-MM` and
`YYYY-MM-DD`. Unsupported calendars or precision do not become invented Gregorian
days. Undated versions can be displayed but cannot produce dated release events.
A coarse date is eligible only after the entire reported period has elapsed;
future dates remain stored but ineligible. Ordinary unversioned updates are deferred
until a separately approved authoritative signal exists.

The selected evidence carries statement IRI, rank, original dates, qualifiers and
reference nodes/values. This is Wikidata evidence, not an independent endorsement
of every upstream claim. A repository URL alone is never release evidence.

## RDF, projections and visible fields

`data/ontologies.ttl` and `data/software.ttl` are authoritative. Resources now use
the same `okg:latestVersion` and `okg:releaseDate` fields as software, plus
`okg:releaseDatePrecision` and `okg:latestRelease`. Date literals use `xsd:date`,
`xsd:gYearMonth` or `xsd:gYear`. Release evidence includes its version, source
statement, rank, canonical structured metadata, and queryable Wikidata qualifier
and reference triples. Existing scalar software metadata remains readable during
migration; it does not create an event until paired statement evidence is acquired.

JSON projects these as `latestVersion`, `releaseDate`, `releaseDatePrecision`,
`latestRelease`. Existing public URLs do not change. Resource detail pages show
known version/date values; absent fields are omitted. The resource listing gains
a sortable latest-release column and equivalent mobile fields. Software's existing
columns remain, with precision-aware date formatting. Unknown dates sort last.
No classification/review metadata panels are added.

## Version 1 event contract for Task 54

- Authoritative history: `data/catalog-events.ttl`.
- Derived feed: `data/catalog-events.json`.
- Schema: `validation/catalog-events-v1/events.schema.json`.
- Representative release feed: `tests/fixtures/releases/event-feed.json`.
- Exactly two event types: `new-to-okg` and `release`.
- Identity is catalog kind plus Wikidata QID, independent of title and slug.
  The same item can be represented in both catalogs. Each catalog has one
  addition event and at most one release event per version identifier.
- Event IDs are deterministic. Date corrections update the existing release event
  while preserving immutable evidence revisions in RDF. `history` links those
  revision nodes. Refreshes, renames, removals and restorations do not reset dates.
- `date` is the actual supported release date or first catalog inclusion date;
  `datePrecision` describes its precision. `discoveredAt` is when OKG first
  observed the event. Never rank an old release by its later discovery timestamp.
- `dateBasis` distinguishes `release`, `catalog-commit`, and `catalog-observation`.
  A historical commit proves recorded catalog inclusion, **not deployment**.
  A candidate assembled feed is also not proof of publication. Serve the feed
  from the same verified live generation as the catalog.
- `eligible: false` retains withdrawn/absent/superseded/ambiguous/future evidence
  for audit; consumers select only eligible entries. A current, unambiguous
  selected release can become eligible again after restoration without becoming
  a new event. Its original date and ID remain unchanged.
- Use current `title`, `kind`, `wikidataId` and `url` for display. `url` is the
  canonical resource identity, not a guarantee that a detail page passed the
  existing page-quality checks. Task 54 must resolve destinations against the
  generation's `data/page_qids.json`, falling back to a catalog/Wikidata link or
  excluding entries without a suitable destination.
- Within a homepage column, group by identity and choose the appropriate recent
  event rather than displaying an addition and release for the same item twice.
  Select using actual event dates; apply the homepage's stated date window.
  Jobs continue to use their separate active/qualified job feed.

## Historical initialization and publication

The committed seed is reconstructed from complete, first-parent Git history of
catalog JSON/RDF. Later first appearances have commit provenance. Items already
present in the first available snapshot have an unknown first-seen date: the
snapshot proves only that they existed by then. Old registry identities are
retained even when no reliable first-seen evidence can be recovered. Migration
and restoration never turn these into fresh additions. Initial addition events
retain their historical dates and must not all be promoted as newly added today.

```sh
python scripts/catalog_events.py backfill --repository . --root . --ref main
python scripts/catalog_events.py validate --root .
```

Backfill is idempotent and refuses shallow history. Run it to initialize a ledger,
not on every refresh. Once initialized, the coordinated publisher updates the
ledger after assembling pinned resource/software snapshots. Independent refreshes
carry release evidence in their existing dataset RDF/JSON; they cannot replace
publisher-owned event history. This does not change workflow orchestration.

The publisher validates RDF/JSON parity and event schema before deployment.
Normal generation manifests cover the ledger/feed. Publication failure preserves
the normal Task 50 recovery path; retrying does not create duplicate events.
Do not delete the ledger or rebuild it from only today's active records.

## Contributor handoff

Help visitors first find the correct existing Wikidata item. For a genuinely
versioned resource, use P348 for the version identifier and add P577 to **that
statement** for its supported release date, with the actual known precision and
references. Respect applicable ranks and qualifiers; never invent a preferred
release or copy unrelated item-level dates. If the metadata is missing, report the
gap or explain how the visitor can improve it; this task performs no Wikidata edits.

Task 54 should verify its full eligibility/notability guidance against current
Wikidata policy before publication. The CTA wording is **Add or update your
project**. Creating or editing an item does not guarantee OKG inclusion, a detail
page, or promotion. These release fields do not change existing inclusion rules.

References: [P348](https://www.wikidata.org/wiki/Property:P348),
[P577](https://www.wikidata.org/wiki/Property:P577).

## Representative records and checks

Captured source claims and revision IDs are in
`tests/fixtures/releases/wikidata-examples.json` (2026-09-20):

| Item | Observed result |
| --- | --- |
| Schema.org (Q3475322) | Preferred version 30.1, paired date 2026-09-15, references preserved |
| Raptor (Q141112433) | Preferred 2.0.16 / 2023-03-01 wins over higher-looking normal versions |
| Basic Formal Ontology (Q4866972) | No P348; release metadata remains absent |
| Gene Ontology (Q135085) | No P348; release metadata remains absent |
| RDF (Q54872) | No P348; unrelated item-level dates are not release dates |
| SAMM (Q140523058) | No P348; repository presence does not fill the gap |

The initial history seed contains 1,423 supported addition events. Tests cover
new and restored identities, rank/date pairing, no-date versions, conflicting and
coarse dates, old releases discovered later, RDF/JSON parity, immutable revisions,
snapshot ownership and desktop/mobile rendering. Real source claims were retrieved
read-only from Wikidata's entity endpoint. The live query service returned a
timeout/502 during verification; the SPARQL query is also executed against a local
RDF fixture with paired date nodes and references. Production refresh should be
verified when that service is available; no live Wikidata data was edited.
