# Task 60 — broader domain and software-type discovery

Revision 3 implements the user's expanded meaning of related: another resource in
the same meaningful subject domain, or another tool of the same functional type,
is a valid discovery suggestion even without a closer ecosystem connection.
Implemented locally for review; not published. Earlier audits remain unchanged.

## Behavior

- Resource-to-resource exact `okg:category` matches qualify independently.
- Software-to-software exact `okg:softwareType` matches qualify independently.
- Known concept identities and display labels come from the maintained catalog
  vocabularies, not a separate project allowlist. Their hashes are in summary.json.
- Examples: **Same domain: Healthcare**, **Same software type: Ontology Engineering**.
- Direct uses/containment rank first, other supported structural/specific-class
  paths next, broader discovery last. At most five distinct target identities.
- Broad admission scores are 60; category/type contributes only 4 points to pairs
  already supported by a closer path. Scores and canonical URL break ties within
  each tier. Changing which category signals count can reorder close peers;
  every changed pair is recorded rather than claiming the prior top five is fixed.
- Shared creator remains support only. General / Cross-domain, missing or unknown
  classifications and generic RDF types do not qualify. Software's general domain
  category does not connect unrelated tools. No project-specific exceptions,
  guessed classifications, source edits or automatic compatibility claims.

## Frozen coverage

Same generation `20261114T135204Z-352b4aa999a4` and same frozen 40 pages; all input
manifest hashes rechecked. No metadata, membership or original source fields changed.

| Catalog | Revision 2 | Revision 3 |
| --- | ---: | ---: |
| Resource pages with recommendations / 1,350 | 382 (28.3%) | **1,197 (88.7%)** |
| Software pages with recommendations / 272 | 86 (31.6%) | **235 (86.4%)** |
| Frozen sample pages with recommendations / 40 | 22 | **33** |

Remaining empty pages: 152 resources and 37 software records lack an admitted
meaningful domain/type plus any closer qualified path in the snapshot. One resource
(Addgene RDF dataset) has a meaningful domain but is excluded by the existing
homepage eligibility gate; that separate gate was not changed in this revision.
No filler is invented for these pages. Relate is still empty in this snapshot.

Against revision 2, 5,840 directed links are gained and 31 lost, with 1,276 pages
changed (including rank/reason changes). Against the frozen live baseline, 5,985
links are gained and 390 lost. Full comparisons are in the two compressed JSON
change files; uncompressed evaluator output is also in the local review package.

## Page-by-page review

All 40 pages and all 161 suggestions were inspected, including source/target
descriptions, exact graph evidence, ordering, empty pages, and all 94 suggestions
new to the sample since revision 2. This is author review, not independent acceptance
or a whole-catalog precision estimate. The usefulness criterion now includes broad
domain and functional discovery, as requested; it is not directly comparable to the
previous close-relevance criterion.

- **154/161 relevant (95.7%)** under the expanded scope.
- **161/161 supported evidence and accurate wording (100%)**.
- 50 shared-domain suggestions, 34 shared-software-type suggestions, 50 specific
  shared-class suggestions, and 27 direct use/containment suggestions.
- Seven conservatively weak suggestions remain disclosed: GeoSPARQL's four
  Technology & Web matches have little recognizable geospatial overlap;
  CMAP Tools on both ontology-editor pages has uncertain editing usefulness;
  SHACTOR's described graph-quality purpose leaves its ontology-engineering
  usefulness unclear. These are evidenced classifications, not fabricated links.

Examples inspected: SNOMED CT gains healthcare vocabularies; GOLD gains linguistic
resources; Catena-X semantic models gain supply-chain standards; Graphameleon gains
YARRRML Parser, Chimera, CoW, D2RQ and Dragoman through RDF mapping/ETL. Its unrelated
creator-only matches remain excluded. Direct dependencies stay above broad matches.
Graph databases with different query interfaces are now accepted as exploratory
functional peers; their reasons do not imply interface compatibility.

`page-review.json` contains all pages, removals, additions, ordered judgments and
empty-page review. `reviewed-pairs.json` includes all 161 individual judgments with
source/target descriptions and exact reason evidence. Broad matches were inspected,
not automatically counted relevant merely because the scorer qualified them.

## Validation and boundaries

**125 focused tests passed**: scorer 34; Task 60 contracts 20; snapshots 15;
JSON-LD 7; page membership 9; catalog snapshots 40. New coverage checks independent
domain/type qualification, exact reason predicates, cross-catalog/software-domain
exclusion, unknown/general classification rejection, top-five tier priority even
with an extreme supporting score, and repeatability. SHACL validates both new reason
codes with the actual concept vocabularies and still rejects an invalid rank.
Existing Graphameleon creator-only and supported-ecosystem regressions remain green.

Full frozen-cohort validation passed source-triple and JSON-field preservation,
deterministic recomputation, full graph evidence, RDF/JSON projections, declared
schema, and rendered HTML/parsed JSON-LD explanations for all 40 sample pages.
The repository-wide suite is not claimed as run.

Task 60 remains review. Relate metadata work and issue #279 library ingestion remain
separate and unchanged. No Wikidata writes, push, Actions or publication occurred.
