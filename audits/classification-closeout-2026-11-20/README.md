# Auryn, OpenMetadata and ETT classification closeout

This batch follows `docs/classification-review.md` against the November 20 catalog evidence. It changes OKG classifications, not Wikidata, admission rules, licenses or product capabilities.

| Record | Accepted assignments | Evidence |
|---|---|---|
| Auryn (Q142219047) | Technology & Web; primary type Knowledge Graph Construction; knowledge graph construction activity; Python | Description explicitly says constructing code knowledge graphs and providing context to AI coding agents; programmingLanguages is Python. Existing PR #297 review remains compatible with the imported record. |
| OpenMetadata (Q141668307) | Technology & Web; Provenance and lineage; Java, Python, TypeScript | Description says metadata platform for data discovery, governance, data quality, and lineage; programmingLanguages lists all three languages. |
| European Training Thesaurus, third edition (Q142189346) | Education & Training | Description explicitly identifies vocational education and training literature. |

All applicable dimensions were reviewed. OpenMetadata receives no primary software type: the current type vocabulary has no metadata-management/data-catalog category. A general platform's data-quality feature does not make data validation its primary function; RDF or SPARQL support does not make it primarily a query client, RDF ETL tool or graph database. Do not attribute Collate-only ontology authoring to OpenMetadata. This is an intentional reviewed omission, not an unresolved classification request. The narrower lineage activity avoids a redundant governance parent assignment. No tool or activity is inferred merely from the ETT title.

Auryn's separate Uses → FalkorDB relation and MIT license remain unchanged. OpenMetadata retains both component-specific license entries. ETT receives no invented open license.

Refs #296, #298, #273. Close only after the coordinated publisher applies these reviews and the live datasets and pages are verified. Microsoft batch #293 stays open pending the licensing inquiry response.

## Validation

- Review import passed with current content, vocabulary and correction hashes.
- Staged publisher review application marks all three records complete with the assignments above.
- Shared-tag validation passed across 4,701 records and 9,117 assignments, including RDF/JSON parity, exact source excerpts, allowed targets and preserved source descriptions/job eligibility.
- Classification tests: 33 passed, 3,069 subtests passed.
- Full Jobs suite: 420 passed, ten failed. All ten failures reproduce on unchanged main `dbb0128f92653660380d767629611f2866867ed1`; tracked separately in #299. This batch changes no Jobs code, fixtures or source contracts.
- Generated staging datasets are not committed. The coordinated publisher reapplies the review log to its pinned snapshots and verifies the live generation.
