# Task 60 local implementation review — 2026-11-14

The local implementation removes data-format-only recommendations, supports
resource/software graph connections, and displays auditable, direction-aware
reasons. It is implemented and locally validated, not published.

Base: current main `c70e366e3009a6749be3c5a6eaa98f20ed9cf40d`, plus the existing
Task 59 scorer corrections ported from the user's working tree. Unrelated local
edits were not changed. The policy tests retain current main's nonblocking
coverage-decline behavior rather than the older local test expectation.

## Evaluation

The user approved 40 pages, >=90% relevance, and 100% supported evidence/accurate
wording before tuning. The sample was frozen against live generation
`20261114T135204Z-352b4aa999a4`. It contains 20 resource pages and 20 software pages,
including pinned regressions, sparse metadata, functional peers, direct edges,
shared creators and no-result cases. Remaining slots use deterministic SHA256
selection from linked and unlinked page-eligible records. Snapshot hashes are in
`frozen-sample.json`; the evaluator also checks the publisher manifest.

**Author-reviewed result: 77/84 suggestions relevant (91.7%); 84/84 have supported
source-graph evidence and honest wording.** All seven same-creator suggestions
were conservatively counted as not sufficiently useful: shared authorship is
factual but does not establish practical usefulness for the source page. This
is an implementation-author review, not independent user acceptance or a claim
about precision across the entire catalog. No-result pages are excluded from the
precision denominator and included in coverage. Sample coverage is 25/40 before,
24/40 after. See `reviewed-pairs.json` for every individual decision.

| Full final-page cohort | Before | After |
| --- | ---: | ---: |
| Resource pages with recommendations / 1,350 | 510 (37.8%) | 410 (30.4%) |
| Software pages with recommendations / 272 | 72 (26.5%) | 103 (37.9%) |

Across both catalogs, 364 directed links are gained and 399 lost. `changes.json`
records each changed pair, score evidence, and whether a lost link remains
qualified but is outside the stronger top five. No source triples, memberships,
original JSON fields, or classifications changed. The coverage decline is reported,
not used to reinstate the removed decline block; the existing absolute floor is
also still satisfied.

## Regression outcomes and limits

- Neo4j Ontology Graph Specification no longer recommends DCAT or LIDO merely
  through Q494823 data format. Independently supported DCAT/LIDO relationships
  remain.
- Relate by Neo4j remains without suggestions: its frozen graph lacks a qualified
  connection to Neo4j. Vendor branding is not used to invent one. Missing creator,
  functional classification and relationship evidence are queued as the separate
  private Teacher metadata finding `task60-relate-relationship-evidence`.
- The specification/library uses edge is verified in fixtures, with **Uses** and
  **Used by** in the correct directions. The library is absent from this frozen
  catalog. Live admission and verification remain under issue #279.
- A reviewed allowlist preserves specific functional matches (including graph
  visualization software) while dropping generic library-language, proprietary
  software and broad RDF-vocabulary matches. Unknown classes remain unapproved;
  the smaller resource coverage is explicit, not hidden by weak replacements.

## Validation

- 120 focused tests passed: scorer/diagnostics 34; new Task 60 contracts 15;
  JSON-LD 7; independent dataset snapshots 15; page membership 9; catalog
  snapshots 40.
- Full frozen-cohort evaluator passed manifest integrity, exact non-recommendation
  triple preservation, original JSON-field preservation, RDF/JSON projection,
  declared-schema checks, complete graph-evidence validation and deterministic
  repeated ranking. All 40 preview pages preserve evidence through RDF, JSON,
  HTML and parsed JSON-LD.
- New SHACL test accepts valid recommendation nodes and rejects out-of-range rank.
- Desktop and actual 390-pixel mobile previews inspected. Mobile viewport width
  and document scroll width both measured 390; all five reasons render.

The repository-wide current-catalog test initially could not run in the sparse
checkout because generated catalog files were intentionally excluded. It is not
claimed as passed; the frozen-cohort checks above validate the affected contracts
against the pinned live artifacts instead. Initial independent-snapshot failures
from missing sparse-checkout policy files were resolved by fetching those files;
all 15 tests subsequently passed.

No Actions, Wikidata edits, push, or publication occurred. Task status is review;
completion still requires reviewed acceptance and separately authorized live
publication verification using the normal nightly route.
