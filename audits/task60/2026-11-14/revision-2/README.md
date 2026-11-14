# Task 60 — creator-only tightening, revision 2

Implemented locally for review; not published. This revision supersedes the initial
recommendation policy and evaluation result, while preserving the original audit.

## Rule

Shared creator is supporting evidence only (4 points, reduced from 60). It cannot
create or qualify a candidate or provide its primary explanation. Another approved
uses, containment, bounded shared-parent, repository, namespace, or specific-class
path is required. Creator plus category, language, license, generic type or text
remains insufficient even with an artificially high creator weight. No project/QID
exceptions were introduced. Independently supported ecosystem paths remain eligible.

## Frozen evaluation and fresh review

The same 40 pages and original generation `20261114T135204Z-352b4aa999a4` were used;
input manifest hashes were reverified, with no metadata or membership changes.
All 40 pages and all 77 resulting suggestions were inspected, including remaining
results, rank changes, empty pages and replacements. Judgments are implementation-
author review, not independent acceptance or an estimate for the whole catalog.

- **73/77 relevant (94.8%)**, above the agreed 90% target.
- **77/77 supported evidence; 77/77 accurate wording (100%)**.
- Sample pages with results: **24/40 → 22/40** versus revision 1.
- Graphameleon: **5 → 0**, with no replacement filler. Skosmos: **2 → 0**.
- Fuseki: HugeGraph leaves the top five; Dgraph enters. Dgraph was explicitly
  reviewed and conservatively counted as weak, not assumed useful because qualified.
- Four remaining weak suggestions are disclosed: **Fuseki → Dgraph**,
  **Fuseki → ArcadeDB**, **WebProtégé → CMAP Tools**, and **Protégé → CMAP Tools**.
  For Fuseki, a broad graph-engine match is less useful than its specific SPARQL
  server purpose. For CMAP Tools, the frozen concept-mapping description does not
  establish useful ontology-editing overlap. All four displayed classifications are
  supported; accurate evidence is distinct from practical discovery usefulness.
  This review applies a more conservative usefulness judgment than the first pass;
  the score is not calculated by simply subtracting seven previously weak matches.

`page-review.json` records every page, ordered suggestions, removals, replacements,
no-result decisions and pair-level judgments. `reviewed-pairs.json` records all 77
judgments with their exact evidence and wording.

## Full-cohort impact and replacement review

| Catalog | Live frozen baseline | Revision 1 | Revision 2 |
| --- | ---: | ---: | ---: |
| Resource pages with results / 1,350 | 510 (37.8%) | 410 (30.4%) | 382 (28.3%) |
| Software pages with results / 272 | 72 (26.5%) | 103 (37.9%) | 86 (31.6%) |

Against revision 1: 181 directed links lost, 2 gained; 71 pages have changed
suggestions, order or reason data. Against the frozen live baseline: 289 links gained,
503 lost. All changes are recorded in the two separately named JSON artifacts.
Coverage still exceeds the existing 25% absolute floor; no decline block was added.

Both new full-cohort suggestions were inspected in `replacement-review.json`:
Fuseki → Dgraph (sample, counted weak) and HugeGraph → TypeDB (outside sample,
useful exploratory graph-engine peer, not included in the sample precision score).
Jena/Fuseki functional peers and Neo4j's explicitly supported consumers remain.
Relate still has no inferred vendor-based connection.

## Validation and boundaries

121 focused tests passed: scorer 34; Task 60 contracts 16; independent snapshots 15;
JSON-LD 7; page membership 9; catalog snapshots 40. The new frozen fixture contains
all records sharing Graphameleon's creators plus Jena/Fuseki, with original source
triples and derived recommendations removed. It rejects creator-only projects and
retains the independently supported Jena/Fuseki connection. General synthetic
regressions cover uses, parent, repository, namespace and class support, including
an extreme creator score that still cannot qualify a pair by itself.

The full frozen-cohort evaluator again passed source-triple/JSON-field preservation,
determinism, complete evidence validation, RDF/JSON projection, schema declarations,
and all 40 rendered HTML/parsed JSON-LD evidence checks. These are focused and
frozen-cohort checks, not a claim that the repository-wide suite was run.

Relate metadata work and issue #279 library ingestion were not changed. No Wikidata
writes, push, Actions or publication occurred. Task 60 remains review. Residual weak
matches are disclosed for review rather than removed using project-specific rules.
