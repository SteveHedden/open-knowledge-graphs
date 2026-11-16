# Task 61 — review checkpoint revision

**Ready for review; not pushed, merged or published.** This revision addresses the two reproduced evidence-filter defects in the November 15 review of `3357028f7`. The original review artifacts are preserved in the parent directory.

## Findings fixed

The filter now requires a target-bound capability in the saved excerpt: an action governing that target/complement, or a technical capability modified by the target. It reads surrounding source context for clipped negation and temporal qualifiers. It no longer admits a target merely because another capability word occurs elsewhere in the excerpt, and it no longer vetoes a valid relationship because an unrelated later clause contains a negative or inverse phrase.

| Reproduced description | Saved excerpt | Revised outcome |
|---|---|---|
| Tool validates RDF data with SHACL without requiring a server. | validates RDF data with SHACL | Current Uses retained |
| Tool validates RDF data with SHACL. It is used by researchers. | validates RDF data with SHACL | Current Uses retained |
| Tool cannot use SHACL. | Full description or clipped “use SHACL” | Metadata only |
| Tool will support SHACL in a future release. | Full description or clipped “support SHACL” | Metadata only |

Regression cases also cover contractions, plans, future-release suffixes, past use, shared negation in target lists, inverse relationships, unrelated capability words, reference-only documentation, repeated contradictory excerpts, and independently sourced P2283 edges. A rejected classification does not erase an upstream relationship or rewrite its provenance.

This remains a conservative rule-based boundary on accepted classifications, not a general English parser. Unrecognized or ambiguous constructions are retained as metadata for review. No product-pair exceptions or ranking changes were added.

## Assignment dispositions

**428 supported / 76 metadata**, compared with **431 / 73** at the review checkpoint. All 73 previously uncertain assignments remain uncertain. Three previously supported assignments are now deferred:

| Subject → target | Saved evidence | Reason and recommended next step |
|---|---|---|
| SNARC → Wikibase | “semantic name authority Wikibase for entities represented in Welsh heritage instituations” | The old check borrowed “represented” from the description of the entities. Obtain a current excerpt explicitly establishing SNARC as a Wikibase instance or using Wikibase, then submit an evidence-backed classification review. |
| Wikibase system ontology → Wikibase | “OWL ontology for Wikibase” | OWL is the representation language; “for Wikibase” does not establish that the ontology uses the software. Retain the application-domain relationship as metadata unless independent use evidence is supplied. Its OWL use remains supported. |
| rdf2rml → RDF | “RDF by Example: rdfpuml for True RDF Diagrams, rdf2rml for R2RML Generation” | The generation capability belongs to the named R2RML target; it must not automatically support the other RDF mention. Obtain an explicit RDF input/output/use excerpt. R2RML use remains supported. |

Eight uncertain entries have a renamed reason code (`mention-negative-or-different-relationship` → `mention-or-different-relationship`); their acceptance state did not change. The complete [disposition delta](disposition-changes.json), [504-entry audit](tag-use-audit.json), and [three withdrawn evidence records](removed-classification-support.json) preserve the exact prior evidence.

## Frozen comparison and replacement review

The original **40-page selection plus the two acceptance examples** was rerun against the same pinned baseline hashes. All **200 recommendations across 42 pages are identical to the reviewed implementation**, including their order, reasons and provenance. SHACL Play! retains RDF and SHACL as Uses; AWS Context Ontology Accelerator retains ELK, ontop and HermiT.

Across all **1,623 eligible published pages**, one displayed list changes relative to the checkpoint:

- SNARC loses **Uses → Wikibase**.
- Its four existing same-domain recommendations move up one place.
- **Microsoft Academic Graph** enters fifth, labeled **Same domain: Library & Cultural Heritage**. The frozen catalog description concerns scientific publications, citations and associated entities, and both records have that explicit domain classification. This is a broad discovery connection under the existing rule, not a claimed dependency or close substitute.

The Wikibase system ontology and rdf2rml records have no eligible displayed list in this frozen catalog, so their withdrawn evidence does not cause another displayed replacement. No other page gains or loses a recommendation relative to the checkpoint. Coverage remains **1,587 / 1,623**. Against the original production baseline, totals are now **188 gained / 186 displaced**, rather than 189 / 187.

See the [single changed list with complete before/after evidence](recommendation-changes-since-review.json), [SNARC rendered preview](snarc-preview.html), [42-page review](page-review.json), [all changes against production](changes.json), and [summary with frozen input hashes](summary.json).

## Validation

**126 targeted tests pass**: Task 61 (12), Task 60 (24), Task 25 (34), shared tags (16), classification review (16), page membership (9), and snapshot/replay (15). The focused recommendation total is 70. The final validation record is in [validation.json](validation.json). It separates this implementation run from the earlier independent review: the checkpoint independently reported 66 focused tests, not a completed broader run. This revision reruns the selected affected suites; it does not claim a repository-wide green test suite.

Staged validation checks all recommendation paths and labels; RDF/JSON use and classification projections; SHACL and declared schema terms; 42-page HTML/JSON-LD parity; the five-result cap and eligible targets; replay idempotence; protected fields; and byte identity of 13 review/correction and Jobs artifacts. The comparison with the reviewed implementation additionally proves that all JSON fields outside `uses`/`relatedTools` are identical, all upstream evidence is unchanged, and remaining use evidence is unchanged. SNARC's replacement list also passes HTML/link/reason parity.

## Reproduce

Use the original baseline and a separate staging copy with the revised code. Replay `scripts/shared_tags.py --root STAGE --only catalog`, refresh recommendations with unchanged `data/page_qids.json` membership, then:

```sh
python audits/task61/evaluate.py BASE STAGE audits/task61/revision-2
python audits/task61/revision-2/compare_review.py PREVIOUS_REVIEW_STAGE STAGE
```

The evaluator now verifies the baseline input hashes and accepts a separate output directory, preserving the initial checkpoint artifacts. No source refresh, paid API, Wikidata mutation, push, merge or publication action is needed or performed.
